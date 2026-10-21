import pytest

from app.config.settings import load_settings


def test_nebius_timeout_is_configurable_and_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEBIUS_TIMEOUT_SECONDS", "90")
    configured = load_settings()
    configured.validate()
    assert configured.nebius_timeout_seconds == 90

    monkeypatch.setenv("NEBIUS_TIMEOUT_SECONDS", "121")
    invalid = load_settings()
    with pytest.raises(ValueError, match="NEBIUS_TIMEOUT_SECONDS"):
        invalid.validate()
