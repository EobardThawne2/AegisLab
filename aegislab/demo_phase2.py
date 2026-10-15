"""Real Phase 2 demonstration against the local server; credentials are never printed."""
import json
import sys
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from aegislab.config import ROOT
from aegislab.demo_setup import CREDENTIALS
from aegislab.documents import validate_document

BASE = "http://localhost:8000"


class Client:
    def __init__(self):
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        self.csrf = ""

    def call(self, path, method="GET", document=None, include_csrf=True):
        headers = {"Accept": "application/json"}
        if self.csrf and include_csrf:
            headers["X-CSRF-Token"] = self.csrf
        data = None
        if document is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(document).encode("utf-8")
        request = Request(BASE + path, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=45) as response:
                return response.status, json.loads(response.read())
        except HTTPError as error:
            try:
                body = json.loads(error.read())
            except (ValueError, UnicodeError):
                body = {}
            return error.code, body


def fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text(encoding="utf-8"))


def main():
    checks = []

    def check(condition, label):
        if not condition:
            raise RuntimeError(label)
        checks.append(label)
        print("PASS: " + label, flush=True)

    try:
        print("AegisLab Phase 2: real authenticated requests to " + BASE, flush=True)
        anonymous = Client()
        code, health = anonymous.call("/health/live")
        check(code == 200 and health.get("phase") in (2, "web-showcase"), "Phase 2 backend is running")
        code, _ = anonymous.call("/api/submissions")
        check(code == 401, "Unauthenticated submission listing denied (401)")
        credentials = json.loads(CREDENTIALS.read_text(encoding="utf-8"))
        clients = {}
        for role in ("red", "blue", "client", "evaluator"):
            client = Client()
            code, result = client.call("/api/auth/login", "POST", credentials[role])
            check(code == 200 and result.get("actor", {}).get("role") == role, "Authenticated synthetic " + role + " participant")
            client.csrf = result["csrf_token"]
            clients[role] = client

        versions = {}
        names = {"red": "red-v1.json", "blue": "blue-v1.json", "client": "model-v1.json", "evaluator": "policy-v1.json"}
        for role, name in names.items():
            document = fixture(name)
            code, version = clients[role].call("/api/submissions", "POST", document)
            check(code == 201 and version.get("digest") == validate_document(document)[1], role + " fixture stored with its content digest")
            versions[role] = version
            print("  v" + str(version["version_number"]) + " " + version["id"], flush=True)
            print("  SHA-256 " + version["digest"], flush=True)

        code, repeated = clients["red"].call("/api/submissions", "POST", fixture("red-v1.json"))
        check(code == 201 and repeated.get("id") == versions["red"]["id"] and repeated.get("reused_existing_version"),
              "Identical resubmission reuses the immutable version")
        code, listing = clients["red"].call("/api/submissions")
        check(code == 200 and all(row["owner_role"] == "red" and "document" not in row for row in listing["versions"]),
              "Red listing contains only its own version metadata")
        code, denied = clients["red"].call("/api/submissions/" + versions["blue"]["id"])
        check(code == 404 and denied == {"detail": "Not found"}, "Red retrieval of the known Blue artifact denied (404)")
        code, _ = clients["evaluator"].call("/api/submissions/" + versions["blue"]["id"])
        check(code == 404, "Evaluator cannot retrieve another participant's private document")
        code, metadata = clients["evaluator"].call("/api/evaluation-references")
        check(code == 200 and all("document" not in row and "canonical_document" not in row for row in metadata["versions"]),
              "Evaluator coordination endpoint returns metadata only")
        code, _ = clients["red"].call("/api/evaluation-references")
        check(code == 403, "Non-evaluator coordination listing denied (403)")
        code, _ = clients["red"].call("/api/submissions", "POST", fixture("blue-v1.json"))
        check(code == 403, "Cross-role artifact submission denied (403)")
        code, _ = clients["red"].call("/api/submissions", "POST", fixture("red-v1.json"), include_csrf=False)
        check(code == 403, "State-changing request without CSRF token denied (403)")
        malformed = fixture("red-v1.json")
        malformed["config"]["command"] = "unsupported"
        code, _ = clients["red"].call("/api/submissions", "POST", malformed)
        check(code == 422, "Unsupported submission fields rejected (422)")

        references = {"red_version_id": versions["red"]["id"], "blue_version_id": versions["blue"]["id"],
                      "model_version_id": versions["client"]["id"], "policy_version_id": versions["evaluator"]["id"]}
        code, evaluation = clients["evaluator"].call("/api/evaluations", "POST", references)
        check(code == 201 and evaluation.get("status") == "locked" and len(evaluation.get("versions", {})) == 4,
              "Evaluator created an evaluation with four fixed versions")
        code, newer = clients["red"].call("/api/submissions", "POST", fixture("red-v2.json"))
        check(code == 201 and newer.get("id") != versions["red"]["id"] and newer.get("version_number", 0) > versions["red"]["version_number"],
              "New Red content has a distinct, newer version")
        code, locked = clients["evaluator"].call("/api/evaluations/" + evaluation["id"])
        check(code == 200 and all(locked["versions"][key]["id"] == value for key, value in references.items()),
              "Evaluation still references all original locked versions")
        code, old = clients["red"].call("/api/submissions/" + versions["red"]["id"])
        check(code == 200 and old.get("document") == fixture("red-v1.json"), "Original private Red document remains unchanged")
        code, red_view = clients["red"].call("/api/evaluations/" + evaluation["id"])
        check(code == 200 and set(red_view.get("versions", {})) == {"red_version_id"},
              "Red evaluation view exposes only its own version reference")
        code, _ = clients["red"].call("/api/submissions/" + versions["red"]["id"], "PUT", fixture("red-v2.json"))
        check(code == 405, "Artifact replacement is not exposed by the API (405)")
        code, _ = clients["red"].call("/api/auth/logout", "POST")
        check(code == 200, "Session logout completed")
        code, _ = clients["red"].call("/api/submissions")
        check(code == 401, "Logged-out session cannot list private submissions")

        receipt = {"evaluation_id": evaluation["id"], "locked_versions": references,
                   "digests": {role: value["digest"] for role, value in versions.items()},
                   "new_red_version_id": newer["id"], "blue_version_for_denial_demo": versions["blue"]["id"],
                   "checks": checks, "scope": "Phase 2 HTTP/API behavior only; not signed evaluation evidence"}
        path = ROOT / "local-data" / "phase2_receipt.json"
        path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        print("Evaluation: " + evaluation["id"], flush=True)
        print("Blue version for the recording's Red access attempt: " + versions["blue"]["id"], flush=True)
        print(str(len(checks)) + " live checks passed. Receipt: local-data/phase2_receipt.json", flush=True)
        print("This script checks private versions only. Run demo_showcase for signed fixture evidence. Worker isolation is unimplemented.")
        return 0
    except RuntimeError as error:
        print("FAIL: " + str(error))
    except (OSError, URLError, ValueError, KeyError, TypeError):
        print("Demo could not finish. Check the running Phase 2 server and run the private demo setup first.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
