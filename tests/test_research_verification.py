"""Reject malformed AI citations and failed semantic verification without paid model calls."""

from backend.config import settings
from database.models import Case, Chunk, Document
from database.session import SessionLocal
from integrations.ai_provider import Answer, Citation, Verification
from sub_agents import research_agent


def seed_evidence(db):
    case = Case(
        client_name="Evidence Test",
        email="evidence@example.com",
        accident_date="2026-01-01",
        jurisdiction="NY",
    )
    db.add(case)
    db.flush()
    document = Document(
        case_id=case.id,
        name="record.txt",
        storage_key="unused.txt",
        sha256="a" * 64,
        status="ready",
    )
    db.add(document)
    db.flush()
    chunk = Chunk(
        case_id=case.id, document_id=document.id, page=1, text="Diagnosis: Cervical strain."
    )
    db.add(chunk)
    db.commit()
    return case, chunk


def test_fabricated_quote_is_rejected(monkeypatch, client):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    with SessionLocal() as db:
        case, chunk = seed_evidence(db)
        monkeypatch.setattr(
            research_agent,
            "structured",
            lambda *args: Answer(
                answer="Surgery was performed.",
                insufficient=False,
                citations=[Citation(chunk_id=chunk.id, quote="Surgery was performed.")],
            ),
        )
        result = research_agent.answer_question(db, case.id, "What diagnosis is documented?")
        assert result["insufficient"] and result["citations"] == []


def test_client_name_is_not_evidence_of_surgery(client):
    with SessionLocal() as db:
        case, chunk = seed_evidence(db)
        case.client_name = "Olivia Bennett"
        chunk.text = "Patient: Olivia Bennett. Diagnosis: Cervical strain."
        db.commit()
        result = research_agent.answer_question(db, case.id, "Did Olivia Bennett have surgery?")
        assert result["insufficient"] and not result["citations"]


def test_other_case_source_id_is_rejected(monkeypatch, client):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    with SessionLocal() as db:
        case, chunk = seed_evidence(db)
        monkeypatch.setattr(
            research_agent,
            "structured",
            lambda *args: Answer(
                answer="Cervical strain.",
                insufficient=False,
                citations=[Citation(chunk_id="foreign-case-chunk", quote="Cervical strain.")],
            ),
        )
        assert research_agent.answer_question(db, case.id, "What diagnosis?")["insufficient"]


def test_verifier_rejection_and_supported_answer(monkeypatch, client):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    with SessionLocal() as db:
        case, chunk = seed_evidence(db)
        for supported in [False, True]:

            def mocked(name, content, output_type):
                if name == "research.md":
                    return Answer(
                        answer="The record states cervical strain.",
                        insufficient=False,
                        citations=[
                            Citation(chunk_id=chunk.id, quote="Diagnosis: Cervical strain.")
                        ],
                    )
                return Verification(supported=supported, reason="Test verifier result")

            monkeypatch.setattr(research_agent, "structured", mocked)
            result = research_agent.answer_question(db, case.id, "What diagnosis?")
            assert result["insufficient"] is not supported
            if supported:
                assert result["citations"][0]["document_id"] == chunk.document_id
