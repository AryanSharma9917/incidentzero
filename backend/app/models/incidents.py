from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class IncidentInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1)
    service: str = Field(min_length=1)
    environment: str = Field(min_length=1)
    severity: Severity
    symptoms: list[str] = Field(min_length=1)
    namespace: str = "incidentzero-demo"


class NormalizedIncident(IncidentInput):
    incident_id: str = Field(min_length=1)


class DemoScenario(StrEnum):
    OOM_KILLED = "oomkilled"
    CRASH_LOOP = "crashloop"
    READINESS_FAILURE = "readiness"
