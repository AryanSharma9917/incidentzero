import json
from collections.abc import Sequence
from typing import Protocol

from pydantic import ValidationError

from app.integrations.nebius import ChatMessage
from app.models.diagnosis import DiagnosisResult
from app.models.incidents import NormalizedIncident
from app.models.integrations import NebiusCompletion
from app.models.kubernetes import KubernetesContext


class CompletionClient(Protocol):
    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> NebiusCompletion: ...


class StructuredDiagnosisError(RuntimeError):
    """Raised after bounded attempts cannot produce a valid diagnosis."""


def _compact_context(context: KubernetesContext) -> dict[str, object]:
    events = [
        {
            key: event.get(key)
            for key in ("type", "reason", "message", "count", "lastTimestamp")
            if event.get(key) is not None
        }
        for event in context.events[-20:]
    ]
    deployment_spec = context.deployment.get("spec", {}).get("template", {}).get("spec", {})
    containers = [
        {
            key: container.get(key)
            for key in ("name", "image", "resources", "env", "readinessProbe", "livenessProbe")
            if container.get(key) is not None
        }
        for container in deployment_spec.get("containers", [])
    ]
    return {
        "namespace": context.namespace,
        "service": context.service,
        "pods": [pod.model_dump(mode="json") for pod in context.pods],
        "events": events,
        "deployment_containers": containers,
        "describe": context.describe[-6000:],
        "logs": context.logs[-4000:],
        "previous_logs": context.previous_logs[-4000:] if context.previous_logs else None,
    }


def _parse_diagnosis(raw: str) -> DiagnosisResult:
    candidate = raw.strip()
    if candidate.startswith("```") and candidate.endswith("```"):
        lines = candidate.splitlines()
        candidate = "\n".join(lines[1:-1]).strip()
    return DiagnosisResult.model_validate_json(candidate)


class DiagnosisAgent:
    MAX_ATTEMPTS = 2

    def __init__(self, client: CompletionClient) -> None:
        self._client = client

    async def diagnose(
        self,
        incident: NormalizedIncident,
        context: KubernetesContext,
    ) -> DiagnosisResult:
        schema = DiagnosisResult.model_json_schema()
        evidence = {
            "incident": incident.model_dump(mode="json"),
            "kubernetes": _compact_context(context),
        }
        messages: list[ChatMessage] = [
            {
                "role": "system",
                "content": (
                    "You are IncidentZero's Kubernetes incident diagnostician. Infer only from the "
                    "provided evidence. Do not invent observations. Return only one JSON object that "
                    "matches the supplied schema. Confidence must be between 0 and 1. Set "
                    "research_required when evidence is insufficient or external documentation is "
                    "needed. Rank no more than five hypotheses."
                ),
            },
            {
                "role": "user",
                "content": json.dumps({"schema": schema, "evidence": evidence}, separators=(",", ":")),
            },
        ]

        last_error: Exception | None = None
        for attempt in range(self.MAX_ATTEMPTS):
            completion = await self._client.complete(tuple(messages), temperature=0, max_tokens=1200)
            try:
                return _parse_diagnosis(completion.content)
            except (ValidationError, ValueError) as exc:
                last_error = exc
                if attempt + 1 == self.MAX_ATTEMPTS:
                    break
                messages.extend(
                    [
                        {"role": "assistant", "content": completion.content[:8000]},
                        {
                            "role": "user",
                            "content": (
                                "Repair the response. Return JSON only, with no markdown or commentary. "
                                f"Validation error: {exc}"
                            ),
                        },
                    ]
                )
        raise StructuredDiagnosisError(
            f"Nemotron did not return a valid structured diagnosis after {self.MAX_ATTEMPTS} attempts"
        ) from last_error
