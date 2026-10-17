"""Five-run acceptance recorder. Plan-only unless both execution/quota flags are supplied."""
import argparse
import asyncio
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, Field

from app.config.settings import settings
from app.models.runs import RunRecord
from app.services.sandbox import SandboxVerifier
from app.integrations.kubernetes import parse_pod_evidence


class AcceptanceRecord(BaseModel):
    sequence: int
    incident_id: str
    run_id: str
    status: str
    mode: str
    score: int | None = None
    attempts: int | None = None
    passed: bool
    finished_at: str | None = None
    check_names: list[str] = Field(default_factory=list)


def assess_run(run: RunRecord, sequence: int) -> AcceptanceRecord:
    result = run.result
    history = result.get("validation_history", [])
    checks = history[-1].get("checks", []) if history else []
    expected = {"sandbox-target", "sandbox-context", "patch-policy", "deployment-identity",
                "sandbox-apply", "rollout", "pod-health", "recent-logs", "http-health"}
    names = {check.get("name") for check in checks}
    context = result.get("cluster_context", {})
    oom = any(c.get("termination_reason") == "OOMKilled" and c.get("exit_code") == 137
              for pod in context.get("pods", []) for c in pod.get("containers", []))
    attempts = result.get("iteration_count")
    passed = (run.status == "verified" and result.get("execution_mode") == "kubernetes"
              and result.get("validation_passed") is True and result.get("validation_score") == 100
              and isinstance(attempts, int) and not isinstance(attempts, bool) and 1 <= attempts <= 2
              and bool(run.finished_at) and bool(result.get("final_report")) and oom
              and expected.issubset(names) and all(check.get("passed") is True for check in checks))
    return AcceptanceRecord(sequence=sequence, incident_id=run.incident_id, run_id=run.id,
                            status=run.status, mode=result.get("execution_mode", "unknown"),
                            score=result.get("validation_score"), attempts=attempts, passed=passed,
                            finished_at=run.finished_at, check_names=sorted(name for name in names if isinstance(name, str)))


def reset_local_lab(verifier: SandboxVerifier) -> None:
    if not verifier.is_local_context():
        raise RuntimeError("Reset refused: fixed local Kind context guard failed")
    base = Path(__file__).resolve().parents[2] / "sandbox" / "base"
    verifier._run("apply", "-k", str(base))
    verifier._run("rollout", "restart", "deployment/payment-api", "-n", verifier.NAMESPACE)
    verifier._run("rollout", "status", "deployment/payment-api", "-n", verifier.NAMESPACE,
                  "--timeout=90s", timeout=105)
    payload = json.loads(verifier._run("get", "pods", "-n", verifier.NAMESPACE,
                                     "-l", "app.kubernetes.io/name=payment-api", "-o", "json"))
    pods = parse_pod_evidence(payload)
    if not pods or not all(p.phase == "Running" and p.containers and all(c.ready and c.restart_count == 0 for c in p.containers) for p in pods):
        raise RuntimeError("Reset completed without a healthy zero-restart baseline")


async def record(api_url: str, output: Path, verifier: SandboxVerifier):
    records: list[AcceptanceRecord] = []
    summary = {"status": "incomplete", "reasoning": "configured live service; transport not independently attested",
               "infrastructure": "API-reported local Kubernetes with fixed-context reset",
               "created_at": datetime.now(timezone.utc).isoformat(), "records": [], "reset_healthy": False}
    output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        summary["records"] = [item.model_dump(mode="json") for item in records]
        output.write_text(json.dumps(summary, indent=2) + "\n")
    headers = {"X-Demo-Run-Token": os.environ["DEMO_RUN_TOKEN"]} if os.environ.get("DEMO_RUN_TOKEN") else {}
    # Raw upstream error bodies/headers and provider credentials are never saved.
    try:
        async with httpx.AsyncClient(base_url=api_url, timeout=20, headers=headers) as client:
            test_probe = await client.get("/__test__/reset")
            if test_probe.status_code != 404:
                raise RuntimeError("Refusing a known browser-test fixture API")
            runtime_response = await client.get("/api/runtime")
            runtime_response.raise_for_status()
            runtime = runtime_response.json()
            if runtime.get("execution_mode") != "kubernetes" or not runtime.get("runs_enabled") or not runtime.get("provider_configured"):
                raise RuntimeError("API must report enabled local Kubernetes execution with a configured provider")
            history = await client.get("/api/runs")
            history.raise_for_status()
            if any(item["status"] in {"queued", "running"} for item in history.json()):
                raise RuntimeError("Refusing acceptance while another run is active")
            today = datetime.now(timezone.utc).date().isoformat()
            used_today = sum(str(item.get("created_at", "")).startswith(today) for item in history.json())
            if int(runtime.get("daily_run_limit", 0)) - used_today < 5:
                raise RuntimeError("Daily run-start allowance is insufficient for five acceptance runs")
            for sequence in range(1, 6):
                created = await client.post("/api/incidents/demo/oomkilled")
                created.raise_for_status()
                incident_id = created.json()["id"]
                started = await client.post(f"/api/incidents/{incident_id}/run")
                started.raise_for_status()
                run_id = started.json()["id"]
                deadline = time.monotonic() + 720
                while True:
                    response = await client.get(f"/api/runs/{run_id}")
                    response.raise_for_status()
                    run = RunRecord.model_validate(response.json())
                    if run.status in {"verified", "failed", "simulated"}:
                        break
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Acceptance polling deadline exceeded; inspect active run before reset")
                    await asyncio.sleep(1)
                result = assess_run(run, sequence)
                records.append(result)
                save()
                print(f"Run {sequence}/5: {'PASS' if result.passed else 'FAIL'} ({run.id})")
                if not result.passed:
                    break
            # Reset only after terminal API results; never race an active worker.
            reset_local_lab(verifier)
            summary["reset_healthy"] = True
            summary["status"] = "passed" if len(records) == 5 and all(item.passed for item in records) else "failed"
    except Exception:
        summary["error"] = "Acceptance interrupted. Inspect server/run state before any reset; raw error omitted."
        raise
    finally:
        save()
    return summary["status"] == "passed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Actually start five demo runs")
    parser.add_argument("--allow-provider-quota", action="store_true", help="Explicitly authorize live provider quota for this command")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, default=Path("artifacts/golden-path-results.json"))
    args = parser.parse_args()
    if not args.execute:
        print("PLAN ONLY: five sequential OOMKilled runs; verify live-mode API results, save evidence, then reset the fixed Kind lab. No HTTP/provider/Kubernetes calls made.")
        return
    if not args.allow_provider_quota:
        parser.error("Execution requires --allow-provider-quota")
    address = urlparse(args.api_url)
    if address.scheme != "http" or address.hostname not in {"localhost", "127.0.0.1", "::1"} or address.username or address.password or address.path not in {"", "/"} or address.query or address.fragment:
        parser.error("Acceptance requires a loopback HTTP API origin")
    if not settings.nebius_api_key or settings.app_environment != "local" or settings.execution_mode != "kubernetes":
        parser.error("Configure local Kubernetes mode and Nebius credentials before acceptance")
    if not shutil.which(settings.kubectl_binary):
        parser.error("kubectl is unavailable; no provider request was made")
    verifier = SandboxVerifier(kubectl_binary=settings.kubectl_binary)
    if not verifier.is_local_context():
        parser.error("Fixed Kind context guard failed; no provider request was made")
    try:
        passed = asyncio.run(record(args.api_url.rstrip("/"), args.output, verifier))
    except Exception:
        print("Acceptance interrupted; inspect the sanitized evidence file and active server state before resetting.")
        raise SystemExit(1) from None
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
