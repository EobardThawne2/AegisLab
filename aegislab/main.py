"""Local FastAPI dashboard; HTML/CSS only, with live checks on each refresh."""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from aegislab.config import get_settings
from aegislab.database import status_snapshot

BASE = Path(__file__).parent
app = FastAPI(title="AegisLab", version="0.1.0", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
templates = Jinja2Templates(directory=BASE / "templates")

WORKFLOW = [
    {"name": "Private Submissions", "phase": "Phase 2", "detail": "Role authorization and private artifacts."},
    {"name": "Version Locking", "phase": "Phase 2", "detail": "Fixed submission and policy references."},
    {"name": "Isolated Evaluation", "phase": "Phase 3", "detail": "Separate Red, Blue and mock Model workers."},
    {"name": "Evidence", "phase": "Phase 5", "detail": "Hash-linked events and signed checkpoints."},
    {"name": "Role-Specific Reports", "phase": "Phase 5", "detail": "Views limited to authorized information."},
]


@app.middleware("http")
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path in {"/", "/api/docs"}:
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
        context={"snapshot": status_snapshot(get_settings()), "workflow": WORKFLOW},
    )


@app.get("/health/live")
def live():
    return {"status": "running", "project": "AegisLab", "phase": 1}


@app.get("/api/status")
def status():
    return status_snapshot(get_settings())


@app.get("/health/ready")
def ready():
    snapshot = status_snapshot(get_settings())
    return JSONResponse(snapshot, status_code=200 if snapshot["ready"] else 503)


@app.get("/api/docs", include_in_schema=False)
def api_reference(request: Request):
    return templates.TemplateResponse(request=request, name="api.html", context={})
