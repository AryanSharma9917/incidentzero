import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("submission_check", Path(__file__).parents[2] / "scripts/check_submission.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def test_release_cannot_pass_by_removing_pending_gates(tmp_path):
    folder = tmp_path / "docs/submission"
    folder.mkdir(parents=True)
    (folder / "readiness.json").write_text(json.dumps({"gates": []}))
    (folder / "golden-path-results.json").write_text(json.dumps({"accepted_live_runs": []}))
    blockers = checker.release_blockers(tmp_path)
    assert any("live_nebius" in message for message in blockers)
    assert any("Five distinct" in message for message in blockers)


def test_simulated_or_duplicated_results_cannot_satisfy_five_run_gate(tmp_path):
    folder = tmp_path / "docs/submission"
    folder.mkdir(parents=True)
    (folder / "readiness.json").write_text(json.dumps({"gates": [
        {"id": name, "status": "passed", "evidence": "operator-reviewed-record"} for name in checker.REQUIRED_GATES
    ]}))
    runs = [{"run_id": str(index), "passed": True, "mode": "simulation", "status": "simulated"} for index in range(5)]
    (folder / "golden-path-results.json").write_text(json.dumps({"accepted_live_runs": runs}))
    assert checker.release_blockers(tmp_path)
    for run in runs:
        run.update(mode="kubernetes", status="verified", run_id="duplicate")
    (folder / "golden-path-results.json").write_text(json.dumps({"accepted_live_runs": runs}))
    assert checker.release_blockers(tmp_path)
