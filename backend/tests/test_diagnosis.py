import asyncio
import json

import pytest

from app.agents.diagnosis import DiagnosisAgent, StructuredDiagnosisError
from app.agents.intake import get_demo_incident, normalize_incident
from app.graph.workflow import build_diagnosis_graph
from app.models.diagnosis import WorkflowStatus
from app.models.incidents import DemoScenario
from app.models.integrations import NebiusCompletion
from app.models.kubernetes import ContainerEvidence, KubernetesContext, PodEvidence


class FakeCompletionClient:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = []

    async def complete(self, messages, *, temperature=0.1, max_tokens=512):
        self.calls.append(messages)
        return NebiusCompletion(content=self.responses.pop(0), model="nemotron-test")


class FakeCollector:
    def __init__(self, context: KubernetesContext) -> None:
        self.context = context
        self.calls: list[tuple[str, str]] = []

    def collect(self, service: str, namespace: str) -> KubernetesContext:
        self.calls.append((service, namespace))
        return self.context


def oom_context() -> KubernetesContext:
    return KubernetesContext(
        namespace="incidentzero-demo",
        service="payment-api",
        pods=[
            PodEvidence(
                name="payment-api-abc",
                phase="Running",
                containers=[
                    ContainerEvidence(
                        name="payment-api",
                        ready=False,
                        restart_count=4,
                        state="running",
                        termination_reason="OOMKilled",
                        exit_code=137,
                        requests={"memory": "32Mi"},
                        limits={"memory": "64Mi"},
                    )
                ],
            )
        ],
        events=[{"type": "Warning", "reason": "BackOff", "message": "Back-off restarting"}],
        deployment={
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": "payment-api",
                                "image": "incidentzero/demo:latest",
                                "resources": {"limits": {"memory": "64Mi"}},
                            }
                        ]
                    }
                }
            }
        },
        describe="Last State: Terminated; Reason: OOMKilled; Exit Code: 137",
        logs="process allocating memory",
        previous_logs="killed",
    )


def valid_diagnosis() -> str:
    return json.dumps(
        {
            "hypotheses": [
                {
                    "title": "Container exceeded its memory limit",
                    "confidence": 0.98,
                    "evidence": [
                        "Last termination reason is OOMKilled",
                        "Exit code is 137",
                        "Container memory limit is 64Mi",
                    ],
                }
            ],
            "research_required": False,
            "research_questions": [],
        }
    )


def test_demo_intake_normalizes_without_exposing_scenario_label() -> None:
    raw = get_demo_incident(DemoScenario.OOM_KILLED)
    normalized = normalize_incident(raw, "inc-123")

    assert normalized.incident_id == "inc-123"
    assert normalized.service == "payment-api"
    assert "scenario" not in normalized.model_dump()


def test_agent_repairs_one_malformed_response() -> None:
    client = FakeCompletionClient(["not-json", f"```json\n{valid_diagnosis()}\n```"])
    agent = DiagnosisAgent(client)
    incident = normalize_incident(get_demo_incident("oomkilled"), "inc-123")

    result = asyncio.run(agent.diagnose(incident, oom_context()))

    assert result.hypotheses[0].confidence == 0.98
    assert len(client.calls) == 2
    assert "Repair the response" in client.calls[1][-1]["content"]
    first_prompt = client.calls[0][-1]["content"]
    assert "OOMKilled" in first_prompt
    assert '"scenario"' not in first_prompt


def test_agent_stops_after_bounded_invalid_responses() -> None:
    client = FakeCompletionClient(["not-json", '{"hypotheses": []}'])
    agent = DiagnosisAgent(client)
    incident = normalize_incident(get_demo_incident("oomkilled"), "inc-123")

    with pytest.raises(StructuredDiagnosisError, match="after 2 attempts"):
        asyncio.run(agent.diagnose(incident, oom_context()))
    assert len(client.calls) == 2


def test_graph_collects_evidence_and_returns_structured_hypotheses() -> None:
    collector = FakeCollector(oom_context())
    client = FakeCompletionClient([valid_diagnosis()])
    graph = build_diagnosis_graph(collector, DiagnosisAgent(client))

    result = asyncio.run(
        graph.ainvoke(
            {
                "incident_id": "inc-123",
                "run_id": "run-123",
                "incident_input": get_demo_incident("oomkilled"),
                "timeline_events": [],
                "errors": [],
            }
        )
    )

    assert result["status"] == WorkflowStatus.DIAGNOSED
    assert result["hypotheses"][0].title == "Container exceeded its memory limit"
    assert result["research_required"] is False
    assert collector.calls == [("payment-api", "incidentzero-demo")]
    assert [event.stage for event in result["timeline_events"]] == [
        "intake",
        "context",
        "diagnosis",
    ]
