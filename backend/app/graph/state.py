import operator
from typing import Annotated, TypedDict

from app.models.diagnosis import (
    CitedEvidence,
    FinalDiagnosis,
    Hypothesis,
    TimelineEvent,
    WorkflowStatus,
)
from app.models.incidents import IncidentInput, NormalizedIncident
from app.models.integrations import ResearchEvidence
from app.models.kubernetes import KubernetesContext
from app.models.remediation import PatchValidation, RemediationCandidate
from app.models.validation import SandboxValidation


class IncidentState(TypedDict, total=False):
    incident_id: str
    run_id: str
    incident_input: IncidentInput
    incident: NormalizedIncident
    cluster_context: KubernetesContext
    hypotheses: list[Hypothesis]
    research_required: bool
    research_queries: list[str]
    research_sources: list[ResearchEvidence]
    research_summary: str
    root_cause: str
    root_cause_confidence: float
    supporting_evidence: list[CitedEvidence]
    alternatives: list[str]
    final_diagnosis: FinalDiagnosis
    remediation: RemediationCandidate
    candidate_validation: PatchValidation
    remediation_plan: str
    patch: str
    affected_resource: str
    risk: str
    expected_outcome: str
    validation_score: int
    validation_passed: bool
    iteration_count: int
    validation_history: list[SandboxValidation]
    final_report: str
    status: WorkflowStatus
    timeline_events: Annotated[list[TimelineEvent], operator.add]
    errors: Annotated[list[str], operator.add]
