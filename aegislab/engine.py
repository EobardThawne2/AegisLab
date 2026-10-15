"""Bounded deterministic data fixtures, executed by the trusted web controller.
No submitted code, containers, worker storage or network isolation is implemented.
"""
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from aegislab.documents import validate_document
from aegislab.evidence import digest, seal

ENGINE = "deterministic-fixture-v1"


def execute(evaluation_id, references, documents, signer, *, clock=perf_counter):
    for role, document in documents.items():
        if validate_document(document)[1] != references[role]["digest"]:
            raise ValueError("Locked document digest mismatch")
    started = datetime.now(UTC).isoformat()
    start = clock()
    policy = documents["policy"]["config"]
    prompts = documents["red"]["config"]["prompts"]
    blocked = documents["blue"]["config"]["blocked_terms"]
    response = documents["model"]["config"]["response"]
    manifest = {"run_id": str(uuid4()), "evaluation_id": evaluation_id,
                "started_at": started, "mode": "fixture_no_isolation", "engine": ENGINE,
                "engine_source_digest": sha256(Path(__file__).read_bytes()).hexdigest(),
                "model": "MOCK / mock-v1", "isolation": False, "worker_image_digests": None,
                "versions": references}
    events = []

    def emit(kind, data):
        record = {"sequence": len(events) + 1, "previous_digest": events[-1]["digest"] if events else "0" * 64,
                  "type": kind, "data": data}
        events.append({**record, "digest": digest(record)})

    emit("run_started", {"mode": manifest["mode"], "model": manifest["model"]})
    turns = denied = model_calls = 0
    failure = None
    for prompt in prompts[:policy["max_turns"]]:
        if clock() - start >= policy["timeout_seconds"]:
            failure = "fixture_deadline_exceeded"
            break
        if len(prompt.encode("utf-8")) > policy["max_message_bytes"]:
            failure = "input_message_limit_exceeded"
            break
        turns += 1
        emit("red_message", {"turn": turns, "content_digest": sha256(prompt.encode()).hexdigest(),
                             "bytes": len(prompt.encode())})
        is_blocked = any(term.casefold() in prompt.casefold() for term in blocked)
        denied += int(is_blocked)
        emit("blue_decision", {"turn": turns, "decision": "blocked" if is_blocked else "allowed"})
        if not is_blocked:
            if len(response.encode()) > policy["max_message_bytes"]:
                failure = "output_message_limit_exceeded"
                break
            model_calls += 1
            emit("mock_model_response", {"turn": turns, "content_digest": sha256(response.encode()).hexdigest(),
                                         "bytes": len(response.encode()), "adapter": "mock-v1"})
    if clock() - start >= policy["timeout_seconds"]:
        failure = "fixture_deadline_exceeded"
    outcome = {"status": "failed" if failure else "completed", "turns": turns,
               "blocked": denied, "mock_model_calls": model_calls, "failure": failure,
               "finished_at": datetime.now(UTC).isoformat(),
               "duration_ms": round((clock() - start) * 1000, 3)}
    emit("run_finished", {"status": outcome["status"], "turns": turns, "failure": failure})
    checks = [{"name": "Fixture policy bounds", "expected": "Turn, message and deadline bounds enforced",
               "observed": failure or f"{turns} bounded turns; {model_calls} mock calls",
               "status": "PASS" if not failure else "FAIL", "reference": "event:" + str(len(events))}]
    for name in ("Cross-team worker storage", "Unauthorized worker networking", "Fresh worker session",
                 "Worker timeout termination", "Worker cleanup after failure"):
        checks.append({"name": name, "expected": "Exercise boundary against isolated workers",
                       "observed": "Not executed: web fixture mode has no isolated workers",
                       "status": "UNVERIFIED", "reference": "manifest:isolation=false"})
    return seal(manifest, events, outcome, checks, signer)
