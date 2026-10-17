"""Structured operational records with an explicit allow-list; never log workflow payloads."""
import json
import logging
import sys
from datetime import datetime, timezone

logger = logging.getLogger("incidentzero.workflow")


def configure_logging():
    parent = logging.getLogger("incidentzero")
    parent.setLevel(logging.INFO)
    if not parent.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        parent.addHandler(handler)


def log_event(*, incident_id: str, run_id: str, node: str, event: str,
              duration_ms: float, status: str):
    logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_id": incident_id, "run_id": run_id, "node": node,
        "event": event, "duration_ms": round(duration_ms, 2), "status": status,
    }, separators=(",", ":")))
