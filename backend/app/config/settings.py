import os
from dataclasses import dataclass


def _cors_origins() -> list[str]:
    value = os.getenv("CORS_ORIGINS", "http://localhost:3000")
    return [origin.strip() for origin in value.split(",") if origin.strip()]


@dataclass(frozen=True, slots=True)
class Settings:
    cors_origins: list[str]


settings = Settings(cors_origins=_cors_origins())
