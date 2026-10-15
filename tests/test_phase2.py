"""Format and HTTP boundary tests. These do not establish PostgreSQL isolation."""
import copy
import json
import secrets

import pytest
from fastapi.testclient import TestClient

from aegislab import main, phase2
from aegislab.config import ROOT
from aegislab.documents import Problem, parse_json, validate_document
from aegislab.passwords import csrf_token, hash_password, verify_password


def fixture(name="red-v1.json"):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["red-v1.json", "red-v2.json", "blue-v1.json", "model-v1.json", "policy-v1.json"])
def test_synthetic_documents_conform_to_the_narrow_format(name):
    canonical, digest = validate_document(fixture(name))
    assert len(digest) == 64
    assert json.loads(canonical) == fixture(name)


def test_document_digest_is_independent_of_json_spacing_and_field_order():
    document = fixture()
    reordered = dict(reversed(list(document.items())))
    assert validate_document(parse_json(json.dumps(document, indent=4))) == validate_document(reordered)
    changed = copy.deepcopy(document)
    changed["config"]["prompts"][0] += " A different prompt."
    assert validate_document(changed)[1] != validate_document(document)[1]


@pytest.mark.parametrize("raw", ['{"name":"a","name":"b"}', '{"number":NaN}', '{"number":Infinity}', '{invalid', '"\\ud800"'])
def test_invalid_or_ambiguous_json_is_rejected(raw):
    with pytest.raises(Problem):
        validate_document(parse_json(raw))


@pytest.mark.parametrize("change", [
    {"schema_version": True}, {"schema_version": 2}, {"name": "../secret"},
    {"kind": "python"}, {"unexpected": "field"}, {"config": {"prompts": []}},
    {"config": {"prompts": ["x" * 1001]}}, {"config": {"prompts": ["x"], "command": "execute"}},
])
def test_unsupported_documents_are_rejected(change):
    document = fixture()
    document.update(change)
    with pytest.raises(Problem) as error:
        validate_document(document)
    assert error.value.status == 422


def test_boolean_policy_limit_is_not_accepted_as_an_integer():
    document = fixture("policy-v1.json")
    document["config"]["max_turns"] = True
    with pytest.raises(Problem):
        validate_document(document)


def test_document_transport_limit_is_enforced():
    with pytest.raises(Problem) as error:
        parse_json(" " * 16385)
    assert error.value.status == 413


def test_password_hashes_use_distinct_salts_and_validate_only_the_right_password():
    password = secrets.token_urlsafe(24)
    first, second = hash_password(password), hash_password(password)
    assert first != second
    assert password not in first
    assert verify_password(password, first)
    assert not verify_password(password + "wrong", first)
    assert not verify_password(password, "malformed")


@pytest.fixture
def client():
    with TestClient(main.app, base_url="http://localhost") as client:
        yield client


def test_unauthenticated_requests_do_not_get_private_resources(client):
    for path in ("/api/auth/me", "/api/submissions", "/api/evaluations", "/api/evaluation-references"):
        response = client.get(path)
        assert response.status_code == 401
        assert response.json() == {"detail": "Sign in required"}
    assert client.get("/workspace", follow_redirects=False).status_code == 303


def test_login_form_never_embeds_demo_passwords(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert 'type="password"' in response.text
    assert response.headers["Referrer-Policy"] == "same-origin"
    assert "<script" not in response.text.lower()


def test_cross_origin_login_is_rejected_before_database_access(client):
    response = client.post("/api/auth/login", json={"username": "demo-red", "password": "not-a-real-credential"},
                           headers={"Origin": "https://untrusted.example"})
    assert response.status_code == 403


@pytest.mark.parametrize("csrf", ["", "wrong"])
def test_missing_or_invalid_csrf_is_denied_before_database_access(client, csrf):
    token = secrets.token_urlsafe(32)
    client.cookies.set("aegislab_session", token)
    response = client.post("/api/submissions", json=fixture(), headers={"x-csrf-token": csrf})
    assert response.status_code == 403


def test_oversize_requests_fail_without_creating_a_version(client):
    response = client.post("/api/submissions", content="x" * 65537, headers={"content-type": "application/json"})
    assert response.status_code == 413


def test_api_login_sets_http_only_cookie_without_returning_the_session_token(client, monkeypatch):
    token = secrets.token_urlsafe(32)
    actor = {"id": "synthetic", "username": "demo-red", "role": "red", "synthetic": True}
    monkeypatch.setattr(phase2, "authenticate", lambda request, values: (actor, token))
    response = client.post("/api/auth/login", json={"username": "demo-red", "password": "test-double-only"})
    assert response.status_code == 200
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert token not in response.text
    assert response.json()["csrf_token"] == csrf_token(token)


def test_opaque_login_origin_is_rejected(client):
    response = client.post("/api/auth/login", json={"username": "demo-red", "password": "test-only"}, headers={"Origin": "null"})
    assert response.status_code == 403
