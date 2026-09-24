"""Consolidate open work into one reviewable client follow-up draft."""

from sqlalchemy import select

from database.models import Approval, Task


def run(db, case):
    pending = db.scalar(
        select(Approval).where(
            Approval.case_id == case.id,
            Approval.kind == "follow_up",
            Approval.status == "pending",
        )
    )
    tasks = list(db.scalars(select(Task).where(Task.case_id == case.id, Task.completed == False)))
    if pending or not tasks:
        return
    # Internal legal/conflict tasks are never copied into client correspondence.
    requests = [
        t.title
        for t in tasks
        if t.agent == "intake" and t.dedupe_key.split(":")[-2:-1] == ["collect"]
    ]
    if requests:
        db.add(
            Approval(
                case_id=case.id,
                kind="follow_up",
                title="Document collection follow-up",
                body=f"Hello {case.client_name},\n\nOur team is following up on the following items:\n"
                + "\n".join(f"- {t}" for t in requests)
                + "\n\nPlease coordinate secure delivery with your paralegal. Thank you.",
                payload={"to": case.email},
            )
        )
