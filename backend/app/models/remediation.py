from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AffectedResource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    api_version: str = Field(pattern=r"^apps/v1$")
    kind: str = Field(pattern=r"^Deployment$")
    name: str = Field(min_length=1)
    namespace: str = Field(min_length=1)


class RemediationCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    summary: str = Field(min_length=1, max_length=500)
    affected_resource: AffectedResource
    reason: str = Field(min_length=1, max_length=1000)
    risk: RiskLevel
    expected_outcome: str = Field(min_length=1, max_length=1000)
    patch_yaml: str = Field(min_length=1, max_length=8000)


class PolicyCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1)
    passed: bool
    message: str = Field(min_length=1)


class PatchValidation(BaseModel):
    checks: list[PolicyCheck] = Field(min_length=1)
    passed: bool
