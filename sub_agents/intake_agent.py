"""Create intake collection tasks and a welcome draft without sending messages."""

from sqlalchemy import select

from database.models import Approval
from sub_agents.common import task

REQUIRED = {
    "identity": "Request driver's license",
    "insurance": "Request insurance card",
    "police": "Request police report",
    "medical": "Request medical records",
    "bills": "Request medical bills",
}


def run(db, case):
    for category, title in REQUIRED.items():
        task(db, case.id, f"collect:{category}", title, "intake")
    task(
        db,
        case.id,
        "eligibility",
        "Attorney: review eligibility, conflicts and applicable deadlines",
        "intake",
        0,
        "high",
    )
    existing = db.scalar(
        select(Approval).where(Approval.case_id == case.id, Approval.kind == "welcome")
    )
    if not existing:
        db.add(
            Approval(
                case_id=case.id,
                kind="welcome",
                title="Welcome email",
                body=f"Hello {case.client_name},\n\nThank you for contacting our team. Please contact your paralegal to arrange secure delivery of your insurance card, police report, identification and medical records. Your attorney will review the information and confirm next steps.\n\nArav Law Firm",
                payload={"to": case.email},
            )
        )
