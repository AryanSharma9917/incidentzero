from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]


def _documents(path: Path):
    return list(yaml.safe_load_all(path.read_text()))


def test_all_sandbox_yaml_is_valid() -> None:
    files = sorted((ROOT / "sandbox").rglob("*.yaml"))
    assert files
    for path in files:
        documents = _documents(path)
        assert documents, path
        assert all(isinstance(document, dict) for document in documents), path


def test_scenarios_encode_expected_failures() -> None:
    oom = _documents(ROOT / "sandbox/incidents/oomkilled/patch.yaml")[0]
    crash = _documents(ROOT / "sandbox/incidents/crashloop/patch.yaml")[0]
    readiness = _documents(ROOT / "sandbox/incidents/readiness/patch.yaml")[0]

    oom_container = oom["spec"]["template"]["spec"]["containers"][0]
    crash_container = crash["spec"]["template"]["spec"]["containers"][0]
    readiness_container = readiness["spec"]["template"]["spec"]["containers"][0]

    assert oom_container["resources"]["limits"]["memory"] == "64Mi"
    assert {item["name"]: item["value"] for item in oom_container["env"]}[
        "MEMORY_LOAD_MB"
    ] == "96"
    assert {item["name"]: item["value"] for item in crash_container["env"]}[
        "DATABASE_HOST"
    ] == "db-invalid"
    assert readiness_container["readinessProbe"]["httpGet"]["path"] == "/healthz"
