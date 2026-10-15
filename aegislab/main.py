"""Local FastAPI dashboard; HTML/CSS only, with live checks on each refresh."""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from aegislab.config import get_settings
from aegislab.database import status_snapshot
from aegislab.documents import Problem
from aegislab.evidence import configuration, ensure_local_key, key_id, load_signer
from aegislab.migrate import apply_migrations
from aegislab.phase2 import router as phase2_router
from aegislab.showcase import router as showcase_router

BASE = Path(__file__).parent
@asynccontextmanager
async def lifespan(app):
    # Normal trusted startup, not an HTTP administration endpoint.
    app.state.setup_ready = False
    try:
        values = configuration()
        if values.get("AEGISLAB_AUTO_MIGRATE", "true" if values.get("AEGISLAB_ENV") != "production" else "false").lower() == "true":
            await asyncio.to_thread(apply_migrations, get_settings())
        await asyncio.to_thread(ensure_local_key)
        app.state.setup_ready = True
    except (OSError, ValueError, TypeError, psycopg.Error):
        logging.getLogger("aegislab").warning("Setup incomplete. Check migrations and signing-key configuration; no secrets logged.")
    yield


app = FastAPI(title="AegisLab", version="0.3.0", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")
app.include_router(phase2_router)
app.include_router(showcase_router)


@app.exception_handler(Problem)
async def domain_problem(request: Request, error: Problem):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": error.message}, status_code=error.status)
    if error.status == 401 and request.method == "GET":
        return RedirectResponse("/login", 303)
    return templates.TemplateResponse(request=request, name="problem.html",
        context={"status": error.status, "message": error.message}, status_code=error.status)


@app.exception_handler(psycopg.Error)
async def database_problem(request: Request, _error):
    return await domain_problem(request, Problem(503, "Database operation unavailable. Check connectivity and apply the current migrations."))

WORKFLOW = [
    {"name": "Private Submissions", "phase": "Phase 2", "state": "Available", "detail": "Authenticated roles and private JSON versions."},
    {"name": "Version Locking", "phase": "Phase 2", "state": "Available", "detail": "Immutable submission and policy references."},
    {"name": "Isolated Evaluation", "phase": "Deferred", "state": "Unimplemented", "detail": "Showcase runs bounded fixtures without worker isolation."},
    {"name": "Evidence", "phase": "Showcase", "state": "Available", "detail": "Hash-linked events and Ed25519 checkpoints."},
    {"name": "Role-Specific Reports", "phase": "Showcase", "state": "Available", "detail": "Aggregate feedback and authorized references."},
]


@app.middleware("http")
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    if not request.url.path.startswith("/static/"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; style-src 'self'; img-src 'self'; "
            "script-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
    return response


@app.get("/", include_in_schema=False)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"snapshot": current_status(), "workflow": WORKFLOW},
    )


@app.get("/health/live")
def live():
    return {"status": "running", "project": "AegisLab", "phase": "web-showcase"}


@app.get("/api/status")
def current_status():
    snapshot = status_snapshot(get_settings())
    try:
        snapshot["signing"] = {"status": "ready", "key_id": key_id(load_signer().public_key())}
    except (OSError, ValueError, TypeError):
        snapshot["signing"] = {"status": "unavailable"}
        snapshot["ready"] = False
    return snapshot



@app.get("/health/ready")
def ready():
    snapshot = current_status()
    return JSONResponse(snapshot, status_code=200 if snapshot["ready"] else 503)


@app.get("/api/docs", include_in_schema=False)
def api_reference(request: Request):
    return templates.TemplateResponse(request=request, name="api.html", context={})
