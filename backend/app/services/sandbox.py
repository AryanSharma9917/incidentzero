import json
import time
from urllib.parse import urlparse

from app.integrations.kubernetes import (
    KubernetesCollectionError,
    Runner,
    _subprocess_runner,
    parse_pod_evidence,
)
from app.models.incidents import NormalizedIncident
from app.models.kubernetes import KubernetesContext
from app.models.remediation import PolicyCheck, RemediationCandidate
from app.models.validation import SandboxValidation
from app.services.remediation import RemediationPolicyValidator


class SandboxVerifier:
    """Apply a revalidated patch only in the fixed, local Kind demo sandbox."""

    CONTEXT = "kind-incidentzero"
    NAMESPACE = "incidentzero-demo"
    SERVICE = "payment-api"
    HEALTH_ATTEMPTS = 3
    HEALTH_SCRIPT = (
        "import urllib.request; "
        "print(urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
        ".read().decode())"
    )

    def __init__(
        self,
        *,
        kubectl_binary: str = "kubectl",
        runner: Runner = _subprocess_runner,
        rollout_timeout: int = 90,
    ) -> None:
        if not 1 <= rollout_timeout <= 120:
            raise ValueError("Rollout timeout must be between 1 and 120 seconds")
        self._binary = kubectl_binary
        self._runner = runner
        self._timeout = rollout_timeout

    def _run(self, *args: str, timeout: int = 15) -> str:
        return self._runner(
            [self._binary, "--context", self.CONTEXT, "--request-timeout=10s", *args],
            timeout,
        )

    def is_local_context(self) -> bool:
        config = json.loads(self._run("config", "view", "--minify", "-o", "json"))
        clusters = config.get("clusters", [])
        contexts = config.get("contexts", [])
        server = urlparse(clusters[0].get("cluster", {}).get("server", "")) if len(clusters) == 1 else None
        local = (
            len(clusters) == len(contexts) == 1
            and contexts[0].get("name") == self.CONTEXT
            and contexts[0].get("context", {}).get("cluster") == self.CONTEXT
            and clusters[0].get("name") == self.CONTEXT
            and server is not None and server.scheme == "https"
            and server.hostname in {"127.0.0.1", "localhost", "::1"}
        )
        return local

    def validate(
        self,
        candidate: RemediationCandidate,
        incident: NormalizedIncident,
        context: KubernetesContext,
    ) -> SandboxValidation:
        checks: list[PolicyCheck] = []

        def check(name: str, passed: bool, message: str) -> bool:
            checks.append(PolicyCheck(name=name, passed=passed, message=message))
            return passed

        def result() -> SandboxValidation:
            return SandboxValidation(
                checks=checks,
                score=round(100 * sum(item.passed for item in checks) / len(checks)),
                passed=all(item.passed for item in checks),
            )

        if not check(
            "sandbox-target",
            incident.namespace == context.namespace == self.NAMESPACE
            and incident.service == context.service == self.SERVICE,
            "Only incidentzero-demo/payment-api permits writes.",
        ):
            return result()

        stage = "sandbox-context"
        try:
            local = self.is_local_context()
            if not check(stage, local, "Require the named Kind context and a loopback API server."):
                return result()

            stage = "patch-policy"
            deployment = json.loads(self._run(
                "get", "deployment", self.SERVICE, "-n", self.NAMESPACE, "-o", "json"
            ))
            metadata = deployment.get("metadata", {})
            identity_ok = (
                deployment.get("apiVersion") == "apps/v1"
                and deployment.get("kind") == "Deployment"
                and metadata.get("name") == self.SERVICE
                and metadata.get("namespace") == self.NAMESPACE
                and isinstance(metadata.get("uid"), str) and bool(metadata["uid"])
            )
            if not check("deployment-identity", identity_ok, "Require the exact live Deployment identity and UID."):
                return result()
            live_context = context.model_copy(update={"deployment": deployment})
            policy = RemediationPolicyValidator().validate(candidate, incident, live_context)
            if not check(stage, policy.passed, "Revalidate candidate against the live Deployment."):
                return result()

            stage = "sandbox-apply"
            self._run(
                "patch", "deployment", self.SERVICE, "-n", self.NAMESPACE,
                "--type=strategic", "--patch", candidate.patch_yaml,
            )
            check(stage, True, "Applied the policy-approved strategic-merge patch.")
            stage = "rollout"
            self._run(
                "rollout", "status", "deployment/payment-api", "-n", self.NAMESPACE,
                f"--timeout={self._timeout}s", timeout=self._timeout + 15,
            )
            check(stage, True, "Deployment rollout completed within the deadline.")

            stage = "pod-health"
            replicasets = json.loads(self._run(
                "get", "replicasets", "-n", self.NAMESPACE, "-o", "json"
            )).get("items", [])
            owned = {
                rs["metadata"]["uid"] for rs in replicasets
                if any(
                    owner.get("uid") == deployment.get("metadata", {}).get("uid")
                    and owner.get("kind") == "Deployment" and owner.get("controller") is True
                    for owner in rs.get("metadata", {}).get("ownerReferences", [])
                )
            }
            payload = json.loads(self._run(
                "get", "pods", "-n", self.NAMESPACE,
                "-l", "app.kubernetes.io/name=payment-api", "-o", "json",
            ))
            items = [
                pod for pod in payload.get("items", [])
                if not pod.get("metadata", {}).get("deletionTimestamp")
                and any(
                    owner.get("uid") in owned and owner.get("kind") == "ReplicaSet"
                    and owner.get("controller") is True
                    for owner in pod.get("metadata", {}).get("ownerReferences", [])
                )
            ]
            pods = parse_pod_evidence({"items": items})
            healthy = bool(pods) and all(
                pod.phase == "Running" and bool(pod.containers)
                and all(
                    c.ready and c.state == "running" and c.restart_count == 0
                    and c.termination_reason is None and c.exit_code is None
                    for c in pod.containers
                ) for pod in pods
            )
            observations = [
                {"pod": p.name, "phase": p.phase, "containers": [
                    {"name": c.name, "ready": c.ready, "state": c.state,
                     "restarts": c.restart_count, "termination": c.termination_reason,
                     "exit_code": c.exit_code} for c in p.containers
                ]} for p in pods
            ]
            if not check(stage, healthy, "Owned pod evidence: " + json.dumps(observations)):
                return result()
            for pod in pods:
                stage = "recent-logs"
                logs = self._run("logs", pod.name, "-n", self.NAMESPACE, "--tail=50")
                check(stage, not any(
                    word in logs.lower() for word in ("fatal", "traceback", "out of memory")
                ), "Recent logs inspected for fatal application errors.")
                stage = "http-health"
                health = None
                for attempt in range(self.HEALTH_ATTEMPTS):
                    try:
                        health = self._run(
                            "exec", pod.name, "-n", self.NAMESPACE,
                            "--", "python", "-c", self.HEALTH_SCRIPT,
                        )
                        break
                    except KubernetesCollectionError:
                        if attempt + 1 == self.HEALTH_ATTEMPTS:
                            break
                        time.sleep(1)
                body = json.loads(health) if health is not None else None
                check(stage, isinstance(body, dict) and body.get("status") == "ok",
                      "The replacement pod /health must return status ok.")
        except (KubernetesCollectionError, ValueError, KeyError, TypeError, AttributeError):
            check(stage, False, "Sandbox operation failed or returned malformed evidence.")
        return result()
