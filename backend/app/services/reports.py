import difflib

import yaml


def patch_diff(state: dict) -> str:
    """Review the concrete strategic merge patch alongside the observed container values."""
    patch = state.get("patch", "")
    if not patch:
        return ""
    deployment = state.get("cluster_context", {}).get("deployment", {})
    patch_doc = yaml.safe_load(patch)

    def project(original, shape):
        if isinstance(shape, dict):
            return {key: project(original[key], value) for key, value in shape.items() if key in original}
        if isinstance(shape, list):
            return [project(next((item for item in original if item.get("name") == value.get("name")), {}), value)
                    for value in shape]
        return original

    before = yaml.safe_dump(project(deployment, patch_doc), sort_keys=False)
    after = yaml.safe_dump(patch_doc, sort_keys=False)
    return "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        fromfile="observed/deployment.yaml", tofile="proposed/deployment.yaml"))


def generate_report(state: dict) -> str:
    """Render validated evidence; no additional model claims or invented impact."""
    incident = state.get("incident", {})
    diagnosis = state.get("final_diagnosis", {})
    simulated = state.get("execution_mode") == "simulation"
    verified = state.get("validation_passed", False) and not simulated
    evidence = diagnosis.get("supporting_evidence", [])
    history = state.get("validation_history", [])
    lines = [
        f"# RCA: {incident.get('title', 'Incident')}",
        f"\nIncident: {state.get('incident_id')}\nService: {incident.get('service')}",
        f"Severity: {incident.get('severity')}\nEnvironment: {incident.get('environment')}",
        "\n## Execution mode", "SIMULATION: infrastructure evidence and validation are simulated; no Kubernetes operations or HTTP health checks were executed." if simulated else "Local Kubernetes sandbox.",
        "\n## Impact", "Controlled demo incident. Production impact was not measured.",
        "\n## Root cause", diagnosis.get("root_cause", "No final diagnosis available."),
        "\n## Evidence",
        *[f"- {item['statement']}" + (f" ({item['source_url']})" if item.get("source_url") else "") for item in evidence],
        "\n## Timeline",
        *[f"- {event['stage']}: {event['message']}" for event in state.get("timeline_events", [])],
        "\n## Resolution", state.get("remediation_plan", "No approved candidate generated."),
        "```yaml", state.get("patch", ""), "```",
        "\n## Validation", "Simulation passed; this is not a Kubernetes-verified resolution." if simulated and state.get("validation_passed") else "Verified in the controlled sandbox." if verified else "Sandbox resolution was not verified.",
        *[f"- Attempt {index + 1}: {result['score']}/100; {'PASS' if result['passed'] else 'FAIL'}"
          for index, result in enumerate(history)],
        "\n## Preventive actions",
        "Review workload configuration and add a regression check for the observed failure before production rollout.",
        "\nHuman approval is required before any production change. No production changes were applied.",
    ]
    return "\n".join(lines) + "\n"
