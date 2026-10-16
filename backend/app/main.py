from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.config.settings import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="IncidentZero API",
        description="API for autonomous, verified Kubernetes incident resolution.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    return app


app = create_app()
