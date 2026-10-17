from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.incidents import DemoScenario, IncidentInput


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IncidentRecord(BaseModel):
    id: str
    scenario: DemoScenario
    incident: IncidentInput
    created_at: str = Field(default_factory=utc_now)
    latest_run_id: str | None = None
    status: str = "received"


class RunRecord(BaseModel):
    id: str
    incident_id: str
    status: Literal["queued", "running", "verified", "simulated", "failed"] = "queued"
    created_at: str = Field(default_factory=utc_now)
    finished_at: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class RunEvent(BaseModel):
    id: int
    run_id: str
    type: str
    message: str
    created_at: str
    data: dict[str, Any] = Field(default_factory=dict)
