"""Shared idempotent task creation and audit helpers for workflow workers."""

from datetime import date, timedelta

from sqlalchemy import select

from database.models import Audit, Task


def task(db, case_id, key, title, agent, days=2, priority="normal"):
    dedupe = f"{case_id}:{key}"
    existing = db.scalar(select(Task).where(Task.dedupe_key == dedupe))
    if existing:
        return existing
    item = Task(
        case_id=case_id,
        dedupe_key=dedupe,
        title=title,
        agent=agent,
        due_date=(date.today() + timedelta(days=days)).isoformat(),
        priority=priority,
    )
    db.add(item)
    return item


def audit(db, case_id, actor, action, detail=""):
    db.add(Audit(case_id=case_id, actor=actor, action=action, detail=detail))
