"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing import NotRequired
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import (
    SwarmConvergenceGateDict,
    SwarmRunDict,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt32, UInt64


class ForgeConvergeSwarmRequestDict(TypedDict, total=True, closed=True):
    """Complete converge command sent to Orchestration."""

    requestId: str
    sessionId: str
    candidateMemberIds: list[str]
    stageCandidateOnly: bool


class ForgeSettleSwarmOutboxOptionalRequestDict(TypedDict, total=True, closed=True):
    """Serde-omitted optional outbox request fields."""

    outboxMigrationId: NotRequired[str]
    outboxAfterSequence: NotRequired[UInt64]


class ForgeSettleSwarmRequestDict(TypedDict, total=True, closed=True):
    """Serde-compatible settle command sent to Orchestration."""

    requestId: str
    sessionId: str
    activityId: NotRequired[str]
    coordinatorAgentId: str
    outboxMigrationId: NotRequired[str]
    outboxAfterSequence: NotRequired[UInt64]
    purgeEphemeral: bool


class SyncAutonomyOutboxRequestDict(TypedDict, total=True, closed=True):
    """Serde-compatible bounded outbox sync command."""

    migrationId: str
    afterSequence: UInt64
    limit: NotRequired[UInt32]


class SyncAutonomyOutboxResponseDict(TypedDict, total=True, closed=True):
    """Complete bounded outbox sync receipt."""

    appliedCount: UInt64
    dagSettledCount: UInt64
    swarmSettledCount: UInt64
    lastSequence: UInt64


class ForgeConvergeSwarmResponseDict(TypedDict, total=True, closed=True):
    """Convergence response with source optionality normalized."""

    run: SwarmRunDict
    changedFiles: list[str]
    gate: SwarmConvergenceGateDict | None


class ForgeSettleSwarmResponseDict(TypedDict, total=True, closed=True):
    """Settlement response with source optionality normalized."""

    run: SwarmRunDict
    gate: SwarmConvergenceGateDict
    settlementId: UUID
    settledFileCount: UInt64
    settledAtMs: Int64
    outboxSequence: UInt64 | None
    outboxSync: SyncAutonomyOutboxResponseDict | None
    purgedEphemeral: bool
