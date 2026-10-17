import asyncio
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.diagnosis import DiagnosisAgent
from app.agents.intake import normalize_incident
from app.agents.research import ResearchAgent
from app.agents.remediation import RemediationAgent, RemediationGenerationError
from app.graph.state import IncidentState
from app.integrations.errors import IntegrationError
from app.integrations.kubernetes import KubernetesCollectionError, KubernetesContextCollector
from app.models.diagnosis import TimelineEvent, WorkflowStatus
from app.services.sandbox import SandboxVerifier

MAX_REMEDIATION_ATTEMPTS = 2


def build_diagnosis_graph(
    collector: KubernetesContextCollector,
    diagnosis_agent: DiagnosisAgent,
    research_agent: ResearchAgent,
    remediation_agent: RemediationAgent,
    sandbox_verifier: SandboxVerifier | None = None,
):
    """Compile planning, with sandbox writes only when an explicit verifier is supplied."""

    async def intake(state: IncidentState) -> IncidentState:
        incident_id = state.get("incident_id") or str(uuid4())
        run_id = state.get("run_id") or str(uuid4())
        incident = normalize_incident(state["incident_input"], incident_id)
        return {
            "incident_id": incident_id,
            "run_id": run_id,
            "incident": incident,
            "iteration_count": 0,
            "validation_history": [],
            "status": WorkflowStatus.INVESTIGATING,
            "timeline_events": [
                TimelineEvent(stage="intake", status="complete", message="Incident normalized")
            ],
        }

    async def collect_context(state: IncidentState) -> IncidentState:
        incident = state["incident"]
        context = collector.collect(incident.service, incident.namespace)
        return {
            "cluster_context": context,
            "timeline_events": [
                TimelineEvent(
                    stage="context",
                    status="complete",
                    message=f"Collected evidence from {len(context.pods)} pod(s)",
                )
            ],
        }

    async def diagnose(state: IncidentState) -> IncidentState:
        result = await diagnosis_agent.diagnose(state["incident"], state["cluster_context"])
        return {
            "hypotheses": result.hypotheses,
            "research_required": result.research_required,
            "research_queries": result.research_questions,
            "status": WorkflowStatus.DIAGNOSED,
            "timeline_events": [
                TimelineEvent(
                    stage="diagnosis",
                    status="complete",
                    message=f"Generated {len(result.hypotheses)} evidence-backed hypothesis(es)",
                )
            ],
        }

    async def research_route(state: IncidentState) -> str:
        return "research" if state["research_required"] else "synthesize"

    async def research(state: IncidentState) -> IncidentState:
        sources = await research_agent.research(state["research_queries"])
        return {
            "research_sources": sources,
            "timeline_events": [
                TimelineEvent(
                    stage="research",
                    status="complete",
                    message=f"Collected {len(sources)} unique source(s)",
                )
            ],
        }

    async def synthesize(state: IncidentState) -> IncidentState:
        sources = state.get("research_sources", [])
        result = await diagnosis_agent.synthesize(
            state["incident"],
            state["cluster_context"],
            state["hypotheses"],
            sources,
        )
        return {
            "final_diagnosis": result,
            "root_cause": result.root_cause,
            "root_cause_confidence": result.confidence,
            "supporting_evidence": result.supporting_evidence,
            "alternatives": result.alternatives,
            "research_summary": result.research_summary,
            "status": WorkflowStatus.SYNTHESIZED,
            "timeline_events": [
                TimelineEvent(
                    stage="synthesis",
                    status="complete",
                    message="Produced final evidence-grounded diagnosis",
                )
            ],
        }

    async def remediate(state: IncidentState) -> IncidentState:
        history = state.get("validation_history", [])
        context = state["cluster_context"]
        if history:
            context = await asyncio.to_thread(
                collector.collect, state["incident"].service, state["incident"].namespace
            )
        candidate, validation = await remediation_agent.generate(
            state["incident"],
            context,
            state["final_diagnosis"],
            **({"previous_validation": history[-1]} if history else {}),
        )
        target = candidate.affected_resource
        return {
            "remediation": candidate,
            "cluster_context": context,
            "iteration_count": state.get("iteration_count", 0) + 1,
            "candidate_validation": validation,
            "remediation_plan": candidate.summary,
            "patch": candidate.patch_yaml,
            "affected_resource": (
                f"{target.api_version}:{target.kind}:{target.namespace}/{target.name}"
            ),
            "risk": candidate.risk.value,
            "expected_outcome": candidate.expected_outcome,
            "status": WorkflowStatus.REMEDIATION_READY,
            "timeline_events": [
                TimelineEvent(
                    stage="remediation",
                    status="complete",
                    message="Generated and policy-validated a reviewable patch candidate",
                )
            ],
        }

    async def validate(state: IncidentState) -> IncidentState:
        assert sandbox_verifier is not None
        result = await asyncio.to_thread(
            sandbox_verifier.validate,
            state["remediation"], state["incident"], state["cluster_context"],
        )
        exhausted = state["iteration_count"] >= MAX_REMEDIATION_ATTEMPTS
        return {
            "validation_history": [*state.get("validation_history", []), result],
            "validation_score": result.score,
            "validation_passed": result.passed,
            "status": (
                WorkflowStatus.VERIFIED if result.passed
                else WorkflowStatus.FAILED if exhausted else WorkflowStatus.RETRYING
            ),
            "errors": ["Sandbox validation failed after two attempts"]
            if not result.passed and exhausted else [],
            "timeline_events": [
                TimelineEvent(stage="validation.started", status="started",
                              message=f"Validation attempt {state['iteration_count']}"),
                *[TimelineEvent(stage="validation.check", status="pass" if c.passed else "fail",
                                message=f"{c.name}: {c.message}") for c in result.checks],
                TimelineEvent(
                    stage="validation.completed" if result.passed else "validation.failed",
                    status="pass" if result.passed else "fail",
                    message=f"Attempt {state['iteration_count']}: score {result.score}/100",
                ),
            ],
        }

    async def guarded_remediate(state: IncidentState) -> IncidentState:
        try:
            return await remediate(state)
        except (RemediationGenerationError, KubernetesCollectionError, IntegrationError, ValueError):
            if sandbox_verifier is None:
                raise
            return {
                "status": WorkflowStatus.FAILED,
                "errors": ["Remediation generation or retry evidence collection failed"],
                "timeline_events": [TimelineEvent(
                    stage="remediation.failed", status="failed",
                    message="Cannot safely generate another sandbox candidate.",
                )],
            }

    def validation_route(state: IncidentState) -> str:
        if state["validation_passed"] or state["iteration_count"] >= MAX_REMEDIATION_ATTEMPTS:
            return "end"
        return "retry"

    graph = StateGraph(IncidentState)
    graph.add_node("intake", intake)
    graph.add_node("collect_kubernetes_context", collect_context)
    graph.add_node("diagnose_with_nemotron", diagnose)
    graph.add_node("research_with_tavily", research)
    graph.add_node("synthesize_diagnosis", synthesize)
    graph.add_node("generate_remediation", guarded_remediate)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "collect_kubernetes_context")
    graph.add_edge("collect_kubernetes_context", "diagnose_with_nemotron")
    graph.add_conditional_edges(
        "diagnose_with_nemotron",
        research_route,
        {"research": "research_with_tavily", "synthesize": "synthesize_diagnosis"},
    )
    graph.add_edge("research_with_tavily", "synthesize_diagnosis")
    graph.add_edge("synthesize_diagnosis", "generate_remediation")
    if sandbox_verifier is None:
        graph.add_edge("generate_remediation", END)
    else:
        graph.add_node("validate_sandbox", validate)
        graph.add_conditional_edges(
            "generate_remediation",
            lambda state: "end" if state["status"] == WorkflowStatus.FAILED else "validate",
            {"end": END, "validate": "validate_sandbox"},
        )
        graph.add_conditional_edges(
            "validate_sandbox", validation_route,
            {"end": END, "retry": "generate_remediation"},
        )
    return graph.compile()
