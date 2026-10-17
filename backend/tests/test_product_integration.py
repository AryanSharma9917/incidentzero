import asyncio
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from httpx import ASGITransport, AsyncClient

from app.integrations.errors import IntegrationNotConfiguredError, IntegrationResponseError
from app.main import create_app
from app.models.incidents import DemoScenario
from app.services.runs import LiveExecution, RunManager
from app.storage.sqlite import ActiveRunError, Store
from test_diagnosis import (
    FakeCompletionClient, FakeSearchClient, oom_context,
    valid_diagnosis, final_diagnosis, valid_remediation,
)
from test_validation import FakeVerifier


@pytest.fixture
def store(tmp_path):
    result = Store(str(tmp_path / "history.sqlite3"))
    result.initialize()
    return result


def test_persistence_terminal_transaction_and_restart_recovery(store):
    incident = store.create_incident(DemoScenario.OOM_KILLED)
    run = store.create_run(incident.id)
    store.update(run.id, {"root_cause": "partial evidence"})
    reopened = Store(store.path)
    reopened.initialize()
    recovered = reopened.get_run(run.id)
    assert recovered.status == "failed"
    assert recovered.finished_at
    assert recovered.result["root_cause"] == "partial evidence"
    assert reopened.get_incident(incident.id).status == "failed"
    assert [event.type for event in reopened.events(run.id)] == ["incident.received", "run.error", "run.completed"]
    assert reopened.events(run.id)[-1].data == {"status": "failed"}
    reopened.initialize()
    assert len(reopened.events(run.id)) == 3
    # A late callback cannot overwrite a terminal state.
    reopened.update(run.id, {})
    assert reopened.get_run(run.id).status == "failed"


def test_shared_sandbox_claim_is_atomic(store):
    incidents = [store.create_incident(DemoScenario.OOM_KILLED) for _ in range(2)]

    def claim(incident):
        try:
            return store.create_run(incident.id)
        except ActiveRunError:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(claim, incidents))
    assert sum(run is not None for run in outcomes) == 1
    run = next(run for run in outcomes if run)
    store.finish(run.id, "failed", {}, "Test failure")
    assert store.create_run(incidents[0].id).status == "queued"


def test_full_graph_persisted_via_live_adapter_with_mocked_boundaries(store, monkeypatch):
    import app.services.runs as service
    client = FakeCompletionClient([valid_diagnosis(), final_diagnosis(), valid_remediation()])
    search = FakeSearchClient()
    async def close():
        pass
    client.close = close
    search.close = close
    prepared = []
    class Controller:
        def __init__(self, verifier):
            self.verifier = FakeVerifier([True])
        def prepare(self, scenario):
            prepared.append(scenario)
        def collect(self, service, namespace):
            return oom_context()
    monkeypatch.setattr(service, "settings", replace(service.settings, nebius_api_key="test-not-live"))
    monkeypatch.setattr(service, "NebiusClient", lambda **kwargs: client)
    monkeypatch.setattr(service, "TavilyClient", lambda **kwargs: search)
    monkeypatch.setattr(service, "DemoController", Controller)
    incident = store.create_incident(DemoScenario.OOM_KILLED)
    run = store.create_run(incident.id)
    RunManager(store).execute(incident, run.id)
    result = store.get_run(run.id)
    assert result.status == "verified", result.error
    assert result.result["validation_score"] == 100
    assert "-            memory: 64Mi" in result.result["patch_diff"]
    assert "+            memory: 128Mi" in result.result["patch_diff"]
    assert "## Root cause" in result.result["final_report"]
    assert "Production impact was not measured" in result.result["final_report"]
    assert prepared == [DemoScenario.OOM_KILLED]
    assert search.calls == []
    types = [event.type for event in store.events(run.id)]
    for event in ["context.started", "context.completed", "diagnosis.started", "diagnosis.completed",
                  "remediation.generated", "validation.started", "validation.check", "validation.completed",
                  "report.generated", "run.completed"]:
        assert event in types
    assert "research.started" not in types
    assert types.index("context.started") < types.index("context.completed")
    assert types[-1] == "run.completed"


def test_failure_sanitizes_errors_and_releases_sandbox(store):
    async def broken(incident, run_id, emit):
        emit("context.started", "Collecting evidence", {"iteration_count": 0})
        raise RuntimeError("Authorization: Bearer secret-value")
    incident = store.create_incident(DemoScenario.OOM_KILLED)
    run = store.create_run(incident.id)
    RunManager(store, broken).execute(incident, run.id)
    result = store.get_run(run.id)
    assert result.status == "failed"
    assert result.result == {"iteration_count": 0}
    assert "secret-value" not in result.model_dump_json()
    assert "secret-value" not in json.dumps([e.model_dump() for e in store.events(run.id)])
    assert store.create_run(incident.id)


def test_missing_credentials_precede_any_sandbox_operation(monkeypatch):
    import app.services.runs as service
    monkeypatch.setattr(service, "settings", replace(service.settings, nebius_api_key=None))
    monkeypatch.setattr(service, "DemoController", lambda *args: pytest.fail("Must not touch sandbox"))
    from app.models.runs import IncidentRecord
    from app.agents.intake import get_demo_incident
    incident = IncidentRecord(id="inc", scenario=DemoScenario.OOM_KILLED, incident=get_demo_incident("oomkilled"))
    with pytest.raises(RuntimeError, match="Provider not configured"):
        asyncio.run(LiveExecution()(incident, "run", lambda *args: None))


def test_api_background_execution_sse_replay_errors_and_export(tmp_path):
    started = threading.Event()
    release = threading.Event()
    async def execution(incident, run_id, emit):
        started.set()
        assert release.wait(5)
        emit("diagnosis.completed", "Collected real execution output (mocked test).", {"root_cause": "Test diagnosis"})
        return {"incident_id": incident.id, "incident": incident.incident.model_dump(mode="json"),
                "status": "verified", "validation_passed": True, "root_cause": "Test diagnosis"}
    app = create_app(database_path=str(tmp_path / "api.sqlite3"), executor=execution)

    async def check():
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                assert (await client.get("/api/incidents/missing")).status_code == 404
                assert (await client.get("/api/runs/missing/stream")).status_code == 404
                assert (await client.post("/api/incidents/demo/arbitrary")).status_code == 422
                response = await client.post("/api/incidents/demo/oomkilled")
                assert response.status_code == 201
                incident = response.json()
                assert len((await client.get("/api/incidents")).json()) == 1
                assert (await client.post("/api/incidents/missing/run")).status_code == 404
                response = await client.post(f"/api/incidents/{incident['id']}/run")
                assert response.status_code == 202
                run_id = response.json()["id"]
                for _ in range(100):
                    if started.is_set():
                        break
                    await asyncio.sleep(.01)
                assert started.is_set()
                # Blocked worker does not block the API loop.
                assert (await client.get("/health")).status_code == 200
                assert (await client.post(f"/api/incidents/{incident['id']}/run")).status_code == 409
                assert (await client.get(f"/api/runs/{run_id}/report")).status_code == 409
                assert (await client.get(f"/api/runs/{run_id}/stream", headers={"Last-Event-ID": "bad"})).status_code == 400
                release.set()
                for _ in range(100):
                    run = (await client.get(f"/api/runs/{run_id}")).json()
                    if run["status"] == "verified":
                        break
                    await asyncio.sleep(.01)
                assert run["status"] == "verified"
                events = (await client.get(f"/api/runs/{run_id}/events")).json()
                response = await client.get(f"/api/runs/{run_id}/stream")
                assert response.headers["content-type"].startswith("text/event-stream")
                assert "event: run.completed" in response.text
                assert response.headers["x-accel-buffering"] == "no"
                first_id = events[0]["id"]
                replay = await client.get(f"/api/runs/{run_id}/stream", headers={"Last-Event-ID": str(first_id)})
                assert "event: incident.received" not in replay.text
                assert "event: run.completed" in replay.text
                final_id = events[-1]["id"]
                assert (await client.get(f"/api/runs/{run_id}/stream?after={final_id}")).text == ""
                report = await client.get(f"/api/runs/{run_id}/report")
                assert report.status_code == 200
                assert "attachment" in report.headers["content-disposition"]
                assert "# RCA:" in report.text
                assert len((await client.get("/api/runs")).json()) == 1
                assert (await client.get(f"/api/incidents/{incident['id']}")).json()["status"] == "verified"
                # Storage failure is explicit and sanitized.
                def unavailable():
                    raise sqlite3.OperationalError("private path and secret")
                app.state.store.list_incidents = unavailable
                response = await client.get("/api/incidents")
                assert response.status_code == 503
                assert "secret" not in response.text
    try:
        asyncio.run(check())
    finally:
        release.set()


def test_second_server_cannot_recover_an_active_owners_runs(store):
    incident = store.create_incident(DemoScenario.OOM_KILLED)
    run = store.create_run(incident.id)
    with store.lease():
        with pytest.raises(RuntimeError, match="one worker"):
            with Store(store.path).lease():
                pytest.fail("Lease should not be granted")
        assert store.get_run(run.id).status == "queued"


@pytest.mark.parametrize("error,message", [
    (TimeoutError("secret"), "execution deadline"),
    (IntegrationNotConfiguredError("secret"), "provider key is missing"),
    (IntegrationResponseError("secret"), "provider request failed"),
])
def test_known_failures_have_actionable_sanitized_messages(store, error, message):
    async def broken(*args):
        raise error
    incident = store.create_incident(DemoScenario.OOM_KILLED)
    run = store.create_run(incident.id)
    RunManager(store, broken).execute(incident, run.id)
    result = store.get_run(run.id)
    assert result.status == "failed"
    assert message in result.error
    assert "secret" not in result.error


def test_sse_storage_failure_is_explicit(tmp_path):
    app = create_app(database_path=str(tmp_path / "sse.sqlite3"))
    async def check():
        async with app.router.lifespan_context(app):
            incident = app.state.store.create_incident(DemoScenario.OOM_KILLED)
            run = app.state.store.create_run(incident.id)
            def unavailable(*args):
                raise sqlite3.OperationalError("private database secret")
            app.state.store.events = unavailable
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get(f"/api/runs/{run.id}/stream")
                assert "event: stream.error" in response.text
                assert "secret" not in response.text
    asyncio.run(check())
