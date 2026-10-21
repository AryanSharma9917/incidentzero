"""Make one minimal live request to each configured provider."""

import asyncio

from app.config.settings import settings
from app.integrations import NebiusClient, TavilyClient
from app.integrations.errors import IntegrationError


async def main() -> int:
    nebius = NebiusClient(
        api_key=settings.nebius_api_key,
        base_url=settings.nebius_base_url,
        model=settings.nebius_model,
        timeout_seconds=settings.nebius_timeout_seconds,
    )
    tavily = TavilyClient(
        api_key=settings.tavily_api_key,
        base_url=settings.tavily_base_url,
    )
    try:
        completion = await nebius.complete(
            [{"role": "user", "content": "Reply with exactly: IncidentZero ready"}],
            max_tokens=16,
        )
        print(f"Nebius OK: model={completion.model}, response={completion.content!r}")

        results = await tavily.search(
            "Kubernetes OOMKilled memory limit remediation", max_results=1
        )
        print(f"Tavily OK: sources={len(results.sources)}")
        return 0
    except IntegrationError as exc:
        print(f"Integration check failed: {exc}")
        return 1
    finally:
        await nebius.close()
        await tavily.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
