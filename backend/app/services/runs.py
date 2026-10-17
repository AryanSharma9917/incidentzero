import asyncio
import time
from collections.abc import Callable
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.agents.diagnosis import DiagnosisAgent, StructuredDiagnosisError
from app.agents.remediation import RemediationAgent
from app.agents.research import ResearchAgent
from app.config.settings import Settings, settings
from app.graph.workflow import build_diagnosis_graph
from app.integrations.errors import IntegrationNotConfiguredError, IntegrationResponseError
from app.integrations.kubernetes import KubernetesCollectionError
from app.integrations.nebius import NebiusClient
from app.integrations.tavily import TavilyClient
from app.models.runs import IncidentRecord
from app.services.demo import DemoController
from app.services.reports import generate_report, patch_diff
from app.services.sandbox import SandboxVerifier
from app.services.simulation import SimulationController
from app.services.telemetry import log_event
from app.storage.sqlite import Store

class LiveExecution:
    def __init__(self, config: Settings | None = None):
        self.config = config

    async def __call__(self, incident: IncidentRecord, run_id: str, emit: Callable):
        config = self.config or settings
        # Fail before mutating the sandbox or making any provider request.
        if not config.nebius_api_key:
            raise IntegrationNotConfiguredError("Provider not configured")
        nebius = NebiusClient(api_key=config.nebius_api_key, base_url=config.nebius_base_url,
                              model=config.nebius_model)
        tavily = TavilyClient(api_key=config.tavily_api_key, base_url=config.tavily_base_url)
        controller = (SimulationController() if config.execution_mode == "simulation"
                      else DemoController(SandboxVerifier(kubectl_binary=config.kubectl_binary)))
        state: dict[str, Any] = {
            "incident_id": incident.id, "run_id": run_id, "incident_input": incident.incident,
            "timeline_events": [], "errors": [], "execution_mode": config.execution_mode,
        }
        names = {
            "intake": "incident", "collect_kubernetes_context": "context",
            "diagnose_with_nemotron": "diagnosis", "research_with_tavily": "research",
            "synthesize_diagnosis": "synthesis", "generate_remediation": "remediation",
            "validate_sandbox": "validation",
        }
        try:
            emit("demo.started", "Preparing SIMULATED infrastructure." if config.execution_mode == "simulation"
                 else "Preparing a controlled local sandbox fault.", jsonable_encoder(state))
            controller.prepare(incident.scenario)
            emit("demo.completed", "Loaded explicitly SIMULATED fault evidence." if config.execution_mode == "simulation"
                 else "Observed the requested fault in Kubernetes.", {})
            graph = build_diagnosis_graph(controller, DiagnosisAgent(nebius), ResearchAgent(tavily),
                                          RemediationAgent(nebius), controller.verifier)
            # Debug task events arrive before each node runs, unlike node-result updates.
            async with asyncio.timeout(600):
                async for mode, chunk in graph.astream(state, stream_mode=["debug", "updates"]):
                    if mode == "debug":
                        if chunk.get("type") == "task":
                            stage = names[chunk["payload"]["name"]]
                            if stage != "incident":
                                emit(f"{stage}.started", f"Starting {stage}.", {})
                        continue
                    for delta in chunk.values():
                        for key, value in delta.items():
                            if key in {"timeline_events", "errors"}:
                                state[key] = [*state.get(key, []), *value]
                            else:
                                state[key] = value
                        if config.execution_mode == "simulation" and state.get("status") == "verified":
                            state["status"] = "simulated"
                        if "patch" in delta:
                            state["patch_diff"] = patch_diff(jsonable_encoder(state))
                        for event in delta.get("timeline_events", []):
                            stage = event.stage
                            if stage == "intake" or stage == "validation.started":
                                continue
                            event_type = {"remediation": "remediation.generated"}.get(stage, stage)
                            if "." not in event_type:
                                event_type += ".completed"
                            emit(event_type, event.message, jsonable_encoder(state))
            if config.execution_mode == "simulation" and state.get("status") == "verified":
                state["status"] = "simulated"
            return jsonable_encoder(state)
        finally:
            await nebius.close()
            await tavily.close()


class RunManager:
    def __init__(self, store: Store, executor=None, config: Settings | None = None):
        self.store = store
        self.executor = executor or LiveExecution(config)
        self.tasks: set[asyncio.Task] = set()

    def start(self, incident: IncidentRecord, run_id: str):
        task = asyncio.create_task(asyncio.to_thread(self.execute, incident, run_id))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def execute(self, incident: IncidentRecord, run_id: str):
        snapshot: dict = {}
        started = time.monotonic()
        node_starts: dict[str, float] = {}

        def emit(event_type: str, message: str, state: dict):
            nonlocal snapshot
            if state:
                snapshot = state
            self.store.update(run_id, snapshot)
            self.store.event(run_id, event_type, message)
            node = event_type.split(".")[0]
            now = time.monotonic()
            if event_type.endswith(".started"):
                node_starts[node] = now
            log_event(incident_id=incident.id, run_id=run_id, node=node, event=event_type,
                      duration_ms=(now - node_starts.get(node, started)) * 1000,
                      status=str(snapshot.get("status", "running")))

        try:
            self.store.update(run_id, {})
            result = asyncio.run(self.executor(incident, run_id, emit))
            passed = result.get("status") in {"verified", "simulated"} and result.get("validation_passed") is True
            status = ("simulated" if result.get("execution_mode") == "simulation" else "verified") if passed else "failed"
            result["status"] = status
            result["patch_diff"] = patch_diff(result)
            result["final_report"] = generate_report(result)
            self.store.event(run_id, "report.generated", "Evidence-based RCA is ready.")
            self.store.finish(run_id, status, result,
                              None if passed else "Workflow did not verify a sandbox resolution.")
            log_event(incident_id=incident.id, run_id=run_id, node="run", event="run.completed",
                      duration_ms=(time.monotonic() - started) * 1000, status=status)
        except Exception as exc:
            # Never persist raw upstream errors, credentials, subprocess output, or tracebacks.
            log_event(incident_id=incident.id, run_id=run_id, node="run", event="run.failed",
                      duration_ms=(time.monotonic() - started) * 1000, status="failed")
            if isinstance(exc, IntegrationNotConfiguredError):
                message = "A required provider key is missing. Configure Nebius and, when research is requested, Tavily."
            elif isinstance(exc, IntegrationResponseError):
                message = "A provider request failed, timed out, or returned malformed data. Check provider access and retry."
            elif isinstance(exc, KubernetesCollectionError):
                message = "Kubernetes evidence or demo setup failed. Check the local Kind context and workload."
            elif isinstance(exc, StructuredDiagnosisError):
                message = "Nemotron did not return a valid diagnosis after the bounded repair attempt."
            elif isinstance(exc, TimeoutError):
                message = "The workflow exceeded its execution deadline. Review the saved evidence before retrying."
            else:
                message = "Run failed. Check provider configuration and local Kind sandbox availability."
            self.store.finish(run_id, "failed", snapshot, message)

    async def close(self):
        # Let bounded operations finish; do not release the shared-sandbox lock mid-write.
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
