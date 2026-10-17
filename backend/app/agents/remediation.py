import json

from pydantic import ValidationError

from app.agents.diagnosis import CompletionClient
from app.integrations.nebius import ChatMessage
from app.models.diagnosis import FinalDiagnosis
from app.models.incidents import NormalizedIncident
from app.models.kubernetes import KubernetesContext
from app.models.remediation import PatchValidation, RemediationCandidate
from app.models.validation import SandboxValidation
from app.services.remediation import RemediationPolicyValidator


class RemediationGenerationError(RuntimeError):
    """Raised when bounded generation cannot produce a policy-safe patch."""


class RemediationAgent:
    MAX_ATTEMPTS = 2

    def __init__(
        self,
        client: CompletionClient,
        validator: RemediationPolicyValidator | None = None,
    ) -> None:
        self._client = client
        self._validator = validator or RemediationPolicyValidator()

    async def generate(
        self,
        incident: NormalizedIncident,
        context: KubernetesContext,
        diagnosis: FinalDiagnosis,
        previous_validation: SandboxValidation | None = None,
    ) -> tuple[RemediationCandidate, PatchValidation]:
        deployment = context.deployment
        payload = {
            "schema": RemediationCandidate.model_json_schema(),
            "incident": incident.model_dump(mode="json"),
            "final_diagnosis": diagnosis.model_dump(mode="json"),
            "current_deployment": deployment,
            "previous_validation": (
                previous_validation.model_dump(mode="json") if previous_validation else None
            ),
        }
        messages: list[ChatMessage] = [
            {
                "role": "system",
                "content": (
                    "You are IncidentZero's Kubernetes remediation planner. Return only one JSON "
                    "object matching the schema. patch_yaml must be a minimal apps/v1 Deployment "
                    "strategic-merge patch for the supplied service and namespace. Change exactly "
                    "one container domain: memory requests/limits, DATABASE_HOST value, or readiness "
                    "httpGet path/port. Never change images, commands, replicas, security settings, "
                    "secrets, labels, selectors, service accounts, volumes, or namespaces. Do not "
                    "include kubectl, shell commands, or instructions to apply the patch."
                ),
            },
            {"role": "user", "content": json.dumps(payload, separators=(",", ":"))},
        ]

        last_error: Exception | None = None
        for attempt in range(self.MAX_ATTEMPTS):
            completion = await self._client.complete(tuple(messages), temperature=0, max_tokens=1600)
            try:
                candidate = RemediationCandidate.model_validate_json(completion.content.strip())
                validation = self._validator.validate(candidate, incident, context)
                if not validation.passed:
                    failures = [item.message for item in validation.checks if not item.passed]
                    raise ValueError("; ".join(failures))
                return candidate, validation
            except (ValidationError, ValueError) as exc:
                last_error = exc
                if attempt + 1 == self.MAX_ATTEMPTS:
                    break
                messages.extend(
                    [
                        {"role": "assistant", "content": completion.content[:10000]},
                        {
                            "role": "user",
                            "content": (
                                "Repair the candidate to satisfy the schema and safety policy. Return "
                                f"JSON only. Validation error: {exc}"
                            ),
                        },
                    ]
                )
        raise RemediationGenerationError(
            f"Nemotron did not return a safe remediation after {self.MAX_ATTEMPTS} attempts"
        ) from last_error
