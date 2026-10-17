from pydantic import BaseModel, ConfigDict, Field

from app.models.remediation import PolicyCheck


class SandboxValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    checks: list[PolicyCheck] = Field(min_length=1)
    score: int = Field(ge=0, le=100)
    passed: bool
