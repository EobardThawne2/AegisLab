"""Authenticated Phase 2 API and HTML/CSS forms. No worker execution."""
import asyncio
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from aegislab.auth import COOKIE, authenticate, authorized
from aegislab.config import ROOT
from aegislab.documents import Problem, parse_json
from aegislab.evidence import configuration
from aegislab.passwords import csrf_token, token_hash

router = APIRouter()
templates = Jinja2Templates(directory=ROOT / "aegislab" / "templates")
FIXTURES = {"red": "red-showcase.json", "blue": "blue-v1.json", "client": "model-v1.json", "evaluator": "policy-v1.json"}


async def payload(request: Request):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 65536:
            raise Problem(413, "Request exceeds the 64 KiB transport limit")
    content_type = request.headers.get("content-type", "").split(";")[0]
    if content_type == "application/json":
        return parse_json(bytes(raw))
    if content_type == "application/x-www-form-urlencoded":
        try:
            fields = parse_qs(raw.decode("utf-8"), keep_blank_values=True, strict_parsing=True, max_num_fields=12)
            if any(len(values) != 1 for values in fields.values()):
                raise ValueError("Duplicate form field")
            return {key: values[0] for key, values in fields.items()}
        except (ValueError, UnicodeError):
            raise Problem(422, "Invalid form") from None
    raise Problem(415, "Use application/json or application/x-www-form-urlencoded")


async def form_payload(request):
    result = await payload(request)
    if not isinstance(result, dict) or any(not isinstance(value, str) for value in result.values()):
        raise Problem(422, "Form fields must be strings")
    return result


def view(request, name, context):
    return templates.TemplateResponse(request=request, name=name, context=context)


def login_response(request, values, api):
    actor, token = authenticate(request, values)
    response = JSONResponse({"actor": actor, "csrf_token": csrf_token(token)}) if api else RedirectResponse("/workspace", 303)
    response.set_cookie(COOKIE, token, max_age=43200, httponly=True, secure=configuration().get("AEGISLAB_ENV") == "production", samesite="strict", path="/")
    return response


@router.get("/login", include_in_schema=False)
def login_page(request: Request):
    return view(request, "login.html", {})


@router.post("/login", include_in_schema=False)
async def login_form(request: Request):
    return await asyncio.to_thread(login_response, request, await form_payload(request), False)


@router.post("/api/auth/login")
async def login_api(request: Request):
    return await asyncio.to_thread(login_response, request, await payload(request), True)


def logout_response(request, data, api):
    with authorized(request, csrf=data.get("csrf_token"), mutation=True) as context:
        context.repository.delete_session(token_hash(context.token))
    response = JSONResponse({"logged_out": True}) if api else RedirectResponse("/login", 303)
    response.delete_cookie(COOKIE, path="/", samesite="strict", httponly=True)
    return response


@router.post("/logout", include_in_schema=False)
async def logout_form(request: Request):
    return await asyncio.to_thread(logout_response, request, await form_payload(request), False)


@router.post("/api/auth/logout")
def logout_api(request: Request):
    return logout_response(request, {}, True)


@router.get("/api/auth/me")
def me(request: Request):
    with authorized(request) as context:
        return {"actor": context.actor, "csrf_token": context.csrf}


@router.get("/api/submissions")
def list_submissions(request: Request):
    with authorized(request) as context:
        return {"versions": context.repository.list_versions(context.actor)}


@router.get("/api/submissions/{version_id}")
def get_submission(request: Request, version_id: str):
    with authorized(request) as context:
        return context.repository.version(context.actor, version_id)


def submit(request, document, csrf=None):
    with authorized(request, csrf=csrf, mutation=True) as context:
        return context.repository.submit(context.actor, document)


@router.post("/api/submissions", status_code=201)
async def submit_api(request: Request):
    return await asyncio.to_thread(submit, request, await payload(request))


@router.get("/api/evaluation-references")
def evaluation_references(request: Request):
    with authorized(request) as context:
        return {"versions": context.repository.references(context.actor)}


def lock(request, values, csrf=None):
    with authorized(request, csrf=csrf, mutation=True) as context:
        return context.repository.lock(context.actor, values)


@router.post("/api/evaluations", status_code=201)
async def lock_api(request: Request):
    return await asyncio.to_thread(lock, request, await payload(request))


@router.get("/api/evaluations")
def list_evaluations(request: Request):
    with authorized(request) as context:
        return {"evaluations": context.repository.list_evaluations(context.actor)}


@router.get("/api/evaluations/{evaluation_id}")
def get_evaluation(request: Request, evaluation_id: str):
    with authorized(request) as context:
        return context.repository.evaluation(context.actor, evaluation_id)


@router.get("/workspace", include_in_schema=False)
def workspace(request: Request):
    with authorized(request) as context:
        references = context.repository.references(context.actor) if context.actor["role"] == "evaluator" else []
        options = {kind: [item for item in references if item["kind"] == kind
                         and (kind != "policy" or item["owner_id"] == context.actor["id"])]
                   for kind in ("attack", "defense", "model", "policy")}
        fixture = (ROOT / "fixtures" / FIXTURES[context.actor["role"]]).read_text(encoding="utf-8")
        return view(request, "workspace.html", {"actor": context.actor, "csrf": context.csrf,
                    "versions": context.repository.list_versions(context.actor),
                    "evaluations": context.repository.list_evaluations(context.actor),
                    "options": options, "references": references, "fixture": fixture})


@router.post("/workspace/submissions", include_in_schema=False)
async def submit_form(request: Request):
    data = await form_payload(request)
    if set(data) != {"csrf_token", "document"}:
        raise Problem(422, "Document and CSRF token required")
    result = await asyncio.to_thread(submit, request, parse_json(data["document"]), data["csrf_token"])
    return RedirectResponse("/workspace/versions/" + result["id"], 303)


@router.get("/workspace/versions/{version_id}", include_in_schema=False)
def version_page(request: Request, version_id: str):
    with authorized(request) as context:
        version = context.repository.version(context.actor, version_id)
        return view(request, "version.html", {"actor": context.actor, "csrf": context.csrf, "version": version})


@router.post("/workspace/evaluations", include_in_schema=False)
async def lock_form(request: Request):
    data = await form_payload(request)
    csrf = data.pop("csrf_token", "")
    result = await asyncio.to_thread(lock, request, data, csrf)
    return RedirectResponse("/workspace/evaluations/" + result["id"], 303)


@router.get("/workspace/evaluations/{evaluation_id}", include_in_schema=False)
def evaluation_page(request: Request, evaluation_id: str):
    with authorized(request) as context:
        evaluation = context.repository.evaluation(context.actor, evaluation_id)
        runs = context.repository.connection.execute(
            "SELECT id, created_at, bundle->'outcome'->>'status' AS status FROM aegislab.fixture_runs "
            "WHERE evaluation_id = %s ORDER BY created_at DESC LIMIT 20", (evaluation_id,),
        ).fetchall()
        creator = context.repository.evaluation_rows(context.actor, evaluation_id)[0]
        return view(request, "evaluation.html", {"actor": context.actor, "csrf": context.csrf,
            "evaluation": evaluation, "runs": runs,
            "can_run": str(creator["created_by"]) == context.actor["id"]})


def access_check(request, data):
    with authorized(request, csrf=data.get("csrf_token"), mutation=True) as context:
        try:
            context.repository.version(context.actor, data.get("version_id", ""))
            observed = 200
        except Problem as error:
            if error.status != 404:
                raise
            observed = 404
        return view(request, "access_check.html", {"actor": context.actor, "csrf": context.csrf,
                    "observed": observed, "target": data.get("version_id", "")[:36]})


@router.post("/workspace/access-check", include_in_schema=False)
async def access_check_form(request: Request):
    return await asyncio.to_thread(access_check, request, await form_payload(request))
