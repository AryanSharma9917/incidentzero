import asyncio
import json

import httpx
import pytest

from app.integrations.errors import (
    IntegrationNotConfiguredError,
    IntegrationResponseError,
)
from app.integrations.nebius import NebiusClient


def test_nebius_completion_parses_structured_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "nvidia/test-nemotron"
        return httpx.Response(
            200,
            json={
                "model": "nvidia/test-nemotron",
                "choices": [
                    {
                        "message": {"role": "assistant", "content": "IncidentZero ready"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 7,
                    "completion_tokens": 3,
                    "total_tokens": 10,
                },
            },
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            client = NebiusClient(
                api_key="test-key",
                base_url="https://nebius.test/v1",
                model="nvidia/test-nemotron",
                http_client=http,
            )
            return await client.complete([{"role": "user", "content": "status"}])

    result = asyncio.run(run())
    assert result.content == "IncidentZero ready"
    assert result.usage.total_tokens == 10


def test_nebius_requires_api_key() -> None:
    client = NebiusClient(
        api_key=None,
        base_url="https://nebius.test/v1",
        model="nvidia/test-nemotron",
    )
    with pytest.raises(IntegrationNotConfiguredError):
        asyncio.run(client.complete([{"role": "user", "content": "status"}]))
    asyncio.run(client.close())


def test_nebius_rejects_malformed_response() -> None:
    async def run():
        transport = httpx.MockTransport(lambda _: httpx.Response(200, json={"choices": []}))
        async with httpx.AsyncClient(transport=transport) as http:
            client = NebiusClient(
                api_key="test-key",
                base_url="https://nebius.test/v1",
                model="nvidia/test-nemotron",
                http_client=http,
            )
            await client.complete([{"role": "user", "content": "status"}])

    with pytest.raises(IntegrationResponseError, match="malformed"):
        asyncio.run(run())
