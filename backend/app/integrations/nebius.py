from collections.abc import Sequence
from typing import Any, Literal, TypedDict

import httpx
from pydantic import ValidationError

from app.integrations.errors import (
    IntegrationNotConfiguredError,
    IntegrationResponseError,
)
from app.models.integrations import NebiusCompletion, NebiusUsage


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class NebiusClient:
    """Minimal async client for Nebius Token Factory's chat-completions API."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        model: str,
        timeout_seconds: float = 30,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.1,
        max_tokens: int = 512,
    ) -> NebiusCompletion:
        if not self._api_key:
            raise IntegrationNotConfiguredError("NEBIUS_API_KEY is not configured")
        if not messages:
            raise ValueError("At least one chat message is required")

        try:
            response = await self._http.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": list(messages),
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            return self._parse_response(response.json())
        except httpx.RequestError as exc:
            raise IntegrationResponseError("Nebius request failed due to a network error") from exc
        except httpx.HTTPStatusError as exc:
            raise IntegrationResponseError(
                f"Nebius returned HTTP {exc.response.status_code}"
            ) from exc
        except (ValueError, ValidationError, KeyError, IndexError, TypeError) as exc:
            raise IntegrationResponseError("Nebius returned a malformed response") from exc

    @staticmethod
    def _parse_response(payload: dict[str, Any]) -> NebiusCompletion:
        choice = payload["choices"][0]
        content = choice["message"]["content"]
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Completion content is empty")

        usage = payload.get("usage") or {}
        return NebiusCompletion(
            content=content,
            model=payload["model"],
            finish_reason=choice.get("finish_reason"),
            usage=NebiusUsage.model_validate(usage),
        )
