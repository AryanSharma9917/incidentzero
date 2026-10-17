import asyncio
import copy
import json

import pytest

from app.agents.diagnosis import DiagnosisAgent
from app.agents.intake import get_demo_incident, normalize_incident
from app.agents.remediation import RemediationAgent
from app.agents.research import ResearchAgent
from app.graph.workflow import build_diagnosis_graph
from app.integrations.kubernetes import KubernetesCollectionError
from app.models.remediation import RemediationCandidate
from app.models.validation import SandboxValidation
from app.services.sandbox import SandboxVerifier
from test_diagnosis import (
    FakeCollector, FakeCompletionClient, FakeSearchClient, final_diagnosis,
    oom_context, valid_diagnosis, valid_remediation,
)


class SandboxRunner:
    def __init__(self):
        self.commands = []
        self.server = "https://127.0.0.1:6443"
        self.fail_operation = None
        self.restart_count = 0
        self.health = '{"status":"ok"}'
        self.logs = "payment-api listening on :8080"
        self.owned = True
        self.current_limit = "64Mi"

    def __call__(self, command, timeout):
        self.commands.append(command)
        assert command[:4] == [
            "kubectl", "--context", "kind-incidentzero", "--request-timeout=10s"
        ]
        args = command[4:]
        if args[0] == self.fail_operation:
            raise KubernetesCollectionError("Simulated failure")
        if args[:2] == ["config", "view"]:
            return json.dumps({
                "clusters": [{"name": "kind-incidentzero", "cluster": {"server": self.server}}],
                "contexts": [{"name": "kind-incidentzero", "context": {"cluster": "kind-incidentzero"}}],
            })
        if args[:2] == ["get", "deployment"]:
            dep = copy.deepcopy(oom_context().deployment)
            dep.update({"apiVersion": "apps/v1", "kind": "Deployment"})
            dep["metadata"] = {"uid": "deployment-uid", "name": "payment-api", "namespace": "incidentzero-demo"}
            dep["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"]["memory"] = self.current_limit
            return json.dumps(dep)
        if args[0] in {"patch", "rollout"}:
            return "ok"
        if args[:2] == ["get", "replicasets"]:
            return json.dumps({"items": [{"metadata": {
                "uid": "rs-uid", "ownerReferences": [{
                    "uid": "deployment-uid", "kind": "Deployment", "controller": True,
                }],
            }}]})
        if args[:2] == ["get", "pods"]:
            return json.dumps({"items": [{
                "metadata": {"name": "payment-api-new", "ownerReferences": [{
                    "uid": "rs-uid" if self.owned else "unrelated", "kind": "ReplicaSet", "controller": True,
                }]},
                "spec": {"containers": [{"name": "payment-api"}]},
                "status": {"phase": "Running", "containerStatuses": [{
                    "name": "payment-api", "ready": True, "restartCount": self.restart_count,
                    "state": {"running": {}},
                }]},
            }]})
        if args[0] == "logs":
            return self.logs
        if args[:2] == ["get", "--raw"]:
            return self.health
        raise AssertionError(args)


def verify(runner, *, incident=None, candidate=None):
    return SandboxVerifier(runner=runner).validate(
        candidate or RemediationCandidate.model_validate_json(valid_remediation()),
        incident or normalize_incident(get_demo_incident("oomkilled"), "inc-123"),
        oom_context(),
    )


def test_sandbox_applies_fixed_operations_and_scores_health():
    runner = SandboxRunner()
    result = verify(runner)
    assert result.passed and result.score == 100
    patch = next(command for command in runner.commands if command[4] == "patch")
    assert patch[5:10] == ["deployment", "payment-api", "-n", "incidentzero-demo", "--type=strategic"]
    assert {check.name for check in result.checks} >= {"rollout", "pod-health", "recent-logs", "http-health"}


def test_production_target_never_runs_kubectl():
    runner = SandboxRunner()
    incident = normalize_incident(get_demo_incident("oomkilled"), "inc-123").model_copy(
        update={"namespace": "demo-production"}
    )
    assert not verify(runner, incident=incident).passed
    assert runner.commands == []


def test_remote_context_never_mutates():
    runner = SandboxRunner()
    runner.server = "https://production.example:6443"
    assert not verify(runner).passed
    assert len(runner.commands) == 1


def test_unsafe_candidate_never_mutates():
    runner = SandboxRunner()
    candidate = RemediationCandidate.model_validate_json(valid_remediation())
    candidate.patch_yaml = candidate.patch_yaml.replace(
        "          resources:", "          image: attacker.invalid/image\n          resources:"
    )
    assert not verify(runner, candidate=candidate).passed
    assert not any(command[4] == "patch" for command in runner.commands)


def test_live_policy_revalidation_rejects_stale_patch():
    runner = SandboxRunner()
    runner.current_limit = "256Mi"
    result = verify(runner)
    assert not result.passed and result.checks[-1].name == "patch-policy"
    assert not any(command[4] == "patch" for command in runner.commands)


@pytest.mark.parametrize("operation", ["config", "get", "patch", "rollout", "logs"])
def test_command_failures_become_named_failures(operation):
    runner = SandboxRunner()
    runner.fail_operation = operation
    result = verify(runner)
    assert not result.passed and result.score < 100
    assert not result.checks[-1].passed


@pytest.mark.parametrize("field,value", [
    ("restart_count", 1), ("health", "not-json"),
    ("health", '{"status":"error"}'), ("logs", "fatal: application crashed"), ("owned", False),
])
def test_unhealthy_evidence_cannot_pass(field, value):
    runner = SandboxRunner()
    setattr(runner, field, value)
    assert not verify(runner).passed


class FakeVerifier:
    def __init__(self, outcomes):
        self.outcomes = outcomes
        self.calls = 0

    def validate(self, *args):
        passed = self.outcomes[self.calls]
        self.calls += 1
        return SandboxValidation(
            checks=[{"name": "http-health", "passed": passed, "message": "Health evidence"}],
            score=100 if passed else 0, passed=passed,
        )


@pytest.mark.parametrize("outcomes,status", [
    ([True], "verified"), ([False, True], "verified"), ([False, False], "failed"),
])
def test_graph_has_one_bounded_retry_with_failure_evidence(outcomes, status):
    client = FakeCompletionClient([
        valid_diagnosis(), final_diagnosis(), *[valid_remediation() for _ in outcomes],
    ])
    collector = FakeCollector(oom_context())
    verifier = FakeVerifier(outcomes)
    graph = build_diagnosis_graph(
        collector, DiagnosisAgent(client), ResearchAgent(FakeSearchClient()),
        RemediationAgent(client), sandbox_verifier=verifier,
    )
    result = asyncio.run(graph.ainvoke({"incident_input": get_demo_incident("oomkilled")}))
    assert result["status"] == status
    assert result["iteration_count"] == verifier.calls == len(outcomes)
    assert len(result["validation_history"]) == len(outcomes)
    assert len(collector.calls) == len(outcomes)
    assert result["validation_passed"] == outcomes[-1]
    if len(outcomes) == 2:
        assert '"previous_validation":{"checks"' in client.calls[-1][-1]["content"]
    assert bool(result.get("errors")) == (status == "failed")


def test_retry_generation_failure_terminates_without_another_write():
    client = FakeCompletionClient([
        valid_diagnosis(), final_diagnosis(), valid_remediation(), "invalid", "invalid",
    ])
    verifier = FakeVerifier([False])
    graph = build_diagnosis_graph(
        FakeCollector(oom_context()), DiagnosisAgent(client), ResearchAgent(FakeSearchClient()),
        RemediationAgent(client), sandbox_verifier=verifier,
    )
    result = asyncio.run(graph.ainvoke({"incident_input": get_demo_incident("oomkilled")}))
    assert result["status"] == "failed"
    assert verifier.calls == 1
    assert result["errors"] == ["Remediation generation or retry evidence collection failed"]
