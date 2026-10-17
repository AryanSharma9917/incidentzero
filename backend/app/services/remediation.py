from collections.abc import Mapping
import re
from typing import Any

import yaml

from app.models.incidents import NormalizedIncident
from app.models.kubernetes import KubernetesContext
from app.models.remediation import PatchValidation, PolicyCheck, RemediationCandidate


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False):
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.YAMLError(f"duplicate key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


def _keys_are(value: object, allowed: set[str]) -> bool:
    return isinstance(value, Mapping) and set(value).issubset(allowed)


_MEMORY_QUANTITY = re.compile(r"^(\d+)(Ki|Mi|Gi)$")
_MEMORY_FACTORS = {"Ki": 1024, "Mi": 1024**2, "Gi": 1024**3}


def _memory_bytes(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    match = _MEMORY_QUANTITY.fullmatch(value)
    if not match:
        return None
    return int(match.group(1)) * _MEMORY_FACTORS[match.group(2)]


def _current_container(context: KubernetesContext, name: str) -> dict[str, Any]:
    containers = (
        context.deployment.get("spec", {})
        .get("template", {})
        .get("spec", {})
        .get("containers", [])
    )
    return next(
        (item for item in containers if isinstance(item, dict) and item.get("name") == name),
        {},
    )


class RemediationPolicyValidator:
    """Validate a narrow patch contract without executing or applying it."""

    def validate(
        self,
        candidate: RemediationCandidate,
        incident: NormalizedIncident,
        context: KubernetesContext,
    ) -> PatchValidation:
        checks: list[PolicyCheck] = []

        def check(name: str, passed: bool, message: str) -> None:
            checks.append(PolicyCheck(name=name, passed=passed, message=message))

        target = candidate.affected_resource
        target_ok = (
            target.api_version == "apps/v1"
            and target.kind == "Deployment"
            and target.name == incident.service
            and target.namespace == incident.namespace
            and context.service == incident.service
            and context.namespace == incident.namespace
        )
        check(
            "target-allowlist",
            target_ok,
            "Patch target matches the collected Deployment and incident namespace."
            if target_ok
            else "Patch target does not match the collected Deployment and incident namespace.",
        )

        try:
            documents = list(yaml.load_all(candidate.patch_yaml, Loader=_UniqueKeyLoader))
            patch = documents[0] if len(documents) == 1 else None
            yaml_ok = isinstance(patch, dict)
        except yaml.YAMLError:
            patch = None
            yaml_ok = False
        check(
            "yaml-safe-load",
            yaml_ok,
            "Patch is one safe YAML mapping without duplicate keys."
            if yaml_ok
            else "Patch must be one safe YAML mapping without duplicate keys.",
        )
        if not isinstance(patch, dict):
            return PatchValidation(checks=checks, passed=False)

        identity_ok = (
            patch.get("apiVersion") == "apps/v1"
            and patch.get("kind") == "Deployment"
            and patch.get("metadata")
            == {"name": incident.service, "namespace": incident.namespace}
        )
        check(
            "patch-identity",
            identity_ok,
            "Patch identity matches the allow-listed Deployment."
            if identity_ok
            else "Patch identity must contain only the matching name and namespace.",
        )

        top_level_ok = set(patch) == {"apiVersion", "kind", "metadata", "spec"}
        check(
            "top-level-fields",
            top_level_ok,
            "Patch contains only required strategic-merge fields."
            if top_level_ok
            else "Patch has missing or forbidden top-level fields.",
        )

        spec = patch.get("spec")
        template = spec.get("template") if _keys_are(spec, {"template"}) else None
        pod_spec = template.get("spec") if _keys_are(template, {"spec"}) else None
        containers = pod_spec.get("containers") if _keys_are(pod_spec, {"containers"}) else None
        shape_ok = isinstance(containers, list) and len(containers) == 1
        check(
            "deployment-shape",
            shape_ok,
            "Patch changes exactly one container in the pod template."
            if shape_ok
            else "Patch must change exactly one container and no other pod-template fields.",
        )
        if not shape_ok:
            return PatchValidation(checks=checks, passed=False)

        container = containers[0]
        container_ok = isinstance(container, dict) and container.get("name") == incident.service
        allowed_container_keys = {"name", "resources", "env", "readinessProbe"}
        container_ok = container_ok and set(container).issubset(allowed_container_keys)
        check(
            "container-allowlist",
            container_ok,
            "Patch targets only the known container and allow-listed configuration fields."
            if container_ok
            else "Patch targets an unknown container or a forbidden field.",
        )
        if not container_ok:
            return PatchValidation(checks=checks, passed=False)

        change_fields = set(container) - {"name"}
        one_change = len(change_fields) == 1
        check(
            "single-change-domain",
            one_change,
            "Patch changes one bounded configuration domain."
            if one_change
            else "Patch must change exactly one of resources, env, or readinessProbe.",
        )

        semantic_ok = False
        current = _current_container(context, incident.service)
        if change_fields == {"resources"}:
            resources = container["resources"]
            proposed_limit = (
                _memory_bytes(resources.get("limits", {}).get("memory"))
                if isinstance(resources, dict)
                else None
            )
            current_limit = _memory_bytes(
                current.get("resources", {}).get("limits", {}).get("memory")
            )
            proposed_request = (
                _memory_bytes(resources.get("requests", {}).get("memory"))
                if isinstance(resources, dict) and "requests" in resources
                else None
            )
            semantic_ok = (
                _keys_are(resources, {"requests", "limits"})
                and isinstance(resources.get("limits"), dict)
                and set(resources["limits"]) == {"memory"}
                and proposed_limit is not None
                and current_limit is not None
                and proposed_limit > current_limit
                and (
                    "requests" not in resources
                    or (
                        isinstance(resources["requests"], dict)
                        and set(resources["requests"]) == {"memory"}
                        and proposed_request is not None
                        and proposed_request <= proposed_limit
                    )
                )
            )
        elif change_fields == {"env"}:
            env = container["env"]
            current_env = {
                item.get("name"): item.get("value")
                for item in current.get("env", [])
                if isinstance(item, dict)
            }
            semantic_ok = (
                isinstance(env, list)
                and len(env) == 1
                and isinstance(env[0], dict)
                and env[0].get("name") == "DATABASE_HOST"
                and set(env[0]) == {"name", "value"}
                and isinstance(env[0]["value"], str)
                and bool(env[0]["value"].strip())
                and "DATABASE_HOST" in current_env
                and env[0]["value"] != current_env.get("DATABASE_HOST")
            )
        elif change_fields == {"readinessProbe"}:
            probe = container["readinessProbe"]
            http_get = probe.get("httpGet") if _keys_are(probe, {"httpGet"}) else None
            current_http_get = current.get("readinessProbe", {}).get("httpGet", {})
            semantic_ok = (
                _keys_are(http_get, {"path", "port"})
                and set(http_get) in ({"path"}, {"path", "port"})
                and isinstance(http_get.get("path"), str)
                and http_get["path"].startswith("/")
                and http_get["path"] != "/"
                and isinstance(current_http_get.get("path"), str)
                and http_get["path"] != current_http_get.get("path")
                and (
                    "port" not in http_get
                    or isinstance(http_get["port"], (str, int))
                    and not isinstance(http_get["port"], bool)
                )
            )
        check(
            "change-policy",
            semantic_ok,
            "Patch content satisfies the allow-listed configuration policy."
            if semantic_ok
            else "Patch content violates the resources, environment, or readiness policy.",
        )

        passed = all(item.passed for item in checks)
        return PatchValidation(checks=checks, passed=passed)
