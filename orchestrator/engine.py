"""Claim durable jobs atomically and run narrow agents inside a transaction."""

from datetime import timedelta

from sqlalchemy import select, update

from database.models import Case, Document, Job, now
from database.session import SessionLocal
from sub_agents import (
    demand_agent,
    document_agent,
    follow_up_agent,
    insurance_agent,
    intake_agent,
    medical_agent,
)
from sub_agents.common import audit


def enqueue(db, case_id, kind, payload=None):
    job = Job(case_id=case_id, kind=kind, payload=payload or {})
    db.add(job)
    db.flush()
    return job


def run_next():
    with SessionLocal() as db:
        candidate = db.scalar(
            select(Job).where(Job.status == "queued").order_by(Job.created_at).limit(1)
        )
        if candidate is None:
            return False
        claimed = db.execute(
            update(Job)
            .where(Job.id == candidate.id, Job.status == "queued")
            .values(status="running", started_at=now(), attempts=Job.attempts + 1)
        )
        db.commit()
        if claimed.rowcount != 1:
            return True
        job_id = candidate.id
    try:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            case = db.get(Case, job.case_id)
            if case.stage in {"closed", "settled"} and job.kind == "monitor":
                pass
            elif job.kind == "intake":
                intake_agent.run(db, case)
            elif job.kind == "document":
                document = db.get(Document, job.payload["document_id"])
                if not document or document.case_id != case.id:
                    raise ValueError("Document does not belong to this case")
                document_agent.run(db, case, document)
            elif job.kind == "monitor":
                medical_agent.run(db, case)
                insurance_agent.run(db, case)
                db.flush()
                follow_up_agent.run(db, case)
            elif job.kind == "demand":
                demand_agent.run(db, case)
            else:
                raise ValueError("Unsupported workflow")
            job.status, job.finished_at = "completed", now()
            audit(
                db,
                case.id,
                "orchestrator",
                f"{job.kind} workflow completed",
                f"Run {job.id}",
            )
            db.commit()
    except Exception as exc:
        with SessionLocal() as db:
            job = db.get(Job, job_id)
            # Only expected validation errors are shown; provider errors may contain PHI or secrets.
            message = (
                str(exc)[:500]
                if isinstance(exc, ValueError)
                else f"{type(exc).__name__}: processing failed; check provider configuration or document format"
            )
            job.status, job.error, job.finished_at = "failed", message, now()
            if job.kind == "document":
                document = db.get(Document, job.payload.get("document_id"))
                if document:
                    document.status, document.error = "failed", message
            audit(
                db,
                job.case_id,
                "orchestrator",
                "Workflow failed",
                f"Run {job.id}: {message}",
            )
            db.commit()
    return True


def mark_stale_jobs():
    # Conservative recovery: never automatically repeat a possibly partial operation.
    with SessionLocal() as db:
        db.execute(
            update(Job)
            .where(Job.status == "running", Job.started_at < now() - timedelta(minutes=30))
            .values(
                status="failed",
                error="Worker interrupted or timed out. Review and retry this local workflow.",
            )
        )
        db.commit()
