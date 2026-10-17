from app.models.incidents import DemoScenario, IncidentInput, NormalizedIncident, Severity


_DEMO_INCIDENTS: dict[DemoScenario, IncidentInput] = {
    DemoScenario.OOM_KILLED: IncidentInput(
        title="Payment API pods are repeatedly restarting",
        service="payment-api",
        environment="demo",
        severity=Severity.P1,
        symptoms=["Elevated restart count", "Requests intermittently fail"],
    ),
    DemoScenario.CRASH_LOOP: IncidentInput(
        title="Payment API cannot remain available",
        service="payment-api",
        environment="demo",
        severity=Severity.P1,
        symptoms=["Pods restart shortly after launch", "Service has no stable replicas"],
    ),
    DemoScenario.READINESS_FAILURE: IncidentInput(
        title="Payment API is not receiving traffic",
        service="payment-api",
        environment="demo",
        severity=Severity.P2,
        symptoms=["Pods remain unready", "Endpoints are unavailable"],
    ),
}


def get_demo_incident(scenario: DemoScenario | str) -> IncidentInput:
    """Return a copy so callers cannot mutate the shared demo fixtures."""
    return _DEMO_INCIDENTS[DemoScenario(scenario)].model_copy(deep=True)


def normalize_incident(incident: IncidentInput, incident_id: str) -> NormalizedIncident:
    return NormalizedIncident(incident_id=incident_id, **incident.model_dump())
