"""Narrow, inert JSON format. No submitted code is executed in Phase 2."""
import json
import re
from hashlib import sha256

ROLE_KIND = {"red": "attack", "blue": "defense", "client": "model", "evaluator": "policy"}
MAX_DOCUMENT_BYTES = 16384


class Problem(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


def reject_constant(_value):
    raise ValueError("Non-finite JSON values are not accepted")


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field")
        result[key] = value
    return result


def parse_json(raw: str | bytes):
    try:
        if len(raw.encode("utf-8") if isinstance(raw, str) else raw) > MAX_DOCUMENT_BYTES:
            raise Problem(413, "Document exceeds 16 KiB")
        return json.loads(raw, object_pairs_hook=unique_keys, parse_constant=reject_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise Problem(422, "Invalid JSON; duplicate fields and non-finite values are not accepted") from None


def string_list(value, maximum: int, item_size: int) -> bool:
    return (isinstance(value, list) and 1 <= len(value) <= maximum
            and all(isinstance(item, str) and 1 <= len(item) <= item_size
                    and "\x00" not in item for item in value))


def validate_document(document: dict) -> tuple[str, str]:
    if not isinstance(document, dict) or set(document) != {"schema_version", "kind", "name", "config"}:
        raise Problem(422, "Required document fields: schema_version, kind, name, config; no extras")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise Problem(422, "schema_version must be integer 1")
    name, kind, config = document["name"], document["kind"], document["config"]
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9-]{1,64}", name):
        raise Problem(422, "name must contain 1–64 lowercase letters, digits or hyphens")
    if not isinstance(kind, str) or kind not in ROLE_KIND.values() or not isinstance(config, dict):
        raise Problem(422, "Unsupported kind or config")
    valid = False
    if kind == "attack":
        valid = set(config) == {"prompts"} and string_list(config["prompts"], 8, 1000)
    elif kind == "defense":
        valid = set(config) == {"blocked_terms"} and string_list(config["blocked_terms"], 32, 80)
    elif kind == "model":
        valid = (set(config) == {"adapter", "response"} and config["adapter"] == "mock-v1"
                 and isinstance(config["response"], str) and 1 <= len(config["response"]) <= 2000
                 and "\x00" not in config["response"])
    elif kind == "policy":
        limits = {"max_turns": (1, 8), "timeout_seconds": (1, 60), "max_message_bytes": (128, 8192)}
        valid = set(config) == set(limits) and all(
            type(config[key]) is int and low <= config[key] <= high
            for key, (low, high) in limits.items()
        )
    if not valid:
        raise Problem(422, "Config does not match the documented schema for this kind")
    try:
        canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        data = canonical.encode("utf-8")
    except (ValueError, UnicodeError):
        raise Problem(422, "Document must contain valid Unicode JSON values") from None
    if len(data) > MAX_DOCUMENT_BYTES:
        raise Problem(413, "Document exceeds 16 KiB")
    return canonical, sha256(data).hexdigest()
