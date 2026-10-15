"""Authenticated web showcase routes; fixture execution is explicitly non-isolated."""
import asyncio
import json
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from psycopg.types.json import Jsonb

from aegislab.auth import authorized
from aegislab.documents import Problem
from aegislab.engine import execute
from aegislab.evidence import digest, key_id, load_signer, modified_copy, verify
from aegislab.phase2 import form_payload, payload, view
from aegislab.repository import public, valid_id

router = APIRouter()


def owned_lock(context, evaluation_id):
    rows = context.repository.evaluation_rows(context.actor, evaluation_id)
    if not rows:
        raise Problem(404, "Not found")
    row = rows[0]
    if str(row["created_by"]) != context.actor["id"] or context.actor["role"] != "evaluator":
        raise Problem(403, "Only the creating evaluator can run fixtures or export evidence")
    return row


def signer():
    try:
        return load_signer()
    except (OSError, ValueError, TypeError):
        raise Problem(503, "Signing key unavailable. Complete local setup or configure the production key.") from None


def create_run(request, evaluation_id, csrf=None):
    with authorized(request, csrf=csrf, mutation=True) as context:
        row = owned_lock(context, evaluation_id)
        references, documents = {}, {}
        for role in ("red", "blue", "model", "policy"):
            version_id = row[role + "_version_id"]
            artifact = context.repository.connection.execute(
                "SELECT id, digest, canonical_document FROM aegislab.submission_versions WHERE id = %s",
                (version_id,),
            ).fetchone()
            documents[role] = json.loads(artifact["canonical_document"])
            references[role] = {"version_id": str(artifact["id"]), "digest": artifact["digest"]}
        bundle = execute(str(row["id"]), references, documents, signer())
        context.repository.connection.execute(
            "INSERT INTO aegislab.fixture_runs (id, evaluation_id, created_by, bundle) VALUES (%s,%s,%s,%s)",
            (bundle["manifest"]["run_id"], row["id"], context.actor["id"], Jsonb(bundle)),
        )
        return {"id": bundle["manifest"]["run_id"], "status": bundle["outcome"]["status"],
                "mode": "fixture_no_isolation"}


def accessible_run(context, run_id):
    row = context.repository.connection.execute(
        "SELECT id, evaluation_id, created_by, created_at, bundle FROM aegislab.fixture_runs WHERE id = %s",
        (valid_id(run_id),),
    ).fetchone()
    if not row:
        raise Problem(404, "Not found")
    evaluation = context.repository.evaluation(context.actor, row["evaluation_id"])
    return row, evaluation


def report(context, run_id):
    row, evaluation = accessible_run(context, run_id)
    bundle = row["bundle"]
    creator = str(row["created_by"]) == context.actor["id"]
    result = {"id": str(row["id"]), "evaluation_id": str(row["evaluation_id"]),
              "role": context.actor["role"], "mode": bundle["manifest"]["mode"],
              "model": "MOCK / mock-v1", "outcome": bundle["outcome"],
              "versions": evaluation["versions"], "checks": bundle["checks"],
              "isolation": "UNVERIFIED — no isolated workers", "can_export": creator,
              "events": bundle["events"] if creator else [], "verifications": []}
    if creator:
        rows = context.repository.connection.execute(
            "SELECT id, created_at, source, bundle_digest, key_id, valid "
            "FROM aegislab.evidence_verifications WHERE run_id = %s ORDER BY created_at DESC LIMIT 20",
            (run_id,),
        ).fetchall()
        result["verifications"] = [public(item) for item in rows]
        result["checkpoint"] = bundle["checkpoint"]
    return result


def verify_run(request, run_id, source, csrf=None):
    if not isinstance(source, str) or source not in {"original", "modified_copy"}:
        raise Problem(422, "Choose original or modified_copy")
    with authorized(request, csrf=csrf, mutation=True) as context:
        row, _ = accessible_run(context, run_id)
        owned_lock(context, row["evaluation_id"])
        bundle = modified_copy(row["bundle"]) if source == "modified_copy" else row["bundle"]
        key = signer().public_key()
        result = verify(bundle, key, run_id)
        identifier = str(uuid4())
        context.repository.connection.execute(
            "INSERT INTO aegislab.evidence_verifications "
            "(id,run_id,created_by,source,bundle_digest,key_id,valid) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (identifier, run_id, context.actor["id"], source, digest(bundle), key_id(key), result["valid"]),
        )
        return {**result, "id": identifier, "source": source, "bundle_digest": digest(bundle)}


@router.post("/api/evaluations/{evaluation_id}/runs", status_code=201)
async def run_api(request: Request, evaluation_id: str):
    data = await payload(request)
    if data != {}:
        raise Problem(422, "Use an empty JSON object; the locked policy controls execution")
    return await asyncio.to_thread(create_run, request, evaluation_id)


@router.post("/workspace/evaluations/{evaluation_id}/run", include_in_schema=False)
async def run_form(request: Request, evaluation_id: str):
    data = await form_payload(request)
    result = await asyncio.to_thread(create_run, request, evaluation_id, data.get("csrf_token"))
    return RedirectResponse("/workspace/runs/" + result["id"], 303)


@router.get("/api/runs/{run_id}/report")
def report_api(request: Request, run_id: str):
    with authorized(request) as context:
        return report(context, run_id)


@router.get("/workspace/runs/{run_id}", include_in_schema=False)
def report_page(request: Request, run_id: str):
    with authorized(request) as context:
        return view(request, "run.html", {"actor": context.actor, "csrf": context.csrf,
                                          "report": report(context, run_id)})


@router.post("/api/runs/{run_id}/verify")
async def verify_api(request: Request, run_id: str):
    data = await payload(request)
    if not isinstance(data, dict) or set(data) != {"source"}:
        raise Problem(422, "Verification source required")
    return await asyncio.to_thread(verify_run, request, run_id, data["source"])


@router.post("/workspace/runs/{run_id}/verify", include_in_schema=False)
async def verify_form(request: Request, run_id: str):
    data = await form_payload(request)
    await asyncio.to_thread(verify_run, request, run_id, data.get("source"), data.get("csrf_token"))
    return RedirectResponse("/workspace/runs/" + run_id + "#verification", 303)


@router.get("/api/runs/{run_id}/evidence")
def export_evidence(request: Request, run_id: str, modified: bool = False):
    with authorized(request) as context:
        row, _ = accessible_run(context, run_id)
        owned_lock(context, row["evaluation_id"])
        bundle = modified_copy(row["bundle"]) if modified else row["bundle"]
        filename = "aegislab-" + valid_id(run_id) + ("-modified" if modified else "") + ".json"
        return JSONResponse(bundle, headers={"Content-Disposition": 'attachment; filename="' + filename + '"'})


@router.get("/api/verification-key")
def verification_key(request: Request):
    with authorized(request) as context:
        if context.actor["role"] != "evaluator":
            raise Problem(403, "Evaluator role required")
        data = signer().public_key().public_bytes(serialization.Encoding.PEM,
                                                 serialization.PublicFormat.SubjectPublicKeyInfo)
        return Response(data, media_type="application/x-pem-file",
                        headers={"Content-Disposition": 'attachment; filename="verification-key.pem"'})
