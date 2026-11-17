"""Closed vocabulary for Gateway mixed-composition responses and filters."""

from enum import StrEnum


class MixedBackendEnum(StrEnum):
    """Backend owning one Mixed dependency result."""

    FORGE = "forge"
    ORCHESTRATION = "orchestration"
    GATEWAY = "gateway"


class MixedDependencyFailureTagEnum(StrEnum):
    """Discriminator for the four typed dependency failure contracts."""

    FORGE_SOURCE = "forge_source"
    ORCHESTRATION_SOURCE = "orchestration_source"
    FORGE_GATEWAY = "forge_gateway"
    ORCHESTRATION_GATEWAY = "orchestration_gateway"
    MIXED_GATEWAY_TIMEOUT = "mixed_gateway_timeout"


class MixedOverviewQueryKeyEnum(StrEnum):
    """Exact snake-case query keys accepted by the Swarm overview route."""

    FORGE_REQUEST_ID = "forge_request_id"
    WORKSPACE_REVISION = "workspace_revision"
    LOCATION_ID = "location_id"
    EXPECTED_REVISION = "expected_revision"
    RELATIVE_ROOT = "relative_root"
    RUN_STATE = "run_state"
    SETTLED_ONLY = "settled_only"
