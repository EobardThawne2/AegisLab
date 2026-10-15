"""Repeatable live showcase. Reuses fixtures, appends a fresh lock/run; never deletes data."""
import json
from urllib.error import URLError

from cryptography.hazmat.primitives import serialization

from aegislab.config import ROOT
from aegislab.demo_phase2 import Client, fixture
from aegislab.demo_setup import CREDENTIALS
from aegislab.evidence import modified_copy, verify


def main():
    checks = []
    clients = {}

    def check(condition, label):
        if not condition:
            raise RuntimeError(label)
        checks.append(label)
        print("PASS: " + label, flush=True)

    try:
        credentials = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
        names = {"red": "red-showcase.json", "blue": "blue-v1.json", "client": "model-v1.json", "evaluator": "policy-v1.json"}
        versions = {}
        for role, name in names.items():
            client = Client()
            code, result = client.call("/api/auth/login", "POST", credentials[role])
            check(code == 200, "Authenticated synthetic " + role)
            client.csrf = result["csrf_token"]
            clients[role] = client
            code, version = client.call("/api/submissions", "POST", fixture(name))
            check(code == 201, "Stored immutable " + role + " fixture")
            versions[role] = version
        evaluator = clients["evaluator"]
        references = {role + "_version_id": versions[owner]["id"] for role, owner in
                      (("red", "red"), ("blue", "blue"), ("model", "client"), ("policy", "evaluator"))}
        code, evaluation = evaluator.call("/api/evaluations", "POST", references)
        check(code == 201, "Created a new fixed-version evaluation")
        code, _ = clients["red"].call("/api/evaluations/" + evaluation["id"] + "/runs", "POST", {})
        check(code == 403, "Participant cannot start an evaluator-owned run")
        code, run = evaluator.call("/api/evaluations/" + evaluation["id"] + "/runs", "POST", {})
        check(code == 201 and run["status"] == "completed", "Completed a real bounded fixture evaluation")
        run_id = run["id"]
        code, report = evaluator.call("/api/runs/" + run_id + "/report")
        check(code == 200 and report["outcome"]["turns"] == 2 and report["outcome"]["blocked"] == 1
              and report["outcome"]["mock_model_calls"] == 1, "Observed one allowed mock call and one blocked attack")
        check(sum(item["status"] == "UNVERIFIED" for item in report["checks"]) == 5,
              "All five unexecuted worker checks remain UNVERIFIED")
        for role, field in (("red", "red_version_id"), ("blue", "blue_version_id"), ("client", "model_version_id")):
            code, limited = clients[role].call("/api/runs/" + run_id + "/report")
            check(code == 200 and set(limited["versions"]) == {field} and not limited["events"]
                  and not limited["can_export"], role + " report contains only its authorized reference")
        code, _ = clients["red"].call("/api/runs/" + run_id + "/evidence")
        check(code == 403, "Participant evidence export denied")
        code, result = evaluator.call("/api/runs/" + run_id + "/verify", "POST", {"source": "original"})
        check(code == 200 and result["valid"], "Original evidence verifies against the configured public key")
        code, result = evaluator.call("/api/runs/" + run_id + "/verify", "POST", {"source": "modified_copy"})
        check(code == 200 and not result["valid"], "Modified evidence copy fails verification")
        code, bundle = evaluator.call("/api/runs/" + run_id + "/evidence")
        check(code == 200, "Exported original signed evidence")
        encoded = json.dumps(bundle)
        forbidden = [fixture("red-showcase.json")["config"]["prompts"][0],
                     fixture("red-showcase.json")["config"]["prompts"][1],
                     fixture("model-v1.json")["config"]["response"],
                     *fixture("blue-v1.json")["config"]["blocked_terms"]]
        check(all(value not in encoded for value in forbidden), "Evidence excludes raw prompts, defense terms and model response")
        with evaluator.opener.open("http://localhost:8000/api/verification-key", timeout=45) as response:
            key_bytes = response.read()
        key = serialization.load_pem_public_key(key_bytes)
        check(verify(bundle, key, run_id)["valid"] and not verify(modified_copy(bundle), key, run_id)["valid"],
              "Independent verifier accepts original and rejects modified copy")
        code, _ = clients["red"].call("/api/submissions/" + versions["blue"]["id"])
        check(code == 404, "Known Blue artifact retrieval denied to Red (404)")
        directory = ROOT / "local-data" / "exports"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "original.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
        (directory / "modified.json").write_text(json.dumps(modified_copy(bundle), indent=2), encoding="utf-8")
        (directory / "verification-key.pem").write_bytes(key_bytes)
        receipt = {"run_id": run_id, "evaluation_id": evaluation["id"], "checks": checks,
                   "blue_version_id": versions["blue"]["id"], "mode": "fixture_no_isolation"}
        (ROOT / "local-data" / "showcase_receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print(str(len(checks)) + " live checks passed. Run: " + run_id)
        print("Open http://localhost:8000/workspace/runs/" + run_id)
        print("Offline exports: local-data/exports. Worker isolation remains UNVERIFIED.")
        return 0
    except RuntimeError as error:
        print("FAIL: " + str(error))
    except (OSError, URLError, ValueError, KeyError, TypeError):
        print("Showcase could not finish. Check local server readiness, setup and signing key; no secrets logged.")
    finally:
        for client in clients.values():
            try:
                client.call("/api/auth/logout", "POST")
            except (OSError, URLError, ValueError):
                pass
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
