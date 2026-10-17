import json

import pytest

from app.integrations.kubernetes import KubernetesCollectionError
from app.models.incidents import DemoScenario
from app.services.demo import DemoController
from app.services.sandbox import SandboxVerifier
from test_diagnosis import oom_context
from test_validation import SandboxRunner


class DemoRunner(SandboxRunner):
    def __call__(self, command, timeout):
        args = command[4:]
        if args[:2] == ["get", "pods"]:
            self.commands.append(command)
            return json.dumps({"items": [{"metadata": {"name": "previous-pod"}}]})
        if args[0] == "apply":
            self.commands.append(command)
            return "applied"
        return super().__call__(command, timeout)


def test_demo_wrong_context_never_mutates():
    runner = DemoRunner()
    runner.server = "https://production.example:6443"
    controller = DemoController(SandboxVerifier(runner=runner))
    with pytest.raises(KubernetesCollectionError, match="local Kind"):
        controller.prepare(DemoScenario.OOM_KILLED)
    assert len(runner.commands) == 1


@pytest.mark.parametrize("scenario", list(DemoScenario))
def test_demo_uses_only_fixed_paths_context_and_waits_for_new_fault_pods(scenario, monkeypatch):
    runner = DemoRunner()
    controller = DemoController(SandboxVerifier(runner=runner))
    context = oom_context()
    if scenario == DemoScenario.CRASH_LOOP:
        context.logs = "fatal: DATABASE_HOST=db-invalid"
    elif scenario == DemoScenario.READINESS_FAILURE:
        context.pods[0].containers[0].restart_count = 0
        context.events = [{"message": "HTTP probe failed: 404"}]
    old = context.model_copy(deep=True)
    old.pods[0].name = "previous-pod"
    samples = iter([old, context])
    monkeypatch.setattr(controller, "collect", lambda *args: next(samples))
    sleeps = []
    monkeypatch.setattr("app.services.demo.time.sleep", sleeps.append)
    controller.prepare(scenario)
    assert sleeps == [1]
    apply = next(command for command in runner.commands if command[4] == "apply")
    assert apply[5] == "-k"
    assert apply[6].endswith("/sandbox/incidents/" + scenario.value)
    assert len(apply) == 7
    assert runner.commands[-1][4:] == ["rollout", "restart", "deployment/payment-api", "-n", "incidentzero-demo"]


def test_missing_fault_evidence_fails_after_bounded_wait(monkeypatch):
    controller = DemoController(SandboxVerifier(runner=DemoRunner()))
    context = oom_context()
    context.pods[0].containers[0].termination_reason = None
    monkeypatch.setattr(controller, "collect", lambda *args: context)
    times = iter([0, 1, 61])
    monkeypatch.setattr("app.services.demo.time.monotonic", lambda: next(times))
    monkeypatch.setattr("app.services.demo.time.sleep", lambda _: None)
    with pytest.raises(KubernetesCollectionError, match="60 seconds"):
        controller.prepare(DemoScenario.OOM_KILLED)


def test_demo_collection_is_pinned_to_explicit_context():
    commands = []
    def unavailable(command, timeout):
        commands.append(command)
        raise KubernetesCollectionError("Simulated read failure")
    controller = DemoController(SandboxVerifier(runner=unavailable))
    with pytest.raises(KubernetesCollectionError):
        controller.collect("payment-api", "incidentzero-demo")
    assert commands[0][:4] == ["kubectl", "--context", "kind-incidentzero", "--request-timeout=10s"]
