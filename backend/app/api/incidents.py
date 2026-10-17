import asyncio
import sqlite3
import hmac
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.models.incidents import DemoScenario
from app.models.runs import IncidentRecord, RunEvent, RunRecord
from app.models.runtime import RuntimeInfo
from app.storage.sqlite import ActiveRunError, DailyRunLimitError

router = APIRouter(prefix="/api")


def authorize_demo(request: Request):
    config = request.app.state.config
    if not config.runs_enabled:
        raise HTTPException(503, "Demo runs are paused by the operator. Saved history remains available.")
    if config.demo_run_token:
        supplied = request.headers.get("X-Demo-Run-Token", "")
        if not hmac.compare_digest(supplied.encode(), config.demo_run_token.encode()):
            raise HTTPException(401, "A valid demo access code is required.")


@router.get("/runtime", response_model=RuntimeInfo)
def runtime_info(request: Request):
    config = request.app.state.config
    return RuntimeInfo(execution_mode=config.execution_mode, runs_enabled=config.runs_enabled,
                       access_code_required=bool(config.demo_run_token), provider_configured=bool(config.nebius_api_key),
                       storage_ephemeral=config.storage_ephemeral, daily_run_limit=config.daily_run_limit)



def require_incident(request: Request, incident_id: str):
    incident = request.app.state.store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(404, "Incident not found")
    return incident


def require_run(request: Request, run_id: str):
    run = request.app.state.store.get_run(run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run


@router.post("/incidents/demo/{scenario}", response_model=IncidentRecord, status_code=201)
def create_demo(scenario: DemoScenario, request: Request):
    authorize_demo(request)
    return request.app.state.store.create_incident(scenario)


@router.get("/incidents", response_model=list[IncidentRecord])
def list_incidents(request: Request):
    return request.app.state.store.list_incidents()


@router.get("/incidents/{incident_id}", response_model=IncidentRecord)
def get_incident(incident_id: str, request: Request):
    return require_incident(request, incident_id)


@router.post("/incidents/{incident_id}/run", response_model=RunRecord, status_code=202)
async def start_run(incident_id: str, request: Request):
    authorize_demo(request)
    incident = require_incident(request, incident_id)
    try:
        run = request.app.state.store.create_run(incident_id, request.app.state.config.daily_run_limit)
    except ActiveRunError as exc:
        raise HTTPException(409, str(exc)) from exc
    except DailyRunLimitError as exc:
        raise HTTPException(429, str(exc)) from exc
    request.app.state.runs.start(incident, run.id)
    return run


@router.get("/runs", response_model=list[RunRecord])
def list_runs(request: Request):
    return request.app.state.store.list_runs()


@router.get("/runs/{run_id}", response_model=RunRecord)
def get_run(run_id: str, request: Request):
    return require_run(request, run_id)


@router.get("/runs/{run_id}/events", response_model=list[RunEvent])
def get_events(run_id: str, request: Request, after: int = Query(0, ge=0)):
    require_run(request, run_id)
    return request.app.state.store.events(run_id, after)


@router.get("/runs/{run_id}/report", response_class=PlainTextResponse)
def get_report(run_id: str, request: Request):
    run = require_run(request, run_id)
    report = run.result.get("final_report")
    if not report:
        raise HTTPException(409, "Report is not available for this run")
    return PlainTextResponse(report, media_type="text/markdown",
                             headers={"Content-Disposition": f'attachment; filename="rca-{run.id}.md"'})


@router.get("/runs/{run_id}/stream")
async def stream(run_id: str, request: Request, after: int = Query(0, ge=0),
                 last_event_id: Annotated[str | None, Header()] = None):
    require_run(request, run_id)
    try:
        cursor = max(after, int(last_event_id or "0"))
        if cursor < 0:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(400, "Invalid Last-Event-ID") from exc

    async def events():
        nonlocal cursor
        while not await request.is_disconnected():
            try:
                batch = request.app.state.store.events(run_id, cursor)
                for event in batch:
                    cursor = event.id
                    yield f"id: {event.id}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"
                run = request.app.state.store.get_run(run_id)
                if run is None or run.status in {"verified", "simulated", "failed"}:
                    # Final transaction may have committed after the preceding event read.
                    for event in request.app.state.store.events(run_id, cursor):
                        cursor = event.id
                        yield f"id: {event.id}\nevent: {event.type}\ndata: {event.model_dump_json()}\n\n"
                    return
                yield ": keep-alive\n\n"
            except sqlite3.Error:
                yield 'event: stream.error\ndata: {"message":"Event storage unavailable. Reconnect to retry."}\n\n'
                return
            await asyncio.sleep(0.5)

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
