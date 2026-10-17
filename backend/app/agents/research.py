from typing import Protocol

from app.models.integrations import ResearchEvidence, ResearchResults


class SearchClient(Protocol):
    async def search(self, query: str, *, max_results: int = 5) -> ResearchResults: ...


class ResearchAgent:
    MAX_QUERIES = 3
    RESULTS_PER_QUERY = 3

    def __init__(self, client: SearchClient) -> None:
        self._client = client

    async def research(self, questions: list[str]) -> list[ResearchEvidence]:
        queries: list[str] = []
        seen_queries: set[str] = set()
        for question in questions:
            query = " ".join(question.split())
            key = query.casefold()
            if query and key not in seen_queries:
                seen_queries.add(key)
                queries.append(query)
            if len(queries) == self.MAX_QUERIES:
                break

        evidence: list[ResearchEvidence] = []
        seen_urls: set[str] = set()
        for query in queries:
            results = await self._client.search(query, max_results=self.RESULTS_PER_QUERY)
            for source in results.sources:
                url = str(source.url)
                if url in seen_urls or not source.content.strip():
                    continue
                seen_urls.add(url)
                evidence.append(
                    ResearchEvidence(
                        query=query,
                        title=source.title,
                        url=source.url,
                        excerpt=source.content,
                        relevance=source.relevance,
                        explanation=f"Returned for the focused incident question: {query}",
                    )
                )
        return evidence
