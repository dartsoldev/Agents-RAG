"""Application entry point: lifecycle, HTTP security headers, API and static frontend."""

import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.body_limit import BodyLimitMiddleware
from backend.config import settings
from backend.routes import router
from database.seed import bootstrap
from orchestrator.worker import worker_loop


@asynccontextmanager
async def lifespan(app):
    bootstrap()
    stop = threading.Event()
    thread = None
    if settings.worker_enabled:
        thread = threading.Thread(
            target=worker_loop, args=(stop,), daemon=True, name="case-orchestrator"
        )
        thread.start()
    yield
    stop.set()
    if thread:
        thread.join(timeout=5)


app = FastAPI(
    title="Arav Case Operations API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.app_env != "production" else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.app_env != "production" else None,
)
app.add_middleware(BodyLimitMiddleware, max_bytes=(settings.max_upload_mb + 1) * 1024 * 1024)


@app.middleware("http")
async def protect_requests(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") != settings.app_url.rstrip("/"):
            return JSONResponse({"detail": "Request origin is not allowed"}, status_code=403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": "Cross-site request denied"}, status_code=403)
        content_length = request.headers.get("content-length", "0")
        if (
            not content_length.isdigit()
            or int(content_length) > (settings.max_upload_mb + 1) * 1024 * 1024
        ):
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        if request.url.path.startswith("/api/") and request.headers.get("x-arav-request") != "1":
            return JSONResponse({"detail": "Missing request header"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    )
    if request.url.path == "/api/docs" and settings.app_env != "production":
        # FastAPI's development-only Swagger page uses the official bundled CDN assets.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


app.include_router(router)
frontend = Path(__file__).resolve().parents[1] / "frontend"
app.mount("/static", StaticFiles(directory=frontend), name="static")


@app.get("/")
def index():
    return FileResponse(frontend / "index.html")
