"""Retrieve within one case and reject answers with unsupported or invalid citations."""

import json
import math
import re

from sqlalchemy import select

from backend.config import settings
from database.models import Case, Chunk, Document
from integrations.ai_provider import Answer, Verification, embed, structured

STOPWORDS = set(
    [
        "what",
        "which",
        "when",
        "where",
        "who",
        "how",
        "does",
        "did",
        "have",
        "has",
        "the",
        "a",
        "an",
        "of",
        "is",
        "are",
        "was",
        "were",
        "to",
        "in",
        "on",
        "for",
        "and",
        "client",
        "patient",
        "please",
        "documented",
        "recorded",
        "available",
        "case",
        "documents",
        "evidence",
        "about",
        "tell",
        "me",
        "show",
        "record",
        "records",
    ]
)
SYNONYMS = {
    "injuries": ["injury", "diagnosis", "strain", "pain"],
    "injury": ["diagnosis", "strain", "pain"],
    "treatment": ["therapy", "visit", "treated"],
    "insurance": ["coverage", "policy", "carrier"],
    "start": ["first", "started"],
    "started": ["first", "start"],
}


def tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOPWORDS


def question_terms(db, case_id, question):
    case = db.get(Case, case_id)
    # A client's name alone cannot establish evidence for a medical or legal question.
    return tokens(question) - tokens(case.client_name if case else "")


def retrieve(db, case_id, question):
    rows = list(
        db.execute(
            select(Chunk, Document.name)
            .join(Document, Chunk.document_id == Document.id)
            .where(
                Chunk.case_id == case_id,
                Document.case_id == case_id,
                Document.status == "ready",
            )
        )
    )
    query = question_terms(db, case_id, question)
    expanded = query | {word for token in query for word in SYNONYMS.get(token, [])}
    vector = embed([question])[0] if settings.embeddings_enabled and rows else None
    ranked = []
    for chunk, name in rows:
        words = tokens(chunk.text)
        score = len(expanded & words) / max(1, len(expanded))
        if vector and chunk.embedding and len(vector) == len(chunk.embedding):
            dot = sum(a * b for a, b in zip(vector, chunk.embedding))
            norm = math.sqrt(sum(a * a for a in vector) * sum(b * b for b in chunk.embedding))
            score += max(0, dot / (norm or 1))
        if score > 0:
            ranked.append(
                (
                    score,
                    {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "name": name,
                        "page": chunk.page,
                        "text": chunk.text,
                    },
                )
            )
    return [item for _, item in sorted(ranked, key=lambda pair: pair[0], reverse=True)[:6]]


def answer_question(db, case_id, question):
    sources = retrieve(db, case_id, question)
    empty = {
        "answer": "Not enough evidence in the available case documents to answer this question.",
        "insufficient": True,
        "citations": [],
        "mode": settings.ai_provider,
    }
    if not sources:
        return empty
    if settings.ai_provider == "demo":
        # Demo is deliberately extractive, never masquerading as an LLM interpretation.
        terms = question_terms(db, case_id, question)
        terms |= {word for token in list(terms) for word in SYNONYMS.get(token, [])}
        excerpts = []
        for source in sources:
            lines = [line.strip() for line in source["text"].splitlines() if tokens(line) & terms]
            if lines:
                quote = lines[0][:400]
                excerpts.append({**source, "quote": quote})
        if not excerpts:
            return empty
        return {
            "answer": "Matching document excerpts (demo retrieval; review their context):\n\n"
            + "\n\n".join(s["quote"] for s in excerpts[:3]),
            "insufficient": False,
            "citations": [{k: v for k, v in s.items() if k != "text"} for s in excerpts[:3]],
            "mode": "demo",
        }
    context = json.dumps({"question": question, "passages": sources})
    result = structured("research.md", context, Answer)
    if result.insufficient:
        return empty
    indexed = {s["chunk_id"]: s for s in sources}
    if not result.citations:
        return empty
    citations = []
    for citation in result.citations:
        source = indexed.get(citation.chunk_id)
        if not source or not citation.quote.strip() or citation.quote not in source["text"]:
            return empty
        citations.append(
            {k: v for k, v in {**source, "quote": citation.quote}.items() if k != "text"}
        )
    check = structured(
        "verification.md",
        json.dumps(
            {
                "question": question,
                "candidate": result.model_dump(),
                "passages": sources,
            }
        ),
        Verification,
    )
    if not check.supported:
        return empty
    return {
        "answer": result.answer,
        "insufficient": False,
        "citations": citations,
        "mode": "openai",
    }
