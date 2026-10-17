"""Isolated UI rehearsal. Every external boundary is mocked; never serve publicly."""
import asyncio
import os
from dataclasses import replace

from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from app.agents.diagnosis import DiagnosisAgent
from app.agents.remediation import RemediationAgent
from app.agents.research import ResearchAgent
from app.config.settings import settings
from app.graph.workflow import build_diagnosis_graph
from app.main import create_app
from app.models.integrations import ResearchResults, ResearchSource
from test_diagnosis import (FakeCollector, FakeCompletionClient, FakeSearchClient, oom_context,
                            research_diagnosis, final_diagnosis, valid_remediation)
from test_validation import SandboxRunner
from app.services.sandbox import SandboxVerifier

SOURCE_URL = "https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/"


async def execute(incident, run_id, emit):
    client = FakeCompletionClient([research_diagnosis(), final_diagnosis(source_url=SOURCE_URL), valid_remediation()])
    search = FakeSearchClient([ResearchResults(query="Kubernetes memory limits", sources=[ResearchSource(
        title="Kubernetes resource management (fixture source)", url=SOURCE_URL,
        content="Fixture excerpt: container memory limits constrain memory use; exceeding the configured limit can cause OOM termination.",
        relevance=.95,
    )])])
    context = oom_context()
    context.deployment.update({"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {
        "name": "payment-api", "namespace": "incidentzero-demo",
    }})
    graph = build_diagnosis_graph(FakeCollector(context), DiagnosisAgent(client), ResearchAgent(search),
                                  RemediationAgent(client), SandboxVerifier(runner=SandboxRunner()))
    state = {"incident_id": incident.id, "run_id": run_id, "incident_input": incident.incident,
             "execution_mode": "kubernetes", "timeline_events": [], "errors": []}
    emit("context.started", "MOCKED rehearsal: collecting fixture evidence.", {})
    async for chunk in graph.astream(state, stream_mode="updates"):
        for delta in chunk.values():
            for key, value in delta.items():
                state[key] = [*state.get(key, []), *value] if key in {"timeline_events", "errors"} else value
            for event in delta.get("timeline_events", []):
                stage = {"intake": "incident.received", "remediation": "remediation.generated"}.get(event.stage, event.stage)
                if "." not in stage:
                    stage += ".completed"
                emit(stage, "MOCKED rehearsal: " + event.message, jsonable_encoder(state))
        await asyncio.sleep(.1)
    return jsonable_encoder(state)


config = replace(settings, app_environment="local", execution_mode="kubernetes", runs_enabled=True,
                 demo_run_token=None, nebius_api_key="mocked-only", daily_run_limit=100)
app = create_app(database_path=os.environ["UI_TEST_DATABASE_PATH"], executor=execute, config=config)
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:3100"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.get("/__test__/reset")
def identify_fixture():
    # Read-only marker lets the live acceptance recorder refuse this fixture server.
    return {"fixture": "mocked-submission-rehearsal"}
