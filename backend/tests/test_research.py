import asyncio

from app.agents.research import ResearchAgent
from app.models.integrations import ResearchResults, ResearchSource


class FakeSearchClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def search(self, query: str, *, max_results: int = 5) -> ResearchResults:
        self.calls.append(query)
        return ResearchResults(
            query=query,
            sources=[
                ResearchSource(
                    title="Kubernetes documentation",
                    url="https://kubernetes.io/docs/oom",
                    content=f"Compact evidence for {query}",
                    relevance=0.9,
                )
            ],
        )


def test_research_bounds_queries_and_deduplicates_sources_across_results() -> None:
    client = FakeSearchClient()
    agent = ResearchAgent(client)

    sources = asyncio.run(
        agent.research(
            [
                "  Kubernetes   OOMKilled  ",
                "kubernetes oomkilled",
                "Exit code 137",
                "Container memory limits",
                "This fourth unique query must not run",
            ]
        )
    )

    assert client.calls == [
        "Kubernetes OOMKilled",
        "Exit code 137",
        "Container memory limits",
    ]
    assert len(sources) == 1
    assert sources[0].excerpt.startswith("Compact evidence")
    assert "focused incident question" in sources[0].explanation
