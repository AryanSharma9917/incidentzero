import asyncio
import json
from dataclasses import replace

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.intake import get_demo_incident, normalize_incident
from app.config.settings import settings, load_settings
from app.main import create_app
from app.models.incidents import DemoScenario
from app.models.remediation import RemediationCandidate
from app.services.reports import generate_report
from app.services.runs import RunManager
from app.services.simulation import SimulationController
from app.storage.sqlite import Store, DailyRunLimitError
from test_diagnosis import FakeCompletionClient, FakeSearchClient, valid_diagnosis, final_diagnosis, valid_remediation


@pytest.mark.parametrize("changes", [
    {"cors_origins": ["*"]}, {"cors_origins": ["https://example.com/path"]},
    {"app_environment": "prod"}, {"execution_mode": "unknown"}, {"daily_run_limit": 0},
    {"app_environment": "production", "cors_origins": ["http://example.com"]},
    {"app_environment": "production", "cors_origins": []},
    {"app_environment": "production", "cors_origins": ["https://example.com"], "execution_mode": "kubernetes"},
    {"app_environment": "production", "cors_origins": ["https://example.com"], "execution_mode": "simulation", "demo_run_token": "short"},
])
def test_unsafe_deployment_configuration_is_rejected(changes):
    with pytest.raises(ValueError):
        replace(settings, **changes).validate()


def test_production_defaults_pause_runs_and_boolean_config_is_strict(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("RUNS_ENABLED", raising=False)
    assert not load_settings().runs_enabled
    monkeypatch.setenv("RUNS_ENABLED", "maybe")
    with pytest.raises(ValueError, match="true or false"):
        load_settings()


@pytest.mark.parametrize("scenario", list(DemoScenario))
def test_simulator_evaluates_configuration_and_enforces_policy(scenario):
    controller = SimulationController()
    controller.prepare(scenario)
    incident = normalize_incident(get_demo_incident(scenario), "inc-test")
    context = controller.collect(incident.service, incident.namespace)
    assert not context.pods[0].containers[0].ready
    assert "SIMULATED" in context.logs
    data = json.loads(valid_remediation())
    if scenario == DemoScenario.CRASH_LOOP:
        change = "          env:\n            - name: DATABASE_HOST\n              value: database\n"
    elif scenario == DemoScenario.READINESS_FAILURE:
        change = "          readinessProbe:\n            httpGet:\n              path: /health\n              port: http\n"
    else:
        change = "          resources:\n            limits:\n              memory: 128Mi\n"
    data["patch_yaml"] = data["patch_yaml"].split("          resources:")[0] + change
    candidate = RemediationCandidate.model_validate(data)
    assert controller.validate(candidate, incident, context).passed
    assert controller.collect(incident.service, incident.namespace).pods[0].containers[0].ready
    candidate.patch_yaml += "          image: attacker/image\n"
    assert not controller.validate(candidate, incident, context).passed


def test_insufficient_simulated_memory_fix_fails_instead_of_fabricating_health():
    controller = SimulationController()
    controller.prepare(DemoScenario.OOM_KILLED)
    incident = normalize_incident(get_demo_incident("oomkilled"), "inc")
    candidate = RemediationCandidate.model_validate_json(valid_remediation().replace("128Mi", "80Mi"))
    result = controller.validate(candidate, incident, controller.collect(incident.service, incident.namespace))
    assert not result.passed
    assert result.score == 50
    assert "no rollout" in result.checks[-1].message


def test_simulation_runs_real_graph_with_mocked_model_never_claims_kubernetes_verification(tmp_path, monkeypatch, caplog):
    import app.services.runs as service
    client = FakeCompletionClient([valid_diagnosis(), final_diagnosis(), valid_remediation()])
    search = FakeSearchClient()
    async def close():
        pass
    client.close = close
    search.close = close
    monkeypatch.setattr(service, "NebiusClient", lambda **kwargs: client)
    monkeypatch.setattr(service, "TavilyClient", lambda **kwargs: search)
    monkeypatch.setattr(service, "DemoController", lambda *args: pytest.fail("Simulation must not call Kubernetes"))
    config = replace(settings, execution_mode="simulation", nebius_api_key="do-not-log-this-key")
    store = Store(str(tmp_path / "simulation.sqlite3"))
    store.initialize()
    incident = store.create_incident(DemoScenario.OOM_KILLED)
    run = store.create_run(incident.id)
    with caplog.at_level("INFO", logger="incidentzero.workflow"):
        RunManager(store, config=config).execute(incident, run.id)
    result = store.get_run(run.id)
    assert result.status == "simulated"
    assert result.finished_at
    assert result.result["status"] == "simulated"
    assert "not a Kubernetes-verified" in result.result["final_report"]
    assert "Verified in the controlled sandbox" not in result.result["final_report"]
    assert len(client.calls) == 3
    assert search.calls == []
    assert store.events(run.id)[-1].data["status"] == "simulated"
    records = [json.loads(record.message) for record in caplog.records if record.name == "incidentzero.workflow"]
    assert records
    assert {"incident_id", "run_id", "node", "event", "duration_ms", "status"}.issubset(records[-1])
    assert records[-1]["status"] == "simulated"
    assert all(record["duration_ms"] >= 0 for record in records)
    assert "do-not-log-this-key" not in caplog.text
    assert "process allocating memory" not in caplog.text
    assert store.create_run(incident.id)  # simulation is terminal and releases the lock


def test_protected_mutations_cors_readonly_history_and_runtime(tmp_path):
    secret = "test-access-code-not-a-provider-key"
    config = replace(settings, app_environment="production", execution_mode="simulation", runs_enabled=True,
                     demo_run_token=secret, cors_origins=["https://demo.example"], storage_ephemeral=True)
    app = create_app(config=config, database_path=str(tmp_path / "api.sqlite3"))
    async def check():
        async with app.router.lifespan_context(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                runtime = await client.get("/api/runtime")
                assert runtime.status_code == 200
                assert secret not in runtime.text
                assert runtime.json()["execution_mode"] == "simulation"
                assert runtime.json()["storage_ephemeral"]
                assert (await client.post("/api/incidents/demo/oomkilled")).status_code == 401
                wrong = {"X-Demo-Run-Token": "wrong"}
                assert (await client.post("/api/incidents/demo/oomkilled", headers=wrong)).status_code == 401
                headers = {"X-Demo-Run-Token": secret, "Origin": "https://demo.example"}
                response = await client.post("/api/incidents/demo/oomkilled", headers=headers)
                assert response.status_code == 201
                assert response.headers["access-control-allow-origin"] == "https://demo.example"
                incident_id = response.json()["id"]
                assert (await client.post(f"/api/incidents/{incident_id}/run")).status_code == 401
                assert (await client.get("/api/incidents")).status_code == 200
                denied = await client.get("/api/incidents", headers={"Origin": "https://untrusted.example"})
                assert "access-control-allow-origin" not in denied.headers
                preflight = await client.options("/api/incidents/demo/oomkilled", headers={
                    "Origin": "https://demo.example", "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "X-Demo-Run-Token",
                })
                assert preflight.status_code == 200
                # Quota refusal is an explicit HTTP terminal response and starts no worker.
                previous = app.state.store.create_run(incident_id)
                app.state.store.finish(previous.id, "failed", {}, "Test failure")
                app.state.config = replace(config, daily_run_limit=1)
                assert (await client.post(f"/api/incidents/{incident_id}/run", headers=headers)).status_code == 429
                assert len(app.state.store.list_runs()) == 1
                # Disabled operation remains fail-closed even with a valid code.
                app.state.config = replace(config, runs_enabled=False)
                assert (await client.post("/api/incidents/demo/oomkilled", headers=headers)).status_code == 503
                assert (await client.post(f"/api/incidents/{incident_id}/run", headers=headers)).status_code == 503
                assert (await client.get("/api/incidents")).status_code == 200
    asyncio.run(check())


def test_daily_limit_counts_failed_attempts_and_rejections_do_not_queue_work(tmp_path):
    store = Store(str(tmp_path / "budget.sqlite3"))
    store.initialize()
    incident = store.create_incident(DemoScenario.OOM_KILLED)
    run = store.create_run(incident.id, daily_limit=1)
    store.finish(run.id, "failed", {}, "Test failure")
    with pytest.raises(DailyRunLimitError):
        store.create_run(incident.id, daily_limit=1)
    assert len(store.list_runs()) == 1
