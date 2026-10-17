import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).parents[3] / ".env")


def _cors_origins() -> list[str]:
    value = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in value.split(",") if origin.strip()]


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


settings = Settings(
    database_path=os.getenv("DATABASE_PATH", str(Path(__file__).parents[2] / "data" / "incidentzero.sqlite3")),
    kubectl_binary=os.getenv("KUBECTL_BIN", "kubectl"),
    cors_origins=_cors_origins(),
    nebius_api_key=os.getenv("NEBIUS_API_KEY") or None,
    nebius_base_url=os.getenv(
        "NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1"
    ).rstrip("/"),
    nebius_model=os.getenv("NEBIUS_MODEL", "nvidia/Nemotron-3_5-Lightning"),
    tavily_api_key=os.getenv("TAVILY_API_KEY") or None,
    tavily_base_url=os.getenv("TAVILY_BASE_URL", "https://api.tavily.com").rstrip("/"),
)
