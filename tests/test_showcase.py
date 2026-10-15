"""Real cryptography and deterministic fixture bounds; no worker-isolation claims."""
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from aegislab.config import ROOT
from aegislab.documents import validate_document
from aegislab.engine import execute
from aegislab.evidence import canonical, digest, modified_copy, verify


def documents():
    return {role: json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8")) for role, name in
            (("red", "red-showcase.json"), ("blue", "blue-v1.json"),
             ("model", "model-v1.json"), ("policy", "policy-v1.json"))}


def bundle(docs=None, clock=lambda: 0):
    key = Ed25519PrivateKey.generate()
    docs = docs or documents()
    refs = {role: {"version_id": role, "digest": validate_document(doc)[1]} for role, doc in docs.items()}
    return execute("test-evaluation", refs, docs, key, clock=clock), key


def test_real_signed_evidence_and_redacted_fixture_outcome():
    record, key = bundle()
    assert verify(record, key.public_key(), record["manifest"]["run_id"])["valid"]
    assert record["outcome"]["turns"] == 2
    assert record["outcome"]["blocked"] == record["outcome"]["mock_model_calls"] == 1
    encoded = canonical(record).decode()
    for role, field in (("red", "prompts"), ("blue", "blocked_terms")):
        assert all(item not in encoded for item in documents()[role]["config"][field])
    assert documents()["model"]["config"]["response"] not in encoded
    assert record["manifest"]["isolation"] is False
    assert record["manifest"]["worker_image_digests"] is None
    assert sum(item["status"] == "UNVERIFIED" for item in record["checks"]) == 5


@pytest.mark.parametrize("change", ["contents", "previous", "reorder", "delete", "truncate", "signature", "manifest", "outcome", "checks", "replacement_key"])
def test_verifier_rejects_tampering(change):
    record, key = bundle()
    if change == "contents":
        record = modified_copy(record)
    elif change == "previous":
        record["events"][1]["previous_digest"] = "0" * 64
    elif change == "reorder":
        record["events"][0], record["events"][1] = record["events"][1], record["events"][0]
    elif change == "delete":
        del record["events"][1]
    elif change == "truncate":
        record["events"].pop()
    elif change == "signature":
        record["signature"] = "AA=="
    elif change == "manifest":
        record["manifest"]["isolation"] = True
    elif change == "outcome":
        record["outcome"]["status"] = "faked"
    elif change == "checks":
        record["checks"][1]["status"] = "PASS"
    elif change == "replacement_key":
        key = Ed25519PrivateKey.generate()
    assert not verify(record, key.public_key())["valid"]


def test_expected_run_protects_against_substituting_another_valid_run():
    record, key = bundle()
    assert not verify(record, key.public_key(), "another-run")["valid"]


def test_rechaining_modified_events_cannot_replace_signed_checkpoint():
    record, key = bundle()
    changed = modified_copy(record)
    previous = "0" * 64
    for event in changed["events"]:
        event["previous_digest"] = previous
        event["digest"] = digest({k: v for k, v in event.items() if k != "digest"})
        previous = event["digest"]
    changed["checkpoint"]["final_chain_digest"] = previous
    assert not verify(changed, key.public_key())["valid"]
    assert verify(record, key.public_key())["valid"]


def test_turn_limit_and_input_output_message_bounds():
    docs = documents()
    docs["policy"]["config"]["max_turns"] = 1
    record, _ = bundle(docs)
    assert record["outcome"]["turns"] == 1
    docs = documents()
    docs["policy"]["config"]["max_message_bytes"] = 128
    docs["red"]["config"]["prompts"] = ["x" * 129]
    record, key = bundle(docs)
    assert record["outcome"]["failure"] == "input_message_limit_exceeded"
    assert verify(record, key.public_key())["valid"]
    docs["red"]["config"]["prompts"] = ["hello"]
    docs["model"]["config"]["response"] = "x" * 129
    record, _ = bundle(docs)
    assert record["outcome"]["failure"] == "output_message_limit_exceeded"


def test_fixture_deadline_failure_is_recorded_without_claiming_process_termination():
    times = iter([0, 61, 61, 61])
    record, key = bundle(clock=lambda: next(times))
    assert record["outcome"]["failure"] == "fixture_deadline_exceeded"
    assert verify(record, key.public_key())["valid"]
    assert any(item["name"] == "Worker timeout termination" and item["status"] == "UNVERIFIED" for item in record["checks"])


@pytest.mark.parametrize("record", [None, [], {}, {"format": "wrong"}])
def test_malformed_evidence_returns_failure(record):
    assert not verify(record, Ed25519PrivateKey.generate().public_key())["valid"]


def test_canonical_encoding_is_stable_for_reordered_keys():
    assert canonical({"a": 1, "b": "é"}) == canonical({"b": "é", "a": 1})
    with pytest.raises(ValueError):
        canonical({"x": float("nan")})


def test_locked_reference_digest_mismatch_is_rejected():
    docs = documents()
    refs = {role: {"version_id": role, "digest": "0" * 64} for role in docs}
    with pytest.raises(ValueError, match="digest mismatch"):
        execute("test", refs, docs, Ed25519PrivateKey.generate())


def test_showcase_routes_require_auth_and_reject_policy_overrides():
    from fastapi.testclient import TestClient

    from aegislab.main import app
    client = TestClient(app, base_url="http://localhost")
    for suffix in ("report", "evidence"):
        assert client.get("/api/runs/00000000-0000-0000-0000-000000000000/" + suffix).status_code == 401
    assert client.get("/api/verification-key").status_code == 401
    assert client.post("/api/evaluations/test/runs", json={}).status_code == 401
    assert client.post("/api/evaluations/test/runs", json={"max_turns": 999}).status_code == 422
    assert client.post("/api/runs/test/verify", json={"source": {}}).status_code == 422


def test_production_uses_secure_cookie_and_configured_origin(monkeypatch):
    from fastapi.testclient import TestClient

    from aegislab import main, phase2
    monkeypatch.setenv("AEGISLAB_ENV", "production")
    monkeypatch.setenv("AEGISLAB_PUBLIC_ORIGIN", "https://showcase.example")
    token = "x" * 43
    monkeypatch.setattr(phase2, "authenticate", lambda request, values: ({"role": "red"}, token))
    client = TestClient(main.app, base_url="https://showcase.example")
    result = client.post("/api/auth/login", json={"username": "synthetic", "password": "test-only"})
    assert "Secure" in result.headers["set-cookie"]
    from starlette.requests import Request

    from aegislab.auth import same_origin
    request = Request({"type": "http", "scheme": "http", "server": ("internal", 80),
                       "path": "/", "headers": [(b"origin", b"https://showcase.example")]})
    same_origin(request)
    with pytest.raises(Exception) as error:
        same_origin(Request({"type": "http", "scheme": "https", "server": ("showcase.example", 443),
                             "path": "/", "headers": [(b"origin", b"https://foreign.example")]}))
    assert error.value.status == 403
