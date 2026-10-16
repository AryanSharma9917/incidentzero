import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import app


async def _get_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/health")


def test_health_endpoint() -> None:
    response = asyncio.run(_get_health())
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "incidentzero-api",
        "version": "0.1.0",
    }
