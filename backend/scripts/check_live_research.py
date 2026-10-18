"""Verify the live conditional research path without mutating Kubernetes."""

import asyncio

from app.agents.diagnosis import DiagnosisAgent
from app.agents.research import ResearchAgent
from app.config.settings import settings
from app.integrations import NebiusClient, TavilyClient
from app.models.incidents import NormalizedIncident, Severity
from app.models.kubernetes import KubernetesContext


async def main() -> int:
    incident = NormalizedIncident(
        incident_id="live-research-check",
        title="Intermittent upstream connection resets with incomplete cluster evidence",
        service="payment-api",
        environment="demo",
        severity=Severity.P2,
        symptoms=["Intermittent upstream connection resets", "No termination reason observed"],
        namespace="incidentzero-demo",
    )
    context = KubernetesContext(
        namespace="incidentzero-demo",
        service="payment-api",
        pods=[],
        events=[],
        deployment={},
        describe="No matching pod was available at collection time.",
        logs="upstream connection reset; cause not present in collected logs",
    )
    nebius = NebiusClient(
        api_key=settings.nebius_api_key,
        base_url=settings.nebius_base_url,
        model=settings.nebius_model,
    )
    tavily = TavilyClient(
        api_key=settings.tavily_api_key,
        base_url=settings.tavily_base_url,
    )
    try:
        diagnosis_agent = DiagnosisAgent(nebius)
        diagnosis = await diagnosis_agent.diagnose(incident, context)
        if not diagnosis.research_required:
            print("FAIL: Nemotron did not request research for deliberately incomplete evidence")
            return 1
        research = await ResearchAgent(tavily).research(diagnosis.research_questions)
        if not research:
            print("FAIL: conditional Tavily call returned no usable sources")
            return 1
        final = await diagnosis_agent.synthesize(
            incident,
            context,
            diagnosis.hypotheses,
            research,
        )
        supplied = {str(item.url) for item in research}
        cited = {
            str(item.source_url)
            for item in final.supporting_evidence
            if item.source_url is not None
        }
        if not cited.issubset(supplied):
            print("FAIL: final diagnosis cited a URL outside supplied Tavily sources")
            return 1
        print(
            "PASS: conditional live research; "
            f"questions={len(diagnosis.research_questions)}, "
            f"sources={len(research)}, cited_sources={len(cited)}"
        )
        return 0
    finally:
        await nebius.close()
        await tavily.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
