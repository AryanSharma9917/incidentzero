"""Read-only deployed smoke check. No POST, model requests, keys, or cluster operations."""
import argparse
import json
from urllib.request import urlopen
from urllib.parse import urlparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend", required=True)
    parser.add_argument("--backend", required=True)
    args = parser.parse_args()
    for address in (args.frontend, args.backend):
        parsed = urlparse(address)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            parser.error("Provide public HTTPS origins without credentials or query strings")
    with urlopen(args.frontend.rstrip("/") + "/dashboard", timeout=60) as response:
        assert response.status == 200, "Frontend did not return 200"
    with urlopen(args.backend.rstrip("/") + "/health", timeout=60) as response:
        assert json.load(response)["status"] == "ok", "Backend health failed"
    with urlopen(args.backend.rstrip("/") + "/api/runtime", timeout=60) as response:
        runtime = json.load(response)
        assert runtime["execution_mode"] == "simulation", "Hosted execution must use labeled simulation"
        assert not runtime["runs_enabled"] or runtime["access_code_required"], "Hosted writes must require an access code"
    print("PASS: frontend, backend health, and runtime configuration (read-only checks; no provider calls)")


if __name__ == "__main__":
    main()
