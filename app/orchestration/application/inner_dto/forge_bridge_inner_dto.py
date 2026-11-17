"""Immutable request and response DTOs for East-West bridge operations."""

from dataclasses import dataclass
from typing import NotRequired
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
    SwarmConvergenceGateDict,
    SwarmConvergenceGateDto,
    SwarmRunDict,
    SwarmRunDto,
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


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeConvergeSwarmCommandDto:
    """Immutable Source converge request."""

    request_id: UUID
    session_id: UUID
    candidate_member_ids: tuple[UUID, ...]
    stage_candidate_only: bool

    def to_dict(self) -> ForgeConvergeSwarmRequestDict:
        """Serialize the complete converge command.

        Args:
            None.
        Return:
            Closed converge request dictionary.
        """
        result = ForgeConvergeSwarmRequestDict(
            requestId=str(self.request_id),
            sessionId=str(self.session_id),
            candidateMemberIds=[str(member_id) for member_id in self.candidate_member_ids],
            stageCandidateOnly=self.stage_candidate_only,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSettleSwarmOutboxOptionsDto:
    """Optional outbox cursor values grouped for Source omission rules."""

    migration_id: UUID | None
    after_sequence: UInt64 | None

    def to_dict(self) -> ForgeSettleSwarmOutboxOptionalRequestDict:
        """Serialize only outbox fields whose Source values are present.

        Args:
            None.
        Return:
            Typed optional outbox request fields.
        """
        result = ForgeSettleSwarmOutboxOptionalRequestDict()
        if self.migration_id is not None:
            result["outboxMigrationId"] = str(self.migration_id)
        if self.after_sequence is not None:
            result["outboxAfterSequence"] = self.after_sequence
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSettleSwarmCommandDto:
    """Immutable Source settlement request."""

    request_id: UUID
    session_id: UUID
    activity_id: UUID | None
    coordinator_agent_id: UUID
    outbox_options: ForgeSettleSwarmOutboxOptionsDto
    purge_ephemeral: bool

    def to_dict(self) -> ForgeSettleSwarmRequestDict:
        """Serialize Source option fields only when they are present.

        Args:
            None.
        Return:
            Closed settlement request dictionary.
        """
        result = ForgeSettleSwarmRequestDict(
            requestId=str(self.request_id),
            sessionId=str(self.session_id),
            coordinatorAgentId=str(self.coordinator_agent_id),
            purgeEphemeral=self.purge_ephemeral,
        )
        if self.activity_id is not None:
            result["activityId"] = str(self.activity_id)
        result.update(self.outbox_options.to_dict())
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncAutonomyOutboxCommandDto:
    """Immutable bounded outbox synchronization request."""

    migration_id: UUID
    after_sequence: UInt64
    limit: UInt32 | None

    def to_dict(self) -> SyncAutonomyOutboxRequestDict:
        """Serialize the source cursor and omit an absent optional page size.

        Args:
            None.
        Return:
            Closed outbox sync request dictionary.
        """
        result = SyncAutonomyOutboxRequestDict(
            migrationId=str(self.migration_id),
            afterSequence=self.after_sequence,
        )
        if self.limit is not None:
            result["limit"] = self.limit
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SyncAutonomyOutboxResponseDto:
    """Immutable summary of one outbox reconciliation page."""

    applied_count: UInt64
    dag_settled_count: UInt64
    swarm_settled_count: UInt64
    last_sequence: UInt64

    def to_dict(self) -> SyncAutonomyOutboxResponseDict:
        """Serialize the exact source synchronization counters.

        Args:
            None.
        Return:
            Closed outbox sync response dictionary.
        """
        result = SyncAutonomyOutboxResponseDict(
            appliedCount=self.applied_count,
            dagSettledCount=self.dag_settled_count,
            swarmSettledCount=self.swarm_settled_count,
            lastSequence=self.last_sequence,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeConvergeSwarmResponseDto:
    """Immutable convergence result and optional verified gate."""

    run: SwarmRunDto
    changed_files: tuple[str, ...]
    gate: SwarmConvergenceGateDto | None

    def to_dict(self) -> ForgeConvergeSwarmResponseDict:
        """Serialize the validated convergence projection.

        Args:
            None.
        Return:
            Closed convergence response dictionary.
        """
        gate = self.gate.to_dict() if self.gate is not None else None
        result = ForgeConvergeSwarmResponseDict(
            run=self.run.to_dict(),
            changedFiles=list(self.changed_files),
            gate=gate,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSettleSwarmResponseDto:
    """Immutable settlement result with normalized optional outbox evidence."""

    run: SwarmRunDto
    gate: SwarmConvergenceGateDto
    settlement_id: UUID
    settled_file_count: UInt64
    settled_at_ms: Int64
    outbox_sequence: UInt64 | None
    outbox_sync: SyncAutonomyOutboxResponseDto | None
    purged_ephemeral: bool

    def to_dict(self) -> ForgeSettleSwarmResponseDict:
        """Serialize the settlement and nullable outbox observations.

        Args:
            None.
        Return:
            Closed settlement response dictionary.
        """
        result = ForgeSettleSwarmResponseDict(
            run=self.run.to_dict(),
            gate=self.gate.to_dict(),
            settlementId=self.settlement_id,
            settledFileCount=self.settled_file_count,
            settledAtMs=self.settled_at_ms,
            outboxSequence=self.outbox_sequence,
            outboxSync=self.outbox_sync.to_dict() if self.outbox_sync is not None else None,
            purgedEphemeral=self.purged_ephemeral,
        )
        return result
