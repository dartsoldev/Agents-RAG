"""Authenticated API for cases, evidence, research, tasks, approvals and configuration status."""

import hashlib
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import timedelta
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.config import settings
from backend.schemas import (
    CaseInput,
    DecisionInput,
    FilevineLinkInput,
    InsuranceInput,
    LoginInput,
    MedicalInput,
    QuestionInput,
    StageInput,
    TaskInput,
    TaskUpdate,
    UserInput,
)
from backend.security import (
    current_user,
    hash_password,
    require_admin,
    require_reviewer,
    token_digest,
    verify_password,
)
from backend.services import (
    STAGES,
    case_detail,
    get_case,
    row_dict,
    validate_transition,
)
from database.models import (
    Approval,
    Audit,
    Case,
    Chunk,
    Document,
    Job,
    LoginSession,
    Task,
    User,
    now,
    uid,
)
from database.session import get_db
from integrations.email_provider import deliver
from integrations.filevine_provider import get_project
from orchestrator.engine import enqueue
from sub_agents.common import audit
from sub_agents.document_agent import ALLOWED_EXTENSIONS
from sub_agents.research_agent import answer_question

router = APIRouter(prefix="/api")
auth_attempts = defaultdict(deque)
rate_lock = threading.Lock()
DUMMY_HASH = hash_password(secrets.token_urlsafe(32))


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@router.post("/auth/login")
def login(
    data: LoginInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    key = request.client.host if request.client else "local"
    with rate_lock:
        cutoff = time.monotonic() - 300
        for old_key in list(auth_attempts):
            while auth_attempts[old_key] and auth_attempts[old_key][0] < cutoff:
                auth_attempts[old_key].popleft()
            if not auth_attempts[old_key]:
                del auth_attempts[old_key]
        attempts = auth_attempts[key]
        if len(attempts) >= 15:
            raise HTTPException(429, "Too many login attempts. Wait five minutes.")
        attempts.append(time.monotonic())
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    valid = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if not user or not valid or not user.active:
        raise HTTPException(401, "Invalid email or password")
    token = secrets.token_urlsafe(48)
    db.execute(delete(LoginSession).where(LoginSession.expires_at < now()))
    db.add(
        LoginSession(
            token_hash=token_digest(token),
            user_id=user.id,
            expires_at=now() + timedelta(hours=8),
        )
    )
    audit(db, None, user.email, "Signed in")
    db.commit()
    response.set_cookie(
        "arav_session",
        token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        max_age=28800,
    )
    return row_dict(user, ("password_hash",))


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    db.execute(
        delete(LoginSession).where(
            LoginSession.token_hash == token_digest(request.cookies.get("arav_session", ""))
        )
    )
    db.commit()
    response.delete_cookie("arav_session")
    return {"ok": True}


@router.get("/auth/me")
def me(user=Depends(current_user)):
    return row_dict(user, ("password_hash",))


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user=Depends(current_user)):
    stages = dict(db.execute(select(Case.stage, func.count()).group_by(Case.stage)).all())
    tasks = db.scalars(select(Task).where(Task.completed == False).order_by(Task.due_date).limit(8))
    cases = {c.id: c.client_name for c in db.scalars(select(Case))}
    return {
        "total_cases": sum(stages.values()),
        "stages": stages,
        "open_tasks": db.scalar(
            select(func.count()).select_from(Task).where(Task.completed == False)
        ),
        "pending_approvals": db.scalar(
            select(func.count()).select_from(Approval).where(Approval.status == "pending")
        ),
        "ready_documents": db.scalar(
            select(func.count()).select_from(Document).where(Document.status == "ready")
        ),
        "tasks": [{**row_dict(t), "client_name": cases.get(t.case_id)} for t in tasks],
        "recent_activity": [
            row_dict(a)
            for a in db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(8))
        ],
    }


@router.get("/cases")
def list_cases(
    q: str = "",
    stage: str = "",
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    query = select(Case)
    if q:
        query = query.where(Case.client_name.ilike(f"%{q[:150]}%"))
    if stage:
        query = query.where(Case.stage == stage)
    return [row_dict(c) for c in db.scalars(query.order_by(Case.updated_at.desc()).limit(1000))]


@router.post("/cases", status_code=201)
def create_case(data: CaseInput, db: Session = Depends(get_db), user=Depends(current_user)):
    case = Case(**data.model_dump(mode="json"))
    db.add(case)
    try:
        db.flush()
        enqueue(db, case.id, "intake")
        audit(
            db,
            case.id,
            user.email,
            "Case created",
            "Intake queued; eligibility requires attorney review",
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "A case with this email and accident date already exists")
    return row_dict(case)


@router.get("/cases/{case_id}")
def read_case(case_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    return case_detail(db, get_case(db, case_id))


@router.get("/cases/{case_id}/export")
def export_case(case_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    case = get_case(db, case_id)
    audit(db, case.id, user.email, "Case export downloaded")
    db.commit()
    return case_detail(db, case)


@router.put("/cases/{case_id}/medical")
def update_medical(
    case_id: str,
    data: MedicalInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    case = get_case(db, case_id)
    case.medical = data.model_dump(mode="json")
    enqueue(db, case.id, "monitor")
    audit(db, case.id, user.email, "Medical tracking updated", "Staff-entered facts")
    db.commit()
    return row_dict(case)


@router.put("/cases/{case_id}/insurance")
def update_insurance(
    case_id: str,
    data: InsuranceInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    case = get_case(db, case_id)
    old_offer = case.insurance.get("offer_cents", 0)
    case.insurance = data.model_dump(mode="json")
    if data.offer_cents and data.offer_cents != old_offer:
        db.add(
            Approval(
                case_id=case.id,
                kind="offer",
                title="New settlement offer",
                body=f"Recorded offer: ${data.offer_cents / 100:,.2f}. Attorney to review with client. Approval records review only; it does not accept this offer.",
                payload={"offer_cents": data.offer_cents},
            )
        )
    enqueue(db, case.id, "monitor")
    audit(db, case.id, user.email, "Insurance tracking updated")
    db.commit()
    return row_dict(case)


@router.post("/cases/{case_id}/stage")
def change_stage(
    case_id: str,
    data: StageInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    require_reviewer(user)
    case = get_case(db, case_id)
    validate_transition(db, case, data.stage, data.settlement_cents)
    previous = case.stage
    changed = db.execute(
        update(Case)
        .where(Case.id == case_id, Case.stage == previous)
        .values(
            stage=data.stage,
            **({"settlement_cents": data.settlement_cents} if data.stage == "settled" else {}),
        )
    )
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Stage changed concurrently. Refresh and review again.")
    audit(db, case.id, user.email, f"Stage: {previous} → {data.stage}", data.note)
    db.commit()
    return {"stage": data.stage}


@router.post("/cases/{case_id}/documents", status_code=201)
def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    category: str = Form("other"),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    get_case(db, case_id)
    name = (file.filename or "document").replace("\\", "/").split("/")[-1][:250]
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Upload a searchable PDF, DOCX, UTF-8 TXT or MD file")
    if category not in {
        "medical",
        "insurance",
        "police",
        "identity",
        "bills",
        "legal",
        "other",
    }:
        raise HTTPException(422, "Unknown document category")
    content = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if not content or len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Upload must be between 1 byte and {settings.max_upload_mb} MB")
    digest = hashlib.sha256(content).hexdigest()
    if db.scalar(select(Document).where(Document.case_id == case_id, Document.sha256 == digest)):
        raise HTTPException(409, "This document is already uploaded to this case")
    key = f"{uid()}{suffix}"
    path = Path(settings.storage_path) / key
    path.write_bytes(content)
    document = Document(
        case_id=case_id, name=name, category=category, storage_key=key, sha256=digest
    )
    try:
        db.add(document)
        db.flush()
        enqueue(db, case_id, "document", {"document_id": document.id})
        audit(db, case_id, user.email, "Document uploaded", name)
        db.commit()
    except Exception:
        db.rollback()
        path.unlink(missing_ok=True)
        raise
    return row_dict(document, ("storage_key", "sha256"))


@router.get("/documents/{document_id}/download")
def download_document(document_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(404, "Document not found")
    path = Path(settings.storage_path) / document.storage_key
    if not path.is_file():
        raise HTTPException(404, "Document file missing; restore from backup")
    audit(db, document.case_id, user.email, "Document downloaded", document.id)
    db.commit()
    return FileResponse(path, filename=document.name, media_type="application/octet-stream")


@router.get("/cases/{case_id}/evidence/{chunk_id}")
def read_evidence(
    case_id: str,
    chunk_id: str,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    chunk = db.get(Chunk, chunk_id)
    if not chunk or chunk.case_id != case_id:
        raise HTTPException(404, "Evidence not found in this case")
    return row_dict(chunk, ("embedding",))


@router.post("/cases/{case_id}/research")
def research(
    case_id: str,
    data: QuestionInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    get_case(db, case_id)
    try:
        result = answer_question(db, case_id, data.question)
    except Exception:
        raise HTTPException(
            502,
            "Research provider unavailable. Check server configuration and try again; no answer was fabricated.",
        )
    audit(
        db,
        case_id,
        user.email,
        "Case research completed",
        f"Provider: {settings.ai_provider}; citations: {len(result['citations'])}",
    )
    db.commit()
    return result


@router.post("/cases/{case_id}/tasks", status_code=201)
def create_task(
    case_id: str,
    data: TaskInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    get_case(db, case_id)
    task = Task(case_id=case_id, dedupe_key=uid(), **data.model_dump(mode="json"))
    db.add(task)
    audit(db, case_id, user.email, "Task created", data.title)
    db.commit()
    return row_dict(task)


@router.patch("/tasks/{task_id}")
def update_task(
    task_id: str,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    task.completed = data.completed
    audit(
        db,
        task.case_id,
        user.email,
        "Task completed" if data.completed else "Task reopened",
        task.title,
    )
    db.commit()
    return row_dict(task)


@router.post("/cases/{case_id}/workflows/{kind}")
def run_workflow(
    case_id: str, kind: str, db: Session = Depends(get_db), user=Depends(current_user)
):
    get_case(db, case_id)
    if kind not in {"monitor", "demand"}:
        raise HTTPException(422, "Choose monitor or demand")
    existing = db.scalar(
        select(Job).where(
            Job.case_id == case_id,
            Job.kind == kind,
            Job.status.in_(["queued", "running"]),
        )
    )
    job = existing or enqueue(db, case_id, kind)
    db.commit()
    return row_dict(job)


@router.post("/jobs/{job_id}/retry")
def retry_job(job_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(404, "Run not found")
    changed = db.execute(
        update(Job)
        .where(Job.id == job_id, Job.status == "failed")
        .values(status="queued", error="", finished_at=None)
    )
    if not changed.rowcount:
        raise HTTPException(409, "Only failed runs can be retried")
    audit(db, job.case_id, user.email, "Workflow retry queued", job_id)
    db.commit()
    return {"status": "queued"}


@router.get("/approvals")
def approvals(db: Session = Depends(get_db), user=Depends(current_user)):
    return [
        {**row_dict(a), "client_name": name}
        for a, name in db.execute(
            select(Approval, Case.client_name)
            .join(Case)
            .order_by(Approval.created_at.desc())
            .limit(500)
        )
    ]


@router.post("/approvals/{approval_id}/review")
def review_approval(
    approval_id: str,
    data: DecisionInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    require_reviewer(user)
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")
    body = data.body if data.body is not None else approval.body
    if not body.strip():
        raise HTTPException(422, "Draft cannot be empty")
    changed = db.execute(
        update(Approval)
        .where(Approval.id == approval_id, Approval.status == "pending")
        .values(status=data.decision, reviewed_by=user.id, review_note=data.note, body=body)
    )
    if changed.rowcount != 1:
        raise HTTPException(409, "This item has already been reviewed")
    audit(db, approval.case_id, user.email, f"{approval.kind} {data.decision}", data.note)
    db.commit()
    return {"status": data.decision}


@router.post("/approvals/{approval_id}/send")
def send_approval(approval_id: str, db: Session = Depends(get_db), user=Depends(current_user)):
    require_reviewer(user)
    approval = db.get(Approval, approval_id)
    if not approval or approval.kind not in {"welcome", "follow_up"}:
        raise HTTPException(422, "Only reviewed client emails can be sent here")
    if not settings.demo_mode and not all(
        [
            settings.smtp_host,
            settings.smtp_username,
            settings.smtp_password,
            settings.smtp_from,
        ]
    ):
        raise HTTPException(409, "SMTP is not configured")
    claimed = db.execute(
        update(Approval)
        .where(Approval.id == approval_id, Approval.status == "approved")
        .values(status="sending")
    )
    if claimed.rowcount != 1:
        raise HTTPException(409, "Email must be approved and not previously sent")
    db.commit()
    try:
        status = deliver(approval)
    except Exception:
        approval.status = "delivery_unknown"
        audit(
            db,
            approval.case_id,
            user.email,
            "Email delivery uncertain",
            "Check SMTP provider before any manual resend",
        )
        db.commit()
        raise HTTPException(
            502,
            "Delivery could not be confirmed. Check the provider; automatic retry is disabled to prevent duplicates.",
        )
    approval.status = status
    audit(db, approval.case_id, user.email, f"Email {status}", approval.id)
    db.commit()
    return {"status": status}


@router.get("/settings")
def configuration(user=Depends(current_user)):
    return {
        "demo_mode": settings.demo_mode,
        "ai_provider": settings.ai_provider,
        "model": settings.openai_model
        if settings.ai_provider == "openai"
        else "Local evidence excerpts",
        "database": "PostgreSQL" if settings.database_url.startswith("postgres") else "SQLite",
        "retrieval": "Semantic + keyword" if settings.embeddings_enabled else "Case-scoped keyword",
        "worker_enabled": settings.worker_enabled,
        "stages": STAGES,
        "integrations": [
            {
                "name": "OpenAI",
                "status": "configured" if settings.openai_api_key else "demo",
                "description": "Structured answers and evidence verification",
            },
            {
                "name": "SMTP email",
                "status": "configured" if settings.smtp_host else "not configured",
                "description": "Approved welcome and follow-up messages",
            },
            {
                "name": "Filevine",
                "status": "configured" if settings.filevine_access_token else "not configured",
                "description": "Link an existing Filevine project; read-only verification",
            },
            {
                "name": "Calendar",
                "status": "local",
                "description": "Task deadlines and calendar export (.ics)",
            },
        ],
    }


@router.post("/cases/{case_id}/filevine/link")
def link_filevine(
    case_id: str,
    data: FilevineLinkInput,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    require_reviewer(user)
    case = get_case(db, case_id)
    try:
        get_project(data.project_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    except Exception:
        raise HTTPException(
            502,
            "Filevine could not verify this project. Check tenant IDs, credentials and project access.",
        )
    case.filevine_project_id = data.project_id
    audit(db, case.id, user.email, "Filevine project linked", data.project_id)
    db.commit()
    return {"project_id": data.project_id, "status": "verified"}


@router.get("/users")
def users(db: Session = Depends(get_db), user=Depends(current_user)):
    require_admin(user)
    return [row_dict(u, ("password_hash",)) for u in db.scalars(select(User))]


@router.post("/users", status_code=201)
def create_user(data: UserInput, db: Session = Depends(get_db), user=Depends(current_user)):
    require_admin(user)
    new_user = User(
        email=data.email.lower(),
        name=data.name,
        role=data.role,
        password_hash=hash_password(data.password),
    )
    db.add(new_user)
    try:
        audit(db, None, user.email, "Staff account created", data.email)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This email already exists")
    return row_dict(new_user, ("password_hash",))


@router.get("/tasks/calendar.ics")
def calendar(db: Session = Depends(get_db), user=Depends(current_user)):
    def escape(value):
        return (
            value.replace("\\", "\\\\")
            .replace("\n", "\\n")
            .replace(",", "\\,")
            .replace(";", "\\;")
            .replace("\r", "")
        )

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Arav//Case Operations//EN"]
    for task in db.scalars(select(Task).where(Task.completed == False)):
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{task.id}@arav.local",
                f"DTSTAMP:{now():%Y%m%dT%H%M%SZ}",
                f"DTSTART;VALUE=DATE:{task.due_date.replace('-', '')}",
                f"SUMMARY:{escape(task.title)}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return Response(
        "\r\n".join(lines) + "\r\n",
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="arav-tasks.ics"'},
    )
