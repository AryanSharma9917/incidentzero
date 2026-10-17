from contextlib import asynccontextmanager
import sqlite3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.config.settings import settings
from app.services.runs import RunManager
from app.storage.sqlite import Store


def create_app(*, database_path: str | None = None, executor=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = Store(database_path or settings.database_path)
        with store.lease():
            store.initialize()
            app.state.store = store
            app.state.runs = RunManager(store, executor)
            try:
                yield
            finally:
                await app.state.runs.close()

    app = FastAPI(
        lifespan=lifespan,
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
    @app.exception_handler(sqlite3.Error)
    async def database_error(request, exc):
        return JSONResponse(status_code=503, content={"detail": "Incident storage is unavailable. Retry shortly."})

    app.include_router(incidents_router)
    app.include_router(health_router)
    return app


app = create_app()
