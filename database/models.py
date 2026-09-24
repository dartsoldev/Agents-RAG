"""Define persisted cases, evidence, workflow jobs, approvals, sessions and audit events."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(UTC).replace(tzinfo=None)


def uid():
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class IdentityMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class User(IdentityMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(250), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))
    password_hash: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True)


class LoginSession(IdentityMixin, Base):
    __tablename__ = "login_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class Case(IdentityMixin, Base):
    __tablename__ = "cases"
    client_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(250), index=True)
    phone: Mapped[str] = mapped_column(String(60), default="")
    accident_date: Mapped[str] = mapped_column(String(10))
    jurisdiction: Mapped[str] = mapped_column(String(100))
    case_type: Mapped[str] = mapped_column(String(100), default="Auto accident")
    injuries: Mapped[str] = mapped_column(Text, default="")
    attorney: Mapped[str] = mapped_column(String(120), default="Unassigned")
    paralegal: Mapped[str] = mapped_column(String(120), default="Unassigned")
    stage: Mapped[str] = mapped_column(String(30), default="intake", index=True)
    medical: Mapped[dict] = mapped_column(JSON, default=dict)
    insurance: Mapped[dict] = mapped_column(JSON, default=dict)
    settlement_cents: Mapped[int | None] = mapped_column(BigInteger, default=None)
    filevine_project_id: Mapped[str | None] = mapped_column(String(100), default=None)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    __table_args__ = (UniqueConstraint("email", "accident_date", name="uq_case_intake"),)


class Document(IdentityMixin, Base):
    __tablename__ = "documents"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    name: Mapped[str] = mapped_column(String(250))
    storage_key: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64))
    category: Mapped[str] = mapped_column(String(40), default="other")
    status: Mapped[str] = mapped_column(String(30), default="queued")
    summary: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (UniqueConstraint("case_id", "sha256", name="uq_document_content"),)


class Chunk(IdentityMixin, Base):
    __tablename__ = "chunks"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), index=True)
    page: Mapped[int] = mapped_column(default=1)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)


class Task(IdentityMixin, Base):
    __tablename__ = "tasks"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    title: Mapped[str] = mapped_column(String(250))
    agent: Mapped[str] = mapped_column(String(30), default="team")
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    due_date: Mapped[str] = mapped_column(String(10))
    completed: Mapped[bool] = mapped_column(default=False)
    dedupe_key: Mapped[str] = mapped_column(String(250), unique=True)


class Approval(IdentityMixin, Base):
    __tablename__ = "approvals"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(250))
    body: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_note: Mapped[str] = mapped_column(Text, default="")


class Job(IdentityMixin, Base):
    __tablename__ = "jobs"
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    error: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Audit(IdentityMixin, Base):
    __tablename__ = "audit_events"
    case_id: Mapped[str | None] = mapped_column(ForeignKey("cases.id"), index=True, nullable=True)
    actor: Mapped[str] = mapped_column(String(150))
    action: Mapped[str] = mapped_column(String(100))
    detail: Mapped[str] = mapped_column(Text, default="")
