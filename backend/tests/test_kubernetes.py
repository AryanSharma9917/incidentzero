import json

import pytest

from app.integrations.kubernetes import KubernetesContextCollector, parse_pod_evidence


PODS = {
    "items": [
        {
            "metadata": {"name": "payment-api-abc"},
            "spec": {
                "containers": [
                    {
                        "name": "payment-api",
                        "resources": {
                            "requests": {"memory": "32Mi"},
                            "limits": {"memory": "64Mi"},
                        },
                    }
                ]
            },
            "status": {
                "phase": "Running",
                "containerStatuses": [
                    {
                        "name": "payment-api",
                        "ready": False,
                        "restartCount": 3,
                        "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                        "lastState": {
                            "terminated": {"reason": "OOMKilled", "exitCode": 137}
                        },
                    }
                ],
            },
        }
    ]
}


def test_parse_pod_evidence_extracts_oom_details() -> None:
    pod = parse_pod_evidence(PODS)[0]
    container = pod.containers[0]
    assert container.restart_count == 3
    assert container.state == "waiting"
    assert container.termination_reason == "OOMKilled"
    assert container.exit_code == 137
    assert container.limits == {"memory": "64Mi"}


def test_collector_uses_only_expected_read_commands() -> None:
    commands: list[list[str]] = []

    def runner(command, timeout):
        commands.append(list(command))
        if command[1:3] == ["get", "pods"]:
            return json.dumps(PODS)
        if command[1:3] == ["get", "events"]:
            return json.dumps({"items": [{"reason": "BackOff"}]})
        if command[1:3] == ["get", "deployment"]:
            return json.dumps({"metadata": {"name": "payment-api"}})
        if command[1:3] == ["describe", "pod"]:
            return "Name: payment-api-abc"
        if command[1] == "logs":
            return "application log"
        raise AssertionError(command)

    context = KubernetesContextCollector(runner=runner).collect(
        "payment-api", "incidentzero-demo"
    )
    assert context.pods[0].containers[0].termination_reason == "OOMKilled"
    assert context.previous_logs == "application log"
    assert {command[1] for command in commands} == {"get", "describe", "logs"}


def test_collector_prefers_unhealthy_pod() -> None:
    payload = {"items": [PODS["items"][0], {**PODS["items"][0], "metadata": {"name": "healthy"}}]}
    payload["items"][1] = json.loads(json.dumps(payload["items"][1]))
    payload["items"][1]["status"]["containerStatuses"][0].update(
        {"ready": True, "restartCount": 0, "state": {"running": {}}}
    )

    commands: list[list[str]] = []

    def runner(command, timeout):
        commands.append(list(command))
        if command[1:3] == ["get", "pods"]:
            return json.dumps(payload)
        if command[1:3] == ["get", "events"]:
            return json.dumps({"items": []})
        if command[1:3] == ["get", "deployment"]:
            return json.dumps({})
        return ""

    KubernetesContextCollector(runner=runner).collect("payment-api", "incidentzero-demo")
    assert any("payment-api-abc" in argument for argument in commands[1])


@pytest.mark.parametrize("value", ["UPPERCASE", "bad/name", "$(whoami)", ""])
def test_collector_rejects_unsafe_resource_names(value: str) -> None:
    collector = KubernetesContextCollector(runner=lambda *_: "")
    with pytest.raises(ValueError):
        collector.collect(value, "incidentzero-demo")
