from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorkflowStatus(StrEnum):
    RECEIVED = "received"
    INVESTIGATING = "investigating"
    DIAGNOSED = "diagnosed"
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


class TimelineEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    stage: str = Field(min_length=1)
    status: str = Field(min_length=1)
    message: str = Field(min_length=1)
