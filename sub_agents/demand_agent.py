"""Compose a factual demand review packet; never choose a demand amount or send it."""

from sqlalchemy import select

from database.models import Approval, Document


def run(db, case):
    if db.scalar(
        select(Approval).where(
            Approval.case_id == case.id,
            Approval.kind == "demand",
            Approval.status == "pending",
        )
    ):
        return
    documents = list(
        db.scalars(select(Document).where(Document.case_id == case.id, Document.status == "ready"))
    )
    medical, insurance = case.medical or {}, case.insurance or {}
    body = "\n".join(
        [
            "DRAFT — ATTORNEY REVIEW REQUIRED",
            "",
            f"Client: {case.client_name}",
            f"Incident: {case.accident_date} | {case.case_type} | {case.jurisdiction}",
            f"Client-reported injuries: {case.injuries or 'Not recorded'}",
            f"Staff-recorded diagnosis: {medical.get('diagnosis') or 'Not confirmed'}",
            f"Treatment: {medical.get('treatment') or 'Not confirmed'}",
            f"Medical bills entered by staff: ${medical.get('bills_cents', 0) / 100:,.2f}",
            f"Carrier: {insurance.get('carrier') or 'Not confirmed'}",
            f"Claim: {insurance.get('claim_number') or 'Not confirmed'}",
            "",
            "Available evidence (verify facts against original documents):",
            *[f"- {doc.name} [document {doc.id}]" for doc in documents],
            "",
            "Attorney to complete: liability analysis, causation, verified expenses, liens, applicable law, demand amount, exhibits and recipient.",
            "Approval of this packet does not send a demand or establish eligibility, damages or liability.",
        ]
    )
    db.add(Approval(case_id=case.id, kind="demand", title="Demand preparation packet", body=body))
