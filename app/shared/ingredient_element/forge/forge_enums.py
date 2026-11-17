"""Closed Forge command and wire vocabularies observed from Forge Rust source."""

from enum import StrEnum


class ForgeCommandOpEnum(StrEnum):
    """Forge command names exposed through the command HTTP endpoint."""

    LOCATION_LIST = "location.list"
    WORKSPACE_LIST = "workspace.list"
    ACTIVITY_LIST = "activity.list"
    DAG_READ_CURRENT = "dag.read_current"
    DAG_SETTLE = "dag.settle"
    SWARM_WORKSPACE_PROVISION = "swarm.workspace_provision"
    SWARM_WORKSPACE_GET = "swarm.workspace_get"
    SWARM_MEMBER_CAPTURE = "swarm.member_capture"
    SWARM_CONVERGE = "swarm.converge"
    SWARM_SETTLE = "swarm.settle"
    SWARM_MATERIALIZE_HYBRID = "swarm.materialize_hybrid"
    SWARM_SETTLEMENT_GET = "swarm.settlement_get"
    SWARM_PURGE = "swarm.purge"


class ForgeErrorCodeEnum(StrEnum):
    """Stable uppercase error codes returned in Forge failure envelopes."""

    FORGE_UNAVAILABLE = "FORGE_UNAVAILABLE"
    AUTH_FAILED = "AUTH_FAILED"
    WORKSPACE_CONFINEMENT_DENIED = "WORKSPACE_CONFINEMENT_DENIED"
    WORKSPACE_SCOPE_OVERLAP = "WORKSPACE_SCOPE_OVERLAP"
    WORKSPACE_ROOT_CONFLICT = "WORKSPACE_ROOT_CONFLICT"
    WORKSPACE_IDENTITY_CONFLICT = "WORKSPACE_IDENTITY_CONFLICT"
    WORKSPACE_REMOVAL_BLOCKED = "WORKSPACE_REMOVAL_BLOCKED"
    INVALID_PATH_KIND = "INVALID_PATH_KIND"
    STALE_REVISION = "STALE_REVISION"
    LEASE_CONFLICT = "LEASE_CONFLICT"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    PLANNING_CONFLICT = "PLANNING_CONFLICT"
    RESYNC_REQUIRED = "RESYNC_REQUIRED"
    UNKNOWN_OUTCOME = "UNKNOWN_OUTCOME"
    INVALID_INPUT = "INVALID_INPUT"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"


class LocationStateEnum(StrEnum):
    """Lifecycle states for registered Forge Locations."""

    ENABLED = "enabled"
    DISABLED = "disabled"


class ActivityStateEnum(StrEnum):
    """Durable Forge Activity states."""

    OPEN = "open"
    CLOSED = "closed"
    INTERRUPTED = "interrupted"


class ActivityLivenessEnum(StrEnum):
    """Projection liveness values for Forge Activities."""

    AVAILABLE = "available"
    LIVE = "live"
    EXPIRED = "expired"
    CLOSED = "closed"
    INTERRUPTED = "interrupted"


class DagNodeLifecycleEnum(StrEnum):
    """Durable DAG node lifecycle values."""

    PENDING = "pending"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class DagNodeStatusEnum(StrEnum):
    """Readiness projection states for DAG nodes."""

    PENDING = "pending"
    READY = "ready"
    ACTIVE = "active"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class DagLineageKindEnum(StrEnum):
    """Lineage operations for DAG node succession."""

    SPLIT = "split"
    REPLACE = "replace"
    MERGE = "merge"


class SwarmWorkspaceModeEnum(StrEnum):
    """Workspace isolation modes supported by Forge Swarm operations."""

    INHERIT = "inherit"
    SHARE = "share"
    BRANCH = "branch"


class SwarmTargetKindEnum(StrEnum):
    """Tagged target variants for a Forge Swarm workspace."""

    STANDALONE_SWARM = "standalone_swarm"
    DAG_NODE_HYBRID = "dag_node_hybrid"


class SwarmConvergenceStatusEnum(StrEnum):
    """Tagged outcomes for a Forge Swarm convergence attempt."""

    CONVERGED = "converged"
    CONFLICT = "conflict"


class SettlementJournalStateEnum(StrEnum):
    """Durable journal states attached to Swarm settlement receipts."""

    PREPARED = "prepared"
    APPLIED = "applied"
    RECOVERY_REQUIRED = "recovery_required"


class ForgeReadbackKindEnum(StrEnum):
    """Readback identity variants emitted by Step 2 mutating commands."""

    SWARM_WORKSPACE = "swarm_workspace"
    SWARM_SETTLEMENT = "swarm_settlement"


class ForgePrincipalKindEnum(StrEnum):
    """Authenticated principal kinds carried by Forge command DTOs."""

    TRUSTED_STDIO = "trusted_stdio"
    DIRECT_TOKEN = "direct_token"  # noqa: S105 - Forge wire principal kind, not a credential.
    OAUTH_GRANT = "oauth_grant"
