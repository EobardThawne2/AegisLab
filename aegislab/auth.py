"""Database-backed sessions, same-origin forms and CSRF protection for local development."""
import hmac
import re
import secrets
import threading
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from time import monotonic

from aegislab.config import get_settings
from aegislab.database import bound_transaction, connect
from aegislab.documents import Problem
from aegislab.evidence import configuration
from aegislab.passwords import csrf_token, hash_password, token_hash, verify_password
from aegislab.repository import Repository, public

COOKIE = "aegislab_session"
DUMMY_HASH = hash_password("unused-account-timing-placeholder")
FAILURES = defaultdict(deque)
RATE_LOCK = threading.Lock()


@dataclass(repr=False)
class Context:
    actor: dict
    repository: Repository
    token: str = field(repr=False)

    @property
    def csrf(self):
        return csrf_token(self.token)


def same_origin(request):
    origin = request.headers.get("origin")
    values = configuration()
    expected = values.get("AEGISLAB_PUBLIC_ORIGIN") or str(request.base_url).rstrip("/")
    if values.get("AEGISLAB_ENV") == "production" and not expected.startswith("https://"):
        raise Problem(503, "Configure the production HTTPS origin")
    if (origin and origin != expected) or request.headers.get("sec-fetch-site") == "cross-site":
        raise Problem(403, "Cross-origin requests are not allowed")


@contextmanager
def database_repository():
    with connect(get_settings()) as connection:
        bound_transaction(connection)
        yield Repository(connection)


@contextmanager
def authorized(request, csrf=None, mutation=False):
    token = request.cookies.get(COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{40,80}", token):
        raise Problem(401, "Sign in required")
    if mutation:
        same_origin(request)
        supplied = csrf or request.headers.get("x-csrf-token", "")
        if not isinstance(supplied, str) or not re.fullmatch(r"[a-f0-9]{64}", supplied) or not hmac.compare_digest(supplied, csrf_token(token)):
            raise Problem(403, "CSRF validation failed; reload the form")
    with database_repository() as repository:
        actor = repository.session_actor(token_hash(token))
        if not actor:
            raise Problem(401, "Session expired or invalid; sign in again")
        yield Context(actor, repository, token)


def authenticate(request, values):
    same_origin(request)
    if not isinstance(values, dict) or set(values) != {"username", "password"}:
        raise Problem(422, "Username and password are required")
    username, password = values["username"], values["password"]
    if not isinstance(username, str) or not re.fullmatch(r"[a-z0-9-]{3,40}", username) or not isinstance(password, str) or not 1 <= len(password) <= 256:
        raise Problem(401, "Invalid username or password")
    key = (request.client.host if request.client else "local", username)
    with RATE_LOCK:
        failures = FAILURES[key]
        while failures and failures[0] < monotonic() - 60:
            failures.popleft()
        if len(failures) >= 5:
            raise Problem(429, "Too many failed attempts; wait one minute")
    with database_repository() as repository:
        row = repository.participant(username)
        matched = verify_password(password, row["password_hash"] if row else DUMMY_HASH)
        if not row or not matched:
            with RATE_LOCK:
                FAILURES[key].append(monotonic())
            raise Problem(401, "Invalid username or password")
        token = secrets.token_urlsafe(32)
        repository.save_session(token_hash(token), row["id"])
        actor = public({key: row[key] for key in ("id", "username", "role", "synthetic")})
    with RATE_LOCK:
        FAILURES.pop(key, None)
    return actor, token
