"""Portable Ed25519 evidence format. Verification requires a separately trusted key."""
import argparse
import base64
import copy
import json
import os
from hashlib import sha256
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from dotenv import dotenv_values

from aegislab.config import ROOT


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return sha256(canonical(value)).hexdigest()


def public_bytes(key):
    return key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def key_id(key):
    return sha256(public_bytes(key)).hexdigest()


def configuration():
    return {**dotenv_values(ROOT / ".env", interpolate=False), **os.environ}


def load_signer():
    values = configuration()
    encoded = values.get("AEGISLAB_SIGNING_KEY")
    if encoded:
        return Ed25519PrivateKey.from_private_bytes(base64.b64decode(encoded, validate=True))
    if values.get("AEGISLAB_ENV") == "production":
        raise ValueError("Production signing key is required")
    path = ROOT / "local-data" / "signing-key.pem"
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("Ed25519 signing key required")
    return key


def ensure_local_key():
    values = configuration()
    if values.get("AEGISLAB_SIGNING_KEY") or values.get("AEGISLAB_ENV") == "production":
        load_signer()
        return
    path = ROOT / "local-data" / "signing-key.pem"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        key = Ed25519PrivateKey.generate()
        data = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption())
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
        except FileExistsError:
            pass
    key = load_signer()
    public = key.public_key().public_bytes(serialization.Encoding.PEM,
                                         serialization.PublicFormat.SubjectPublicKeyInfo)
    (path.parent / "verification-key.pem").write_bytes(public)


def seal(manifest, events, outcome, checks, key):
    checkpoint = {"format": "aegislab-checkpoint-v1", "run_id": manifest["run_id"],
                  "evaluation_id": manifest["evaluation_id"], "manifest_digest": digest(manifest),
                  "event_count": len(events), "final_chain_digest": events[-1]["digest"],
                  "outcome_digest": digest(outcome), "checks_digest": digest(checks),
                  "key_id": key_id(key.public_key())}
    return {"format": "aegislab-evidence-v1", "manifest": manifest, "events": events,
            "outcome": outcome, "checks": checks, "checkpoint": checkpoint,
            "signature": base64.b64encode(key.sign(canonical(checkpoint))).decode("ascii")}


def verify(bundle, trusted_key, expected_run=None):
    try:
        if not isinstance(trusted_key, Ed25519PublicKey):
            raise TypeError("An Ed25519 public key is required")
        if set(bundle) != {"format", "manifest", "events", "outcome", "checks", "checkpoint", "signature"}:
            raise ValueError("Unexpected evidence fields")
        if bundle["format"] != "aegislab-evidence-v1":
            raise ValueError("Unsupported evidence format")
        checkpoint = bundle["checkpoint"]
        if checkpoint["key_id"] != key_id(trusted_key):
            raise ValueError("Trusted key does not match checkpoint")
        trusted_key.verify(base64.b64decode(bundle["signature"], validate=True), canonical(checkpoint))
        if checkpoint["format"] != "aegislab-checkpoint-v1":
            raise ValueError("Unsupported checkpoint")
        manifest = bundle["manifest"]
        if expected_run and manifest["run_id"] != expected_run:
            raise ValueError("Unexpected run identity")
        if checkpoint["run_id"] != manifest["run_id"] or checkpoint["evaluation_id"] != manifest["evaluation_id"]:
            raise ValueError("Run identity mismatch")
        for field in ("manifest", "outcome", "checks"):
            if checkpoint[field + "_digest"] != digest(bundle[field]):
                raise ValueError("Signed record digest mismatch")
        events = bundle["events"]
        if not events or len(events) > 128 or checkpoint["event_count"] != len(events):
            raise ValueError("Event count mismatch or truncated history")
        previous = "0" * 64
        for sequence, event in enumerate(events, 1):
            if set(event) != {"sequence", "previous_digest", "type", "data", "digest"}:
                raise ValueError("Unexpected event fields")
            record = {k: v for k, v in event.items() if k != "digest"}
            if event["sequence"] != sequence or event["previous_digest"] != previous or digest(record) != event["digest"]:
                raise ValueError("Event chain mismatch")
            previous = event["digest"]
        if checkpoint["final_chain_digest"] != previous:
            raise ValueError("Final chain digest mismatch")
    except (InvalidSignature, ValueError, TypeError, KeyError, IndexError, OverflowError):
        return {"valid": False, "detail": "Evidence verification failed against the trusted key/checkpoint."}
    return {"valid": True, "detail": "Signature, identity, event chain and signed record digests verified."}


def modified_copy(bundle):
    changed = copy.deepcopy(bundle)
    changed["events"][0]["data"]["modified_for_demo"] = True
    return changed


def main():
    parser = argparse.ArgumentParser(description="Independent, offline AegisLab evidence verification")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--public-key", type=Path, required=True)
    parser.add_argument("--expected-run")
    args = parser.parse_args()
    try:
        if args.bundle.stat().st_size > 1048576:
            raise ValueError("Bundle exceeds 1 MiB")
        bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        key = serialization.load_pem_public_key(args.public_key.read_bytes())
        result = verify(bundle, key, args.expected_run)
    except (OSError, ValueError, TypeError, RecursionError):
        result = {"valid": False, "detail": "Unable to read a valid evidence bundle and trusted public key."}
    print(("PASS: " if result["valid"] else "FAIL: ") + result["detail"])
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
