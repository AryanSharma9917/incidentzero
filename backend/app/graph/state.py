import operator
from typing import Annotated, TypedDict

from app.models.diagnosis import Hypothesis, TimelineEvent, WorkflowStatus
from app.models.incidents import IncidentInput, NormalizedIncident
from app.models.integrations import ResearchSource
from app.models.kubernetes import KubernetesContext


class IncidentState(TypedDict, total=False):
    incident_id: str
    run_id: str
    incident_input: IncidentInput
    incident: NormalizedIncident
    cluster_context: KubernetesContext
    hypotheses: list[Hypothesis]
    research_required: bool
    research_queries: list[str]
    research_sources: list[ResearchSource]
    research_summary: str
    root_cause: str
    root_cause_confidence: float
    supporting_evidence: list[str]
    remediation_plan: str
    patch: str
    affected_resource: str
    risk: str
    validation_score: int
    validation_passed: bool
    iteration_count: int
    final_report: str
    status: WorkflowStatus
    timeline_events: Annotated[list[TimelineEvent], operator.add]
    errors: Annotated[list[str], operator.add]
