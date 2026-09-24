"""Flag missing treatment records from staff-confirmed dates; never diagnose clients."""

from datetime import date

from backend.config import settings
from sub_agents.common import task


def run(db, case):
    medical = case.medical or {}
    if medical.get("status") == "complete":
        return
    last = medical.get("last_visit")
    if not last:
        task(
            db,
            case.id,
            "medical:provider",
            "Confirm medical provider and last treatment date",
            "medical",
        )
    elif (date.today() - date.fromisoformat(last)).days >= settings.medical_gap_days:
        task(
            db,
            case.id,
            f"medical:gap:{last}",
            f"Request treatment update: last recorded visit {last}",
            "medical",
            0,
            "high",
        )
