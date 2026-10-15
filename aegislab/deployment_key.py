"""Prepare a private deployment key file without printing any key material."""
import base64
import os

from cryptography.hazmat.primitives import serialization

from aegislab.config import ROOT
from aegislab.evidence import ensure_local_key, key_id, load_signer


def main():
    ensure_local_key()
    key = load_signer()
    target = ROOT / "local-data" / "deployment-key.env"
    raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                            serialization.NoEncryption())
    try:
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print("Private deployment-key.env already exists; it was not overwritten.")
        return 0
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write("AEGISLAB_SIGNING_KEY=" + base64.b64encode(raw).decode("ascii") + "\n")
    print("Private deployment setting written to local-data/deployment-key.env. Keep off screen.")
    print("Public key fingerprint: " + key_id(key.public_key()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
