"""Controlled configuration simulation, never a Kubernetes or model-output substitute."""
import copy
from pathlib import Path

import yaml

from app.models.incidents import DemoScenario, NormalizedIncident
from app.models.kubernetes import ContainerEvidence, KubernetesContext, PodEvidence
from app.models.remediation import PolicyCheck, RemediationCandidate
from app.models.validation import SandboxValidation
from app.services.remediation import RemediationPolicyValidator, _memory_bytes


def merge_configuration(original: dict, patch: dict) -> dict:
    """Merge trusted fixtures or policy-approved fields, including named container/env lists."""
    result = copy.deepcopy(original)
    for key, value in patch.items():
        if isinstance(value, dict):
            result[key] = merge_configuration(result.get(key, {}), value)
        elif isinstance(value, list) and all(isinstance(item, dict) and "name" in item for item in value):
            items = {item["name"]: item for item in result.get(key, [])}
            for item in value:
                items[item["name"]] = merge_configuration(items.get(item["name"], {}), item)
            result[key] = list(items.values())
        else:
            result[key] = copy.deepcopy(value)
    return result


class SimulationController:
    def __init__(self):
        self.deployment: dict = {}
        self.verifier = self

    def prepare(self, scenario: DemoScenario):
        root = Path(__file__).resolve().parents[3] / "sandbox"
        base = yaml.safe_load((root / "base/deployment.yaml").read_text())
        patch = yaml.safe_load((root / "incidents" / scenario.value / "patch.yaml").read_text())
        self.deployment = merge_configuration(base, patch)

    def collect(self, service: str, namespace: str) -> KubernetesContext:
        if service != "payment-api" or namespace != "incidentzero-demo":
            raise ValueError("Simulation only supports the controlled demo workload")
        container = self.deployment["spec"]["template"]["spec"]["containers"][0]
        env = {item["name"]: item.get("value", "") for item in container["env"]}
        limit = _memory_bytes(container["resources"]["limits"]["memory"]) or 0
        oom = int(env["MEMORY_LOAD_MB"]) * 1024**2 > limit
        crash = env["DATABASE_HOST"] != "database"
        probe = container["readinessProbe"]["httpGet"]
        unready = probe["path"] != "/health" or probe["port"] not in {"http", 8080}
        healthy = not (oom or crash or unready)
        reason = "OOMKilled" if oom else "Error" if crash else None
        log = "process allocating memory" if oom else f"fatal: DATABASE_HOST={env['DATABASE_HOST']}" if crash else "payment-api listening on :8080"
        event = "Memory limit exceeded; exit 137" if oom else "Back-off restarting container" if crash else "Readiness probe returned HTTP 404" if unready else "Container ready"
        return KubernetesContext(
            namespace=namespace, service=service,
            pods=[PodEvidence(name="payment-api-simulated", phase="Running", containers=[ContainerEvidence(
                name=service, ready=healthy, restart_count=1 if oom or crash else 0,
                state="waiting" if oom or crash else "running", termination_reason=reason,
                exit_code=137 if oom else 1 if crash else None,
                requests=container["resources"]["requests"], limits=container["resources"]["limits"],
            )])],
            events=[{"type": "Normal" if healthy else "Warning", "reason": "Simulation", "message": event}],
            deployment=copy.deepcopy(self.deployment), describe="SIMULATED infrastructure evidence: " + event,
            logs="SIMULATED application log: " + log,
            previous_logs="SIMULATED prior termination: " + log if reason else None,
        )

    def validate(self, candidate: RemediationCandidate, incident: NormalizedIncident,
                 context: KubernetesContext) -> SandboxValidation:
        policy = RemediationPolicyValidator().validate(candidate, incident, context)
        checks = [PolicyCheck(name="simulation-policy", passed=policy.passed,
                              message="SIMULATED validation: candidate passed the real configuration allow-list." if policy.passed else "Candidate rejected by the configuration policy.")]
        if policy.passed:
            self.deployment = merge_configuration(self.deployment, yaml.safe_load(candidate.patch_yaml))
            evidence = self.collect(incident.service, incident.namespace)
            healthy = all(c.ready and c.restart_count == 0 for pod in evidence.pods for c in pod.containers)
            checks.append(PolicyCheck(name="simulation-configuration", passed=healthy,
                                      message="SIMULATED configuration evaluation only; no rollout, pod, log, or HTTP health check was executed."))
        return SandboxValidation(checks=checks, score=round(100 * sum(c.passed for c in checks) / len(checks)),
                                 passed=all(c.passed for c in checks))
