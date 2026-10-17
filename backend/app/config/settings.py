import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(Path(__file__).parents[3] / ".env")


def _boolean(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).lower()
    if value not in {"true", "false"}:
        raise ValueError(f"{name} must be true or false")
    return value == "true"


@dataclass(frozen=True, slots=True)
class Settings:
    cors_origins: list[str]
    nebius_api_key: str | None
    nebius_base_url: str
    nebius_model: str
    tavily_api_key: str | None
    tavily_base_url: str
    database_path: str
    kubectl_binary: str
    app_environment: str = "local"
    execution_mode: str = "kubernetes"
    runs_enabled: bool = True
    demo_run_token: str | None = None
    daily_run_limit: int = 20
    storage_ephemeral: bool = False

    def validate(self) -> None:
        if self.app_environment not in {"local", "production"}:
            raise ValueError("APP_ENV must be local or production")
        if self.execution_mode not in {"kubernetes", "simulation"}:
            raise ValueError("EXECUTION_MODE must be kubernetes or simulation")
        if not 1 <= self.daily_run_limit <= 100:
            raise ValueError("DAILY_RUN_LIMIT must be between 1 and 100")
        for origin in self.cors_origins:
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
                raise ValueError("CORS_ORIGINS must contain exact HTTP(S) origins without paths")
            if self.app_environment == "production" and parsed.scheme != "https":
                raise ValueError("Production CORS origins must use HTTPS")
        if self.app_environment == "production":
            if not self.cors_origins:
                raise ValueError("Production requires explicit CORS_ORIGINS")
            if self.execution_mode != "simulation":
                raise ValueError("Public deployment supports simulation only; keep Kind execution local")
            if self.runs_enabled and (not self.demo_run_token or len(self.demo_run_token) < 24):
                raise ValueError("Enabled production runs require a DEMO_RUN_TOKEN of at least 24 characters")
            for endpoint in (self.nebius_base_url, self.tavily_base_url):
                parsed = urlparse(endpoint)
                if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
                    raise ValueError("Production provider endpoints must use HTTPS without URL credentials")


def load_settings() -> Settings:
    production = os.getenv("APP_ENV", "local") == "production"
    return Settings(
        database_path=os.getenv("DATABASE_PATH", str(Path(__file__).parents[2] / "data" / "incidentzero.sqlite3")),
        kubectl_binary=os.getenv("KUBECTL_BIN", "kubectl"),
        cors_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "" if production else "http://localhost:3000").split(",") if origin.strip()],
        nebius_api_key=os.getenv("NEBIUS_API_KEY") or None,
        nebius_base_url=os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1").rstrip("/"),
        nebius_model=os.getenv("NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning"),
        tavily_api_key=os.getenv("TAVILY_API_KEY") or None,
        tavily_base_url=os.getenv("TAVILY_BASE_URL", "https://api.tavily.com").rstrip("/"),
        app_environment=os.getenv("APP_ENV", "local"),
        execution_mode=os.getenv("EXECUTION_MODE", "kubernetes"),
        runs_enabled=_boolean("RUNS_ENABLED", not production),
        demo_run_token=os.getenv("DEMO_RUN_TOKEN") or None,
        daily_run_limit=int(os.getenv("DAILY_RUN_LIMIT", "20")),
        storage_ephemeral=_boolean("STORAGE_EPHEMERAL", False),
    )


settings = load_settings()
