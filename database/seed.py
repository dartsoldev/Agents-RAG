"""Seed clearly fictional demo cases and evidence; never seed in real mode."""

import hashlib
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import select

from backend.config import settings
from backend.security import hash_password
from database.models import Case, Document, User, uid
from database.session import SessionLocal
from orchestrator.engine import enqueue
from sub_agents.common import audit
from sub_agents.intake_agent import run as intake


def bootstrap():
    with SessionLocal() as db:
        if not db.scalar(select(User).limit(1)):
            db.add(
                User(
                    email=settings.admin_email.lower(),
                    name="Firm Administrator",
                    role="admin",
                    password_hash=hash_password(settings.admin_password),
                )
            )
        if settings.demo_mode and settings.seed_demo and not db.scalar(select(Case).limit(1)):
            today = date.today()
            examples = [
                (
                    "John Smith",
                    "Auto accident",
                    "treatment",
                    "Neck and lower back pain",
                    "NY",
                ),
                (
                    "Olivia Bennett",
                    "Premises liability",
                    "documents",
                    "Left ankle injury",
                    "NY",
                ),
                ("Marcus Johnson", "Auto accident", "intake", "Shoulder pain", "NJ"),
                ("Sophia Chen", "Auto accident", "treatment", "Wrist injury", "NY"),
            ]
            for index, (name, kind, stage, injuries, jurisdiction) in enumerate(examples):
                accident = (today - timedelta(days=40 + index * 7)).isoformat()
                case = Case(
                    client_name=name,
                    email=name.lower().replace(" ", ".") + "@example.com",
                    phone="+1 202-555-010" + str(index),
                    accident_date=accident,
                    jurisdiction=jurisdiction,
                    case_type=kind,
                    injuries=injuries,
                    attorney="Sarah Mitchell",
                    paralegal="Mike Davis",
                    stage=stage,
                )
                db.add(case)
                db.flush()
                intake(db, case)
                audit(db, case.id, "demo seed", "Fictional demo case created")
                if index == 0:
                    last = (today - timedelta(days=18)).isoformat()
                    case.medical = {
                        "provider": "Riverside Medical Center (fictional)",
                        "diagnosis": "Cervical strain; lumbar strain",
                        "treatment": "Physical therapy",
                        "last_visit": last,
                        "status": "ongoing",
                        "bills_cents": 1245000,
                    }
                    case.insurance = {
                        "carrier": "ABC Insurance (fictional)",
                        "claim_number": "DEMO-778899",
                        "policy_number": "DEMO-100",
                        "adjuster": "David Miller",
                        "last_response": (today - timedelta(days=12)).isoformat(),
                        "policy_limit_cents": 10000000,
                        "offer_cents": 0,
                        "liability": "Attorney review pending",
                    }
                    docs = [
                        (
                            "medical",
                            "John Smith - medical record.txt",
                            f"FICTIONAL DEMO RECORD\nPatient: John Smith\nAccident date: {accident}\nDiagnosis: Cervical strain and lumbar strain.\nInjuries: Neck and lower back pain.\nTreatment: Physical therapy.\nFirst treatment date: {(today - timedelta(days=38)).isoformat()}\nLast recorded visit: {last}\nProvider: Riverside Medical Center (fictional).",
                        ),
                        (
                            "insurance",
                            "John Smith - insurance.txt",
                            "FICTIONAL DEMO RECORD\nClient: John Smith\nCarrier: ABC Insurance (fictional)\nClaim number: DEMO-778899\nPolicy limit: $100,000\nCoverage is unverified pending attorney review.",
                        ),
                        (
                            "bills",
                            "John Smith - medical bills.txt",
                            "FICTIONAL DEMO RECORD\nClient: John Smith\nMedical expenses recorded: $12,450.00\nBilling total requires verification against original invoices.",
                        ),
                    ]
                    for category, filename, content in docs:
                        key = uid() + ".txt"
                        encoded = content.encode()
                        (Path(settings.storage_path) / key).write_bytes(encoded)
                        document = Document(
                            case_id=case.id,
                            name=filename,
                            category=category,
                            storage_key=key,
                            sha256=hashlib.sha256(encoded).hexdigest(),
                        )
                        db.add(document)
                        db.flush()
                        enqueue(db, case.id, "document", {"document_id": document.id})
                    enqueue(db, case.id, "monitor")
        db.commit()
