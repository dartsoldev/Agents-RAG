"""Run one polling worker per installation with periodic case monitoring."""

import threading
import time

from sqlalchemy import select

from backend.config import settings
from database.models import Case, Job
from database.session import SessionLocal
from orchestrator.engine import enqueue, mark_stale_jobs, run_next


def worker_loop(stop: threading.Event):
    last_monitor = time.monotonic()
    while not stop.is_set():
        try:
            mark_stale_jobs()
            if time.monotonic() - last_monitor >= settings.monitor_interval_seconds:
                with SessionLocal() as db:
                    cases = db.scalars(select(Case).where(Case.stage.not_in(["closed", "settled"])))
                    for case in cases:
                        pending = db.scalar(
                            select(Job).where(
                                Job.case_id == case.id,
                                Job.kind == "monitor",
                                Job.status.in_(["queued", "running"]),
                            )
                        )
                        if not pending:
                            enqueue(db, case.id, "monitor")
                    db.commit()
                last_monitor = time.monotonic()
            if not run_next():
                stop.wait(1)
        except Exception:
            # Keep the loop alive through a temporary database outage; do not log case contents.
            stop.wait(5)


if __name__ == "__main__":
    worker_loop(threading.Event())
