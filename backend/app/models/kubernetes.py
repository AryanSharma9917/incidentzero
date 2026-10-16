from typing import Any

from pydantic import BaseModel, Field


class ContainerEvidence(BaseModel):
    name: str
    ready: bool
    restart_count: int = 0
    state: str
    termination_reason: str | None = None
    exit_code: int | None = None
    requests: dict[str, str] = Field(default_factory=dict)
    limits: dict[str, str] = Field(default_factory=dict)


class PodEvidence(BaseModel):
    name: str
    phase: str
    containers: list[ContainerEvidence]


class KubernetesContext(BaseModel):
    namespace: str
    service: str
    pods: list[PodEvidence]
    events: list[dict[str, Any]]
    deployment: dict[str, Any]
    describe: str
    logs: str
    previous_logs: str | None = None
