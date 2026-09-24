"""Exercise complete case flow, authorization, evidence isolation and failure recovery."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.main import app
from backend.routes import auth_attempts
from database.models import Chunk
from database.session import SessionLocal
from orchestrator.engine import run_next


def make_case(client, email="john@example.com"):
    response = client.post(
        "/api/cases",
        json={
            "client_name": "John Smith",
            "email": email,
            "accident_date": (date.today() - timedelta(days=40)).isoformat(),
            "jurisdiction": "NY",
            "injuries": "Neck pain",
        },
    )
    assert response.status_code == 201, response.text
    drain()
    return response.json()["id"]


def drain():
    for _ in range(100):
        if not run_next():
            return
    raise AssertionError("Workflow queue did not drain")


def upload(client, case_id, category, content):
    response = client.post(
        f"/api/cases/{case_id}/documents",
        data={"category": category},
        files={"file": (category + ".txt", content, "text/plain")},
    )
    assert response.status_code == 201, response.text
    drain()
    return response.json()


def test_end_to_end_intake_evidence_monitor_demand_settlement(client):
    case_id = make_case(client)
    case = client.get(f"/api/cases/{case_id}").json()
    assert len(case["tasks"]) == 6
    assert len(case["approvals"]) == 1
    upload(
        client,
        case_id,
        "medical",
        "Patient: John Smith\nDiagnosis: Cervical strain.\nTreatment: Physical therapy.",
    )
    upload(client, case_id, "insurance", "Carrier: ABC Insurance\nPolicy limit: $100,000")
    upload(client, case_id, "bills", "Medical bills: $12,450")
    research = client.post(
        f"/api/cases/{case_id}/research",
        json={"question": "What injuries are documented?"},
    ).json()
    assert research["citations"] and "Cervical strain" in research["answer"]
    unknown = client.post(
        f"/api/cases/{case_id}/research",
        json={"question": "Did the patient undergo surgery?"},
    ).json()
    assert unknown["insufficient"] and unknown["citations"] == []
    assert (
        client.put(
            f"/api/cases/{case_id}/medical",
            json={
                "status": "ongoing",
                "last_visit": (date.today() - timedelta(days=20)).isoformat(),
            },
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/api/cases/{case_id}/insurance",
            json={
                "last_response": (date.today() - timedelta(days=15)).isoformat(),
                "offer_cents": 2500000,
            },
        ).status_code
        == 200
    )
    drain()
    tasks = client.get(f"/api/cases/{case_id}").json()["tasks"]
    assert any(t["agent"] == "medical" and t["priority"] == "high" for t in tasks)
    assert any(t["agent"] == "insurance" and t["priority"] == "high" for t in tasks)
    for stage in ["documents", "treatment"]:
        assert (
            client.post(
                f"/api/cases/{case_id}/stage",
                json={"stage": stage, "note": "Attorney reviewed"},
            ).status_code
            == 200
        )
    assert (
        client.post(
            f"/api/cases/{case_id}/stage",
            json={"stage": "demand", "note": "Attorney reviewed"},
        ).status_code
        == 409
    )
    client.put(
        f"/api/cases/{case_id}/medical",
        json={"status": "complete", "bills_cents": 1245000},
    )
    client.post(f"/api/cases/{case_id}/workflows/demand")
    drain()
    packet = next(
        a for a in client.get(f"/api/cases/{case_id}").json()["approvals"] if a["kind"] == "demand"
    )
    assert (
        client.post(
            f"/api/approvals/{packet['id']}/review",
            json={"decision": "approved", "note": "Reviewed evidence"},
        ).status_code
        == 200
    )
    for stage in ["demand", "negotiation", "settled", "closed"]:
        response = client.post(
            f"/api/cases/{case_id}/stage",
            json={
                "stage": stage,
                "settlement_cents": 7500000 if stage == "settled" else None,
                "note": "Attorney and client decision recorded",
            },
        )
        assert response.status_code == 200, response.text
    case = client.get(f"/api/cases/{case_id}").json()
    assert case["stage"] == "closed" and case["settlement_cents"] == 7500000
    assert len(case["audit"]) >= 10


def test_auth_csrf_and_paralegal_cannot_approve(client):
    case_id = make_case(client)
    with TestClient(app) as anonymous:
        assert anonymous.get("/api/cases").status_code == 401
        assert (
            anonymous.post(
                "/api/auth/login", json={"email": "admin@arav.local", "password": "bad"}
            ).status_code
            == 403
        )
    assert (
        client.post("/api/cases", json={}, headers={"Origin": "https://evil.example"}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/users",
            json={
                "name": "Mike Davis",
                "email": "mike@example.com",
                "role": "paralegal",
                "password": "StrongPassword123!",
            },
        ).status_code
        == 201
    )
    client.post("/api/auth/logout")
    assert client.get("/api/cases").status_code == 401
    client.post(
        "/api/auth/login",
        json={"email": "mike@example.com", "password": "StrongPassword123!"},
    )
    assert client.get("/api/users").status_code == 403
    assert (
        client.post(
            f"/api/cases/{case_id}/stage",
            json={"stage": "documents", "note": "Tried changing stage"},
        ).status_code
        == 403
    )
    approval = client.get(f"/api/cases/{case_id}").json()["approvals"][0]
    assert (
        client.post(
            f"/api/approvals/{approval['id']}/review", json={"decision": "approved"}
        ).status_code
        == 403
    )


def test_duplicate_intake_documents_and_monitor_idempotency(client):
    case_id = make_case(client)
    assert (
        client.post(
            "/api/cases",
            json={
                "client_name": "John Smith",
                "email": "JOHN@example.com",
                "accident_date": (date.today() - timedelta(days=40)).isoformat(),
                "jurisdiction": "NY",
            },
        ).status_code
        == 409
    )
    upload(client, case_id, "medical", "Diagnosis: Cervical strain")
    assert (
        client.post(
            f"/api/cases/{case_id}/documents",
            data={"category": "medical"},
            files={"file": ("copy.txt", "Diagnosis: Cervical strain")},
        ).status_code
        == 409
    )
    for _ in range(3):
        client.post(f"/api/cases/{case_id}/workflows/monitor")
        drain()
    case = client.get(f"/api/cases/{case_id}").json()
    assert len({t["dedupe_key"] for t in case["tasks"]}) == len(case["tasks"])
    assert len([a for a in case["approvals"] if a["kind"] == "follow_up"]) == 1


def test_retrieval_cannot_leak_another_case(client):
    a, b = make_case(client), make_case(client, "other@example.com")
    upload(client, a, "medical", "Diagnosis: ConfidentialZebra diagnosis")
    result = client.post(
        f"/api/cases/{b}/research",
        json={"question": "What is the ConfidentialZebra diagnosis?"},
    ).json()
    assert result["insufficient"]
    with SessionLocal() as db:
        chunk = db.scalar(select(Chunk).where(Chunk.case_id == a))
        assert client.get(f"/api/cases/{b}/evidence/{chunk.id}").status_code == 404


def test_corrupt_document_failure_visible_and_retryable(client):
    case_id = make_case(client)
    response = client.post(
        f"/api/cases/{case_id}/documents",
        data={"category": "medical"},
        files={"file": ("bad.pdf", b"not a pdf")},
    )
    assert response.status_code == 201
    drain()
    case = client.get(f"/api/cases/{case_id}").json()
    assert case["documents"][0]["status"] == "failed"
    job = next(j for j in case["jobs"] if j["kind"] == "document")
    assert job["error"] and job["status"] == "failed"
    assert client.post(f"/api/jobs/{job['id']}/retry").status_code == 200
    drain()
    assert client.get(f"/api/cases/{case_id}").json()["documents"][0]["status"] == "failed"


def test_approved_email_simulated_once_and_review_cannot_repeat(client):
    case_id = make_case(client)
    approval = client.get(f"/api/cases/{case_id}").json()["approvals"][0]
    path = f"/api/approvals/{approval['id']}"
    assert client.post(path + "/send").status_code == 409
    assert (
        client.post(
            path + "/review",
            json={"decision": "approved", "body": "Reviewed welcome text"},
        ).status_code
        == 200
    )
    assert client.post(path + "/review", json={"decision": "rejected"}).status_code == 409
    assert client.post(path + "/send").json()["status"] == "simulated"
    assert client.post(path + "/send").status_code == 409


def test_invalid_stage_negative_money_unsupported_upload_and_calendar(client):
    case_id = make_case(client)
    assert (
        client.post(
            f"/api/cases/{case_id}/stage",
            json={"stage": "settled", "settlement_cents": 500, "note": "Skip stages"},
        ).status_code
        == 409
    )
    assert (
        client.put(f"/api/cases/{case_id}/insurance", json={"offer_cents": -1}).status_code == 422
    )
    assert (
        client.post(
            f"/api/cases/{case_id}/documents", files={"file": ("malware.exe", b"data")}
        ).status_code
        == 415
    )
    assert "BEGIN:VCALENDAR" in client.get("/api/tasks/calendar.ics").text
    assert client.get("/api/settings").json()["demo_mode"] is True
    assert "password" not in client.get("/api/settings").text.lower()


def test_login_rate_limit(client):
    client.post("/api/auth/logout")
    auth_attempts.clear()
    for _ in range(15):
        assert (
            client.post(
                "/api/auth/login",
                json={"email": "admin@arav.local", "password": "wrong"},
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/auth/login", json={"email": "admin@arav.local", "password": "wrong"}
        ).status_code
        == 429
    )
