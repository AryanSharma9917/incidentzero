import json
import time
from pathlib import Path

from app.integrations.kubernetes import KubernetesContextCollector, KubernetesCollectionError
from app.models.incidents import DemoScenario
from app.services.sandbox import SandboxVerifier


class DemoController:
    """Fixed repository scenarios in the ownership-checked local Kind sandbox only."""

    def __init__(self, verifier: SandboxVerifier):
        self.verifier = verifier

    def collect(self, service: str, namespace: str):
        return KubernetesContextCollector(runner=lambda args, timeout: self.verifier._run(
            *args[1:], timeout=timeout,
        )).collect(service, namespace)

    def prepare(self, scenario: DemoScenario):
        verifier = self.verifier
        if not verifier.is_local_context():
            raise KubernetesCollectionError("Demo requires the local Kind sandbox.")
        # No user-provided paths, resource identities, commands, or context names.
        directory = Path(__file__).resolve().parents[3] / "sandbox" / "incidents" / scenario.value
        previous = json.loads(verifier._run(
            "get", "pods", "-n", verifier.NAMESPACE,
            "-l", "app.kubernetes.io/name=payment-api", "-o", "json",
        ))
        previous_names = {pod["metadata"]["name"] for pod in previous.get("items", [])}
        verifier._run("apply", "-k", str(directory))
        verifier._run("rollout", "restart", "deployment/payment-api", "-n", verifier.NAMESPACE)
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                context = self.collect(verifier.SERVICE, verifier.NAMESPACE)
                if any(pod.name in previous_names for pod in context.pods):
                    time.sleep(1)
                    continue
                containers = [c for p in context.pods for c in p.containers]
                if scenario == DemoScenario.OOM_KILLED:
                    observed = any(c.termination_reason == "OOMKilled" and c.exit_code == 137 for c in containers)
                elif scenario == DemoScenario.CRASH_LOOP:
                    observed = any(c.restart_count > 0 for c in containers) and "db-invalid" in (
                        context.logs + (context.previous_logs or "")
                    )
                else:
                    # Ensure this is the newly configured broken workload, with real probe evidence.
                    observed = any(c.state == "running" and not c.ready for c in containers) and any(
                        "404" in json.dumps(event) for event in context.events
                    )
                if observed:
                    return
            except KubernetesCollectionError:
                pass
            time.sleep(1)
        raise KubernetesCollectionError("Demo fault evidence was not ready within 60 seconds.")
