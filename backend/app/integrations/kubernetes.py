import json
import re
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

from app.models.kubernetes import ContainerEvidence, KubernetesContext, PodEvidence


class KubernetesCollectionError(RuntimeError):
    """Raised when Kubernetes evidence cannot be collected safely."""


Runner = Callable[[Sequence[str], int], str]
DNS_LABEL = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")


def _subprocess_runner(command: Sequence[str], timeout: int) -> str:
    try:
        completed = subprocess.run(
            list(command),
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise KubernetesCollectionError(f"Kubernetes command failed: {command[1]}") from exc
    return completed.stdout


def _state_name(state: dict[str, Any]) -> str:
    for name in ("running", "waiting", "terminated"):
        if state.get(name) is not None:
            return name
    return "unknown"


def parse_pod_evidence(payload: dict[str, Any]) -> list[PodEvidence]:
    pods: list[PodEvidence] = []
    for item in payload.get("items", []):
        statuses = {
            status["name"]: status for status in item.get("status", {}).get("containerStatuses", [])
        }
        containers: list[ContainerEvidence] = []
        for container in item.get("spec", {}).get("containers", []):
            status = statuses.get(container["name"], {})
            last_terminated = status.get("lastState", {}).get("terminated") or {}
            current_terminated = status.get("state", {}).get("terminated") or {}
            termination = current_terminated or last_terminated
            containers.append(
                ContainerEvidence(
                    name=container["name"],
                    ready=status.get("ready", False),
                    restart_count=status.get("restartCount", 0),
                    state=_state_name(status.get("state", {})),
                    termination_reason=termination.get("reason"),
                    exit_code=termination.get("exitCode"),
                    requests=container.get("resources", {}).get("requests", {}),
                    limits=container.get("resources", {}).get("limits", {}),
                )
            )
        pods.append(
            PodEvidence(
                name=item["metadata"]["name"],
                phase=item.get("status", {}).get("phase", "Unknown"),
                containers=containers,
            )
        )
    return pods


class KubernetesContextCollector:
    """Read-only, allow-listed kubectl evidence collector."""

    def __init__(
        self,
        *,
        kubectl_binary: str = "kubectl",
        timeout_seconds: int = 15,
        runner: Runner = _subprocess_runner,
    ) -> None:
        self._kubectl = kubectl_binary
        self._timeout = timeout_seconds
        self._runner = runner

    def _run(self, *arguments: str) -> str:
        return self._runner([self._kubectl, *arguments], self._timeout)

    def collect(self, service: str, namespace: str) -> KubernetesContext:
        for label, value in (("service", service), ("namespace", namespace)):
            if not DNS_LABEL.fullmatch(value):
                raise ValueError(f"Invalid Kubernetes {label} name")

        pods_payload = json.loads(
            self._run(
                "get", "pods", "-n", namespace, "-l", f"app.kubernetes.io/name={service}", "-o", "json"
            )
        )
        pods = parse_pod_evidence(pods_payload)
        if not pods:
            raise KubernetesCollectionError(f"No pods found for service {service}")
        pods.sort(
            key=lambda pod: (
                all(container.ready for container in pod.containers),
                -sum(container.restart_count for container in pod.containers),
            )
        )
        pod_name = pods[0].name

        events = json.loads(
            self._run(
                "get", "events", "-n", namespace, "--field-selector", f"involvedObject.name={pod_name}", "-o", "json"
            )
        ).get("items", [])
        deployment = json.loads(
            self._run("get", "deployment", service, "-n", namespace, "-o", "json")
        )
        describe = self._run("describe", "pod", pod_name, "-n", namespace)
        logs = self._run("logs", pod_name, "-n", namespace, "--tail=200")
        try:
            previous_logs = self._run(
                "logs", pod_name, "-n", namespace, "--previous", "--tail=200"
            )
        except KubernetesCollectionError:
            previous_logs = None

        return KubernetesContext(
            namespace=namespace,
            service=service,
            pods=pods,
            events=events,
            deployment=deployment,
            describe=describe,
            logs=logs,
            previous_logs=previous_logs,
        )
