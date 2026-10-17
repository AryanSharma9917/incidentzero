"""Test-only ASGI server: mocked reasoning/Kubernetes; never imports live execution keys."""
import asyncio
import json
import os

from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware

from app.agents.intake import normalize_incident
from app.main import create_app
from test_diagnosis import oom_context, final_diagnosis, valid_remediation


async def execute(incident, run_id, emit):
    emit("context.started", "Collecting mocked browser-test evidence.", {})
    await asyncio.sleep(.2)
    if incident.scenario == "crashloop":
        raise RuntimeError("Test-only upstream failure: secret-token-must-not-leak")
    context = oom_context()
    context.deployment.update({"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {
        "name": "payment-api", "namespace": "incidentzero-demo",
    }})
    state = jsonable_encoder({
        "incident_id": incident.id, "run_id": run_id,
        "incident": normalize_incident(incident.incident, incident.id),
        "cluster_context": context, "final_diagnosis": json.loads(final_diagnosis()),
        "root_cause": json.loads(final_diagnosis())["root_cause"],
        "root_cause_confidence": .99,
        "supporting_evidence": json.loads(final_diagnosis())["supporting_evidence"],
        "research_summary": "External research was not required (mocked browser test).",
        "research_sources": [], "patch": json.loads(valid_remediation())["patch_yaml"],
        "remediation_plan": "Increase the payment-api memory limit (mocked browser test).",
        "risk": "low", "expected_outcome": "Healthy replacement pod",
        "iteration_count": 1, "timeline_events": [],
    })
    emit("context.completed", "Mocked evidence collected.", state)
    emit("diagnosis.completed", "Mocked diagnosis ready.", state)
    await asyncio.sleep(.2)
    emit("validation.started", "Checking mocked sandbox result.", state)
    state.update({"status": "verified", "validation_passed": True, "validation_score": 100,
                  "validation_history": [{"score": 100, "passed": True, "checks": [
                      {"name": "http-health", "passed": True, "message": "Mocked /health returned status ok."},
                  ]}]})
    emit("validation.completed", "Mocked sandbox result passed.", state)
    return state


app = create_app(database_path=os.environ["UI_TEST_DATABASE_PATH"], executor=execute)

# The test server is isolated from developer CORS/credentials and binds only to loopback.
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:3100"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])
