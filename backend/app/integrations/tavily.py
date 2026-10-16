from typing import Any

import httpx
from pydantic import ValidationError

from app.integrations.errors import (
    IntegrationNotConfiguredError,
    IntegrationResponseError,
)
from app.models.integrations import ResearchResults, ResearchSource


class TavilyClient:
    """Async Tavily Search client returning compact, normalized sources."""

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        timeout_seconds: float = 20,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout_seconds)

    async def close(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def search(self, query: str, *, max_results: int = 5) -> ResearchResults:
        if not self._api_key:
            raise IntegrationNotConfiguredError("TAVILY_API_KEY is not configured")
        query = query.strip()
        if not query:
            raise ValueError("Search query cannot be empty")
        if not 1 <= max_results <= 10:
            raise ValueError("max_results must be between 1 and 10")

        try:
            response = await self._http.post(
                f"{self._base_url}/search",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "topic": "general",
                    "include_answer": False,
                    "include_raw_content": False,
                    "include_images": False,
                    "safe_search": True,
                },
            )
            response.raise_for_status()
            return self._normalize(response.json(), query)
        except httpx.RequestError as exc:
            raise IntegrationResponseError("Tavily request failed due to a network error") from exc
        except httpx.HTTPStatusError as exc:
            raise IntegrationResponseError(
                f"Tavily returned HTTP {exc.response.status_code}"
            ) from exc
        except (ValueError, ValidationError, KeyError, TypeError) as exc:
            raise IntegrationResponseError("Tavily returned a malformed response") from exc

    @staticmethod
    def _normalize(payload: dict[str, Any], fallback_query: str) -> ResearchResults:
        seen_urls: set[str] = set()
        sources: list[ResearchSource] = []
        for result in payload["results"]:
            url = str(result["url"])
            if url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(
                ResearchSource(
                    title=result.get("title") or url,
                    url=url,
                    content=(result.get("content") or "")[:1000],
                    relevance=result.get("score", 0),
                )
            )

        return ResearchResults(
            query=payload.get("query") or fallback_query,
            sources=sources,
            response_time=payload.get("response_time"),
        )
