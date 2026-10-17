from scripts.record_golden_runs import assess_run
from app.models.runs import RunRecord


def accepted_run():
    return RunRecord(id="run", incident_id="incident", status="verified", finished_at="2026-10-17T12:00:00Z", result={
        "execution_mode": "kubernetes", "validation_passed": True, "validation_score": 100,
        "iteration_count": 1, "final_report": "Real acceptance report",
        "cluster_context": {"pods": [{"containers": [{"termination_reason": "OOMKilled", "exit_code": 137}]}]},
        "validation_history": [{"checks": [{"name": name, "passed": True} for name in (
            "sandbox-target", "sandbox-context", "patch-policy", "deployment-identity", "sandbox-apply",
            "rollout", "pod-health", "recent-logs", "http-health",
        )]}],
    })


def test_acceptance_requires_all_golden_path_evidence():
    run = accepted_run()
    assert assess_run(run, 1).passed
    for key, value in [("execution_mode", "simulation"), ("validation_score", 99), ("iteration_count", 3),
                       ("validation_passed", False), ("cluster_context", {}), ("final_report", "")]:
        broken = run.model_copy(deep=True)
        broken.result[key] = value
        assert not assess_run(broken, 1).passed
    broken = run.model_copy(deep=True)
    broken.result["validation_history"][0]["checks"].pop()
    assert not assess_run(broken, 1).passed
    simulated = run.model_copy(update={"status": "simulated"})
    assert not assess_run(simulated, 1).passed


def test_recorder_persists_five_distinct_results_and_resets_only_after_terminal(tmp_path, monkeypatch):
    import asyncio
    import json
    import httpx
    import scripts.record_golden_runs as recorder
    counters = {"created": 0, "reset": 0}
    def handle(request):
        path = request.url.path
        if path == "/__test__/reset":
            return httpx.Response(404)
        if path == "/api/runtime":
            return httpx.Response(200, json={"execution_mode": "kubernetes", "runs_enabled": True,
                                            "provider_configured": True, "daily_run_limit": 20})
        if path == "/api/runs":
            return httpx.Response(200, json=[])
        if path == "/api/incidents/demo/oomkilled":
            counters["created"] += 1
            return httpx.Response(201, json={"id": f"incident-{counters['created']}"})
        if request.method == "POST":
            return httpx.Response(202, json={"id": f"run-{counters['created']}"})
        run = accepted_run().model_copy(update={"id": f"run-{counters['created']}", "incident_id": f"incident-{counters['created']}"})
        return httpx.Response(200, json=run.model_dump(mode="json"))
    original = httpx.AsyncClient
    monkeypatch.setattr(recorder.httpx, "AsyncClient", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handle)))
    def reset(verifier):
        assert counters["created"] == 5
        counters["reset"] += 1
    monkeypatch.setattr(recorder, "reset_local_lab", reset)
    output = tmp_path / "results.json"
    assert asyncio.run(recorder.record("http://127.0.0.1:8000", output, object()))
    result = json.loads(output.read_text())
    assert result["status"] == "passed" and result["reset_healthy"]
    assert len({item["run_id"] for item in result["records"]}) == 5
    assert counters == {"created": 5, "reset": 1}


def test_recorder_interrupt_does_not_reset_an_active_worker(tmp_path, monkeypatch):
    import asyncio
    import json
    import httpx
    import pytest
    import scripts.record_golden_runs as recorder
    original = httpx.AsyncClient
    def handle(request):
        if request.url.path == "/__test__/reset":
            return httpx.Response(404)
        if request.url.path == "/api/runtime":
            return httpx.Response(200, json={"execution_mode": "kubernetes", "runs_enabled": True,
                                            "provider_configured": True, "daily_run_limit": 20})
        return httpx.Response(200, json=[{"status": "running"}])
    monkeypatch.setattr(recorder.httpx, "AsyncClient", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handle)))
    monkeypatch.setattr(recorder, "reset_local_lab", lambda _: pytest.fail("Must not race an active worker"))
    output = tmp_path / "interrupted.json"
    with pytest.raises(RuntimeError, match="active"):
        asyncio.run(recorder.record("http://127.0.0.1:8000", output, object()))
    result = json.loads(output.read_text())
    assert result["status"] == "incomplete" and result["reset_healthy"] is False
    assert result["records"] == []
