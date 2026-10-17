from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class WorkflowStatus(StrEnum):
    RECEIVED = "received"
    INVESTIGATING = "investigating"
    DIAGNOSED = "diagnosed"
    SYNTHESIZED = "synthesized"
    REMEDIATION_READY = "remediation_ready"
    FAILED = "failed"


class Hypothesis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(min_length=1)


class DiagnosisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=5)
    research_required: bool
    research_questions: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="after")
    def require_research_questions(self) -> "DiagnosisResult":
        if self.research_required and not self.research_questions:
            raise ValueError("research_questions are required when research_required is true")
        return self


class CitedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    statement: str = Field(min_length=1)
    source_type: Literal["kubernetes", "application", "external"]
    source_url: HttpUrl | None = None

    @model_validator(mode="after")
    def external_evidence_requires_url(self) -> "CitedEvidence":
        if self.source_type == "external" and self.source_url is None:
            raise ValueError("external evidence requires source_url")
        if self.source_type != "external" and self.source_url is not None:
            raise ValueError("only external evidence may include source_url")
        return self


class FinalDiagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    root_cause: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    supporting_evidence: list[CitedEvidence] = Field(min_length=1, max_length=10)
    alternatives: list[str] = Field(default_factory=list, max_length=3)
    research_summary: str = Field(min_length=1, max_length=2000)


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    stage: str = Field(min_length=1)
    status: str = Field(min_length=1)
    message: str = Field(min_length=1)
