"""Track unverified coverage and adjuster response gaps using recorded facts."""

from datetime import date

from backend.config import settings
from sub_agents.common import task


def run(db, case):
    insurance = case.insurance or {}
    if not insurance.get("policy_limit_cents"):
        task(
            db,
            case.id,
            "insurance:coverage",
            "Verify coverage and policy limits with insurer",
            "insurance",
        )
    last = insurance.get("last_response")
    if last and (date.today() - date.fromisoformat(last)).days >= settings.insurance_gap_days:
        task(
            db,
            case.id,
            f"insurance:gap:{last}",
            f"Follow up with adjuster: last response {last}",
            "insurance",
            0,
            "high",
        )
