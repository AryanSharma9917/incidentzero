import asyncio
import json

import pytest
import yaml

from app.agents.intake import get_demo_incident, normalize_incident
from app.agents.remediation import RemediationAgent
from app.models.diagnosis import FinalDiagnosis
from app.models.integrations import NebiusCompletion
from app.models.kubernetes import KubernetesContext
from app.models.remediation import RemediationCandidate
from app.services.remediation import RemediationPolicyValidator


class FakeCompletionClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = []

    async def complete(self, messages, *, temperature=0.1, max_tokens=512):
        self.calls.append(messages)
        return NebiusCompletion(content=self.responses.pop(0), model="nemotron-test")


def deployment_with(container_fields: dict) -> dict:
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "payment-api", "namespace": "incidentzero-demo"},
        "spec": {
            "template": {
                "spec": {"containers": [{"name": "payment-api", **container_fields}]}
            }
        },
    }


def context_with(container_fields: dict) -> KubernetesContext:
    return KubernetesContext(
        namespace="incidentzero-demo",
        service="payment-api",
        pods=[],
        events=[],
        deployment=deployment_with(container_fields),
        describe="",
        logs="",
    )


def candidate(patch_fields: dict) -> RemediationCandidate:
    patch = deployment_with(patch_fields)
    return RemediationCandidate(
        summary="Apply one bounded configuration correction.",
        affected_resource={
            "api_version": "apps/v1",
            "kind": "Deployment",
            "name": "payment-api",
            "namespace": "incidentzero-demo",
        },
        reason="The proposed field directly addresses the diagnosed configuration fault.",
        risk="low",
        expected_outcome="The replacement pod becomes stable and ready.",
        patch_yaml=yaml.safe_dump(patch, sort_keys=False),
    )


@pytest.mark.parametrize(
    ("scenario", "current_fields", "patch_fields"),
    [
        (
            "oomkilled",
            {"resources": {"limits": {"memory": "64Mi"}}},
            {"resources": {"limits": {"memory": "128Mi"}}},
        ),
        (
            "crashloop",
            {"env": [{"name": "DATABASE_HOST", "value": "db-invalid"}]},
            {"env": [{"name": "DATABASE_HOST", "value": "database"}]},
        ),
        (
            "readiness",
            {"readinessProbe": {"httpGet": {"path": "/healthz", "port": "http"}}},
            {"readinessProbe": {"httpGet": {"path": "/health", "port": "http"}}},
        ),
    ],
)
def test_policy_accepts_scenario_appropriate_patch(
    scenario: str,
    current_fields: dict,
    patch_fields: dict,
) -> None:
    incident = normalize_incident(get_demo_incident(scenario), f"inc-{scenario}")

    validation = RemediationPolicyValidator().validate(
        candidate(patch_fields),
        incident,
        context_with(current_fields),
    )

    assert validation.passed is True
    assert all(check.passed for check in validation.checks)


def test_policy_rejects_image_changes() -> None:
    incident = normalize_incident(get_demo_incident("oomkilled"), "inc-oom")
    validation = RemediationPolicyValidator().validate(
        candidate({"image": "attacker.example/replacement:latest"}),
        incident,
        context_with({"resources": {"limits": {"memory": "64Mi"}}}),
    )

    assert validation.passed is False
    assert any(check.name == "container-allowlist" and not check.passed for check in validation.checks)


@pytest.mark.parametrize(
    "patch_yaml",
    [
        "apiVersion: apps/v1\napiVersion: apps/v2\nkind: Deployment\n",
        "apiVersion: apps/v1\nkind: Deployment\n---\napiVersion: apps/v1\nkind: Deployment\n",
    ],
)
def test_policy_rejects_duplicate_keys_and_multiple_documents(patch_yaml: str) -> None:
    incident = normalize_incident(get_demo_incident("oomkilled"), "inc-oom")
    malformed = candidate({"resources": {"limits": {"memory": "128Mi"}}}).model_copy(
        update={"patch_yaml": patch_yaml}
    )

    validation = RemediationPolicyValidator().validate(
        malformed,
        incident,
        context_with({"resources": {"limits": {"memory": "64Mi"}}}),
    )

    assert validation.passed is False
    assert validation.checks[1].name == "yaml-safe-load"
    assert validation.checks[1].passed is False


def test_agent_repairs_policy_rejected_candidate() -> None:
    unsafe = candidate({"image": "example.invalid/replacement:latest"}).model_dump(mode="json")
    safe = candidate({"resources": {"limits": {"memory": "128Mi"}}}).model_dump(mode="json")
    client = FakeCompletionClient([json.dumps(unsafe), json.dumps(safe)])
    diagnosis = FinalDiagnosis(
        root_cause="The container exceeded its 64Mi memory limit.",
        confidence=0.99,
        supporting_evidence=[
            {
                "statement": "The previous container termination reason was OOMKilled.",
                "source_type": "kubernetes",
            }
        ],
        research_summary="External research was not required.",
    )
    incident = normalize_incident(get_demo_incident("oomkilled"), "inc-oom")

    result, validation = asyncio.run(
        RemediationAgent(client).generate(
            incident,
            context_with({"resources": {"limits": {"memory": "64Mi"}}}),
            diagnosis,
        )
    )

    assert validation.passed is True
    assert "128Mi" in result.patch_yaml
    assert len(client.calls) == 2
    assert "safety policy" in client.calls[1][-1]["content"]
    system_prompt = client.calls[0][0]["content"]
    assert "metadata must contain only name and namespace" in system_prompt
    assert "never copy CPU fields" in system_prompt
