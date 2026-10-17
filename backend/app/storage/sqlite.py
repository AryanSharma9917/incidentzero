import fcntl
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from app.agents.intake import get_demo_incident
from app.models.incidents import DemoScenario
from app.models.runs import IncidentRecord, RunEvent, RunRecord, utc_now


class ActiveRunError(RuntimeError):
    pass


class Store:
    """Short transactions; one connection per operation, safe for worker threads."""

    def __init__(self, path: str):
        self.path = path

    @contextmanager
    def lease(self):
        """Only one API process may recover or execute runs against this database."""
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.path + ".lock", "a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("This database is already owned by another API process; use one worker.") from exc
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY, body TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, incident_id TEXT NOT NULL REFERENCES incidents(id),
                    status TEXT NOT NULL, body TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON runs ((1))
                    WHERE status IN ('queued', 'running');
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES runs(id), type TEXT NOT NULL,
                    message TEXT NOT NULL, created_at TEXT NOT NULL, data TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS events_run ON events(run_id, id);
            """)
        # Single API process owns this local sandbox. A prior process cannot resume a run.
        for run in self.list_runs():
            if run.status in {"queued", "running"}:
                self.finish(run.id, "failed", run.result, "Run interrupted by server restart.")

    def create_incident(self, scenario: DemoScenario) -> IncidentRecord:
        incident = IncidentRecord(id=str(uuid4()), scenario=scenario, incident=get_demo_incident(scenario))
        with self.connect() as db:
            db.execute("INSERT INTO incidents VALUES (?, ?)", (incident.id, incident.model_dump_json()))
        return incident

    def get_incident(self, incident_id: str) -> IncidentRecord | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM incidents WHERE id=?", (incident_id,)).fetchone()
        return IncidentRecord.model_validate_json(row[0]) if row else None

    def list_incidents(self) -> list[IncidentRecord]:
        with self.connect() as db:
            rows = db.execute("SELECT body FROM incidents ORDER BY rowid DESC").fetchall()
        return [IncidentRecord.model_validate_json(row[0]) for row in rows]

    def get_run(self, run_id: str) -> RunRecord | None:
        with self.connect() as db:
            row = db.execute("SELECT body FROM runs WHERE id=?", (run_id,)).fetchone()
        return RunRecord.model_validate_json(row[0]) if row else None

    def list_runs(self) -> list[RunRecord]:
        with self.connect() as db:
            rows = db.execute("SELECT body FROM runs ORDER BY rowid DESC").fetchall()
        return [RunRecord.model_validate_json(row[0]) for row in rows]

    def create_run(self, incident_id: str) -> RunRecord:
        run = RunRecord(id=str(uuid4()), incident_id=incident_id)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM incidents WHERE id=?", (incident_id,)).fetchone()
            if not row:
                raise KeyError(incident_id)
            incident = IncidentRecord.model_validate_json(row[0])
            try:
                db.execute("INSERT INTO runs VALUES (?, ?, ?, ?)", (
                    run.id, incident_id, run.status, run.model_dump_json(),
                ))
            except sqlite3.IntegrityError as exc:
                raise ActiveRunError("The shared sandbox already has an active run.") from exc
            incident.latest_run_id, incident.status = run.id, run.status
            db.execute("UPDATE incidents SET body=? WHERE id=?", (incident.model_dump_json(), incident_id))
            self._event(db, run.id, "incident.received", "Demo incident queued.", {})
        return run

    def _event(self, db, run_id, event_type, message, data):
        db.execute("INSERT INTO events(run_id,type,message,created_at,data) VALUES (?,?,?,?,?)",
                   (run_id, event_type, message, utc_now(), json.dumps(data)))

    def event(self, run_id: str, event_type: str, message: str, data: dict | None = None):
        with self.connect() as db:
            self._event(db, run_id, event_type, message, data or {})

    def update(self, run_id: str, result: dict):
        self._save(run_id, "running", result, None)

    def finish(self, run_id: str, status: str, result: dict, error: str | None = None):
        self._save(run_id, status, result, error)

    def _save(self, run_id: str, status: str, result: dict, error: str | None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT body FROM runs WHERE id=?", (run_id,)).fetchone()
            if not row:
                raise KeyError(run_id)
            run = RunRecord.model_validate_json(row[0])
            if run.status in {"verified", "failed"}:
                return
            run.status, run.result, run.error = status, result, error
            terminal = status in {"verified", "failed"}
            if terminal:
                run.finished_at = utc_now()
            db.execute("UPDATE runs SET status=?, body=? WHERE id=?", (status, run.model_dump_json(), run_id))
            incident_row = db.execute("SELECT body FROM incidents WHERE id=?", (run.incident_id,)).fetchone()
            incident = IncidentRecord.model_validate_json(incident_row[0])
            incident.status = status
            db.execute("UPDATE incidents SET body=? WHERE id=?", (incident.model_dump_json(), incident.id))
            if terminal:
                if error:
                    self._event(db, run_id, "run.error", error, {})
                self._event(db, run_id, "run.completed", f"Run {status}.", {"status": status})

    def events(self, run_id: str, after: int = 0) -> list[RunEvent]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM events WHERE run_id=? AND id>? ORDER BY id", (run_id, after)).fetchall()
        return [RunEvent(**{**dict(row), "data": json.loads(row["data"])}) for row in rows]
