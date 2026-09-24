"""Case serialization and deterministic state transitions shared by HTTP routes."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.inspection import inspect

from database.models import Approval, Audit, Case, Document, Job, Task

STAGES = [
    "intake",
    "documents",
    "treatment",
    "demand",
    "negotiation",
    "settled",
    "litigation",
    "closed",
]
TRANSITIONS = {
    "intake": {"documents"},
    "documents": {"treatment", "litigation"},
    "treatment": {"demand", "litigation"},
    "demand": {"negotiation", "litigation"},
    "negotiation": {"settled", "litigation"},
    "settled": {"closed"},
    "litigation": {"settled", "closed"},
    "closed": set(),
}


def row_dict(row, exclude=()):
    return {
        column.key: getattr(row, column.key)
        for column in inspect(row).mapper.column_attrs
        if column.key not in exclude
    }


def get_case(db, case_id):
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    return case


def case_detail(db, case):
    result = row_dict(case)
    for key, model in [
        ("documents", Document),
        ("tasks", Task),
        ("approvals", Approval),
        ("jobs", Job),
        ("audit", Audit),
    ]:
        rows = db.scalars(
            select(model)
            .where(model.case_id == case.id)
            .order_by(model.created_at.desc())
            .limit(200)
        )
        result[key] = [row_dict(row, ("storage_key", "sha256")) for row in rows]
    return result


def validate_transition(db, case, stage, amount):
    if stage not in TRANSITIONS.get(case.stage, set()):
        raise HTTPException(409, f"Cannot move from {case.stage} to {stage}")
    if stage == "demand":
        if case.medical.get("status") != "complete":
            raise HTTPException(409, "Confirm treatment completion before demand stage")
        categories = set(
            db.scalars(
                select(Document.category).where(
                    Document.case_id == case.id, Document.status == "ready"
                )
            )
        )
        if not {"medical", "bills", "insurance"}.issubset(categories):
            raise HTTPException(
                409,
                "Ready medical, bills and insurance documents are required for demand stage",
            )
    if stage == "negotiation":
        approved = db.scalar(
            select(Approval).where(
                Approval.case_id == case.id,
                Approval.kind == "demand",
                Approval.status == "approved",
            )
        )
        if not approved:
            raise HTTPException(409, "Approve a demand packet before negotiation")
    if stage == "settled" and not amount:
        raise HTTPException(422, "A positive settlement amount is required")
