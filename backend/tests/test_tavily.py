import asyncio
import json

import httpx
import pytest

from app.integrations.errors import IntegrationNotConfiguredError
from app.integrations.tavily import TavilyClient


def test_tavily_search_normalizes_and_deduplicates_sources() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer tvly-test"
        body = json.loads(request.content)
        assert body["search_depth"] == "basic"
        assert body["include_raw_content"] is False
        return httpx.Response(
            200,
            json={
                "query": body["query"],
                "response_time": 0.42,
                "results": [
                    {
                        "title": "Kubernetes docs",
                        "url": "https://kubernetes.io/docs/example",
                        "content": "Increase or tune the container memory limit.",
                        "score": 0.96,
                    },
                    {
                        "title": "Duplicate",
                        "url": "https://kubernetes.io/docs/example",
                        "content": "Duplicate content",
                        "score": 0.5,
                    },
                ],
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = TavilyClient(
                api_key="tvly-test",
                base_url="https://tavily.test",
                http_client=http,
            )
            return await client.search("Kubernetes OOMKilled", max_results=3)

    result = asyncio.run(run())
    assert result.query == "Kubernetes OOMKilled"
    assert len(result.sources) == 1
    assert result.sources[0].relevance == 0.96


def test_tavily_requires_api_key() -> None:
    client = TavilyClient(api_key=None, base_url="https://tavily.test")
    with pytest.raises(IntegrationNotConfiguredError):
        asyncio.run(client.search("Kubernetes OOMKilled"))
    asyncio.run(client.close())
