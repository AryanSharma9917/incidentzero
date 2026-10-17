from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.agents.diagnosis import DiagnosisAgent
from app.agents.intake import normalize_incident
from app.graph.state import IncidentState
from app.integrations.kubernetes import KubernetesContextCollector
from app.models.diagnosis import TimelineEvent, WorkflowStatus


def build_diagnosis_graph(
    collector: KubernetesContextCollector,
    diagnosis_agent: DiagnosisAgent,
):
    """Compile the evidence-to-hypotheses workflow; it never mutates the cluster."""

    async def intake(state: IncidentState) -> IncidentState:
        incident_id = state.get("incident_id") or str(uuid4())
        run_id = state.get("run_id") or str(uuid4())
        incident = normalize_incident(state["incident_input"], incident_id)
        return {
            "incident_id": incident_id,
            "run_id": run_id,
            "incident": incident,
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

    graph = StateGraph(IncidentState)
    graph.add_node("intake", intake)
    graph.add_node("collect_kubernetes_context", collect_context)
    graph.add_node("diagnose_with_nemotron", diagnose)
    graph.add_edge(START, "intake")
    graph.add_edge("intake", "collect_kubernetes_context")
    graph.add_edge("collect_kubernetes_context", "diagnose_with_nemotron")
    graph.add_edge("diagnose_with_nemotron", END)
    return graph.compile()
