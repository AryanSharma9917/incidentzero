import asyncio
import json

import pytest

from app.agents.diagnosis import DiagnosisAgent, StructuredDiagnosisError
from app.agents.intake import get_demo_incident, normalize_incident
from app.agents.research import ResearchAgent
from app.agents.remediation import RemediationAgent
from app.graph.workflow import build_diagnosis_graph
from app.models.diagnosis import Hypothesis, WorkflowStatus
from app.models.incidents import DemoScenario
from app.models.integrations import (
    NebiusCompletion,
    ResearchEvidence,
    ResearchResults,
    ResearchSource,
)
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


class FakeSearchClient:
    def __init__(self, results: list[ResearchResults] | None = None) -> None:
        self.results = results or []
        self.calls: list[tuple[str, int]] = []

    async def search(self, query: str, *, max_results: int = 5) -> ResearchResults:
        self.calls.append((query, max_results))
        return self.results.pop(0)


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


def research_diagnosis() -> str:
    return json.dumps(
        {
            "hypotheses": [
                {
                    "title": "Container exceeded its memory limit",
                    "confidence": 0.72,
                    "evidence": ["Last termination reason is OOMKilled"],
                }
            ],
            "research_required": True,
            "research_questions": ["Kubernetes OOMKilled exit 137 memory limit guidance"],
        }
    )


def final_diagnosis(*, source_url: str | None = None) -> str:
    evidence = [
        {
            "statement": "The container was terminated as OOMKilled with exit code 137.",
            "source_type": "kubernetes",
            "source_url": None,
        }
    ]
    if source_url:
        evidence.append(
            {
                "statement": "Kubernetes enforces container memory limits with OOM termination.",
                "source_type": "external",
                "source_url": source_url,
            }
        )
    return json.dumps(
        {
            "root_cause": "The payment-api container exceeded its 64Mi memory limit.",
            "confidence": 0.99,
            "supporting_evidence": evidence,
            "alternatives": [],
            "research_summary": (
                "One relevant external source corroborated the cluster evidence."
                if source_url
                else "External research was not required."
            ),
        }
    )


def valid_remediation() -> str:
    return json.dumps(
        {
            "summary": "Increase the payment-api container memory limit.",
            "affected_resource": {
                "api_version": "apps/v1",
                "kind": "Deployment",
                "name": "payment-api",
                "namespace": "incidentzero-demo",
            },
            "reason": "The observed OOMKilled termination shows the 64Mi limit is insufficient.",
            "risk": "low",
            "expected_outcome": "The container remains below its new memory limit.",
            "patch_yaml": (
                "apiVersion: apps/v1\n"
                "kind: Deployment\n"
                "metadata:\n"
                "  name: payment-api\n"
                "  namespace: incidentzero-demo\n"
                "spec:\n"
                "  template:\n"
                "    spec:\n"
                "      containers:\n"
                "        - name: payment-api\n"
                "          resources:\n"
                "            limits:\n"
                "              memory: 128Mi\n"
            ),
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


def test_synthesis_repairs_an_unsupported_external_citation() -> None:
    supplied_url = "https://kubernetes.io/docs/oom"
    client = FakeCompletionClient(
        [
            final_diagnosis(source_url="https://untrusted.example/claim"),
            final_diagnosis(source_url=supplied_url),
        ]
    )
    agent = DiagnosisAgent(client)
    incident = normalize_incident(get_demo_incident("oomkilled"), "inc-123")
    hypotheses = json.loads(valid_diagnosis())["hypotheses"]
    research = [
        ResearchEvidence(
            query="Kubernetes OOMKilled",
            title="Kubernetes documentation",
            url=supplied_url,
            excerpt="Memory limits can result in OOM termination.",
            relevance=0.95,
            explanation="Relevant to the observed termination.",
        )
    ]

    result = asyncio.run(
        agent.synthesize(
            incident,
            oom_context(),
            [Hypothesis.model_validate(item) for item in hypotheses],
            research,
        )
    )

    assert str(result.supporting_evidence[1].source_url) == supplied_url
    assert len(client.calls) == 2
    assert "Use only supplied source URLs" in client.calls[1][-1]["content"]


def test_graph_collects_evidence_and_returns_structured_hypotheses() -> None:
    collector = FakeCollector(oom_context())
    client = FakeCompletionClient([valid_diagnosis(), final_diagnosis(), valid_remediation()])
    search = FakeSearchClient()
    graph = build_diagnosis_graph(
        collector,
        DiagnosisAgent(client),
        ResearchAgent(search),
        RemediationAgent(client),
    )

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

    assert result["status"] == WorkflowStatus.REMEDIATION_READY
    assert result["hypotheses"][0].title == "Container exceeded its memory limit"
    assert result["research_required"] is False
    assert result["root_cause"] == "The payment-api container exceeded its 64Mi memory limit."
    assert result["candidate_validation"].passed is True
    assert search.calls == []
    assert collector.calls == [("payment-api", "incidentzero-demo")]
    assert [event.stage for event in result["timeline_events"]] == [
        "intake",
        "context",
        "diagnosis",
        "synthesis",
        "remediation",
    ]


def test_graph_researches_only_when_requested_and_cites_supplied_source() -> None:
    source_url = "https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/"
    search = FakeSearchClient(
        [
            ResearchResults(
                query="Kubernetes OOMKilled exit 137 memory limit guidance",
                sources=[
                    ResearchSource(
                        title="Resource management for pods and containers",
                        url=source_url,
                        content="Memory limits are enforced reactively with out-of-memory kills.",
                        relevance=0.97,
                    )
                ],
            )
        ]
    )
    client = FakeCompletionClient(
        [research_diagnosis(), final_diagnosis(source_url=source_url), valid_remediation()]
    )
    graph = build_diagnosis_graph(
        FakeCollector(oom_context()),
        DiagnosisAgent(client),
        ResearchAgent(search),
        RemediationAgent(client),
    )

    result = asyncio.run(
        graph.ainvoke(
            {
                "incident_input": get_demo_incident("oomkilled"),
                "timeline_events": [],
                "errors": [],
            }
        )
    )

    assert search.calls == [("Kubernetes OOMKilled exit 137 memory limit guidance", 3)]
    assert len(result["research_sources"]) == 1
    assert str(result["supporting_evidence"][1].source_url) == source_url
    assert [event.stage for event in result["timeline_events"]][-3:] == [
        "research",
        "synthesis",
        "remediation",
    ]
