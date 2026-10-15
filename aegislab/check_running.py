"""Check the already-running local backend. Database queries execute in that server."""
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

BASE_URL = "http://localhost:8000"


def request(path: str) -> tuple[int, str]:
    try:
        with urlopen(BASE_URL + path, timeout=20) as response:
            return response.status, response.read().decode("utf-8")
    except HTTPError as error:
        return error.code, ""


def main() -> int:
    print("AegisLab: checking the existing server at " + BASE_URL)
    print("Database probes run in the server process; this is an HTTP smoke check.")
    checks = []
    try:
        code, body = request("/health/live")
        live = json.loads(body) if code == 200 else {}
        checks.append(("Backend liveness: HTTP 200", code == 200 and live.get("status") == "running"))

        code, body = request("/health/ready")
        ready = json.loads(body) if code == 200 else {}
        database = ready.get("database", {})
        checks.append(("Readiness: HTTP 200", code == 200 and ready.get("ready") is True))
        checks.append(("Real PostgreSQL probe through the running server", database.get("status") == "connected"))
        checks.append(("Migration checksums and foundation record", database.get("schema_status") == "ready"))

        code, body = request("/api/status")
        status = json.loads(body) if code == 200 else {}
        checks.append(("Status endpoint: current, ready and security unverified",
                       code == 200 and status.get("ready") is True
                       and status.get("security_validation") == "unverified"))

        code, body = request("/")
        labels = ("Private Submissions", "Version Locking", "Isolated Evaluation",
                  "Evidence", "Role-Specific Reports", "Security: UNVERIFIED")
        checks.append(("Dashboard: workflow labels and no JavaScript",
                       code == 200 and all(label in body for label in labels)
                       and "<script" not in body.lower()))

        code, body = request("/static/dashboard.css")
        checks.append(("Dashboard CSS asset", code == 200 and bool(body.strip())))
        code, body = request("/api/docs")
        checks.append(("HTML/CSS API reference", code == 200 and "<script" not in body.lower()))
    except (URLError, OSError, ValueError):
        print("FAIL: could not complete HTTP checks. Keep the local server running and check its status.")
        return 1

    for label, passed in checks:
        print(("PASS" if passed else "FAIL") + ": " + label)
    print("Worker isolation, participant authorization and signed evidence: UNVERIFIED / not implemented.")
    return 0 if all(passed for _, passed in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
