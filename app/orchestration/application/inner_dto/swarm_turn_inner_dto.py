"""Immutable request and result DTOs for Native Swarm member turns."""

from dataclasses import dataclass
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.autonomy_snapshot_inner_dto import (
    LaunchLedgerRecordDict,
    LaunchLedgerRecordDto,
)
from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPermissionsDict,
    ExecutionPermissionsDto,
    ExecutionPreferenceDict,
    ExecutionPreferenceDto,
    ExecutionPreferenceResultDict,
    ExecutionTimeoutsDict,
    ExecutionTimeoutsDto,
    McpGrantDict,
    McpGrantDto,
)
from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
    SwarmBoardMessageDict,
    SwarmBoardMessageDto,
    SwarmMemberDict,
    SwarmMemberDto,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    PositiveInt64,
    SignedInt32,
    UnixTimestampMs,
    WorkAttempt,
)
from app.orchestration.schema.types.orchestration_types import UInt64
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmTurnFailureDispositionEnum,
)


class ClaimSwarmWakeupRequestDict(TypedDict, total=True, closed=True):
    """Closed wire request for a Swarm wakeup claim."""

    snapshotId: str


class CompleteSwarmTurnRequestDict(TypedDict, total=True, closed=True):
    """Closed wire request for clean turn completion."""

    expectedSnapshotId: str
    outputCommitOid: str | None
    outputTreeBlake3Hex: str | None


class FailSwarmTurnRequestDict(TypedDict, total=True, closed=True):
    """Closed wire request for non-clean turn release."""

    expectedSnapshotId: str
    disposition: str
    consumeTurn: bool


class DispatchSwarmTurnRequestDict(TypedDict, total=True, closed=True):
    """Closed wire request for one supervised Swarm dispatch."""

    snapshotRequestId: str
    snapshotId: str
    activityId: str
    defaultWorktreePath: str
    leaseId: str
    leaseRevision: PositiveInt64
    leaseExpiresAtMs: UnixTimestampMs
    mcpGrant: McpGrantDict | None
    permissions: ExecutionPermissionsDict
    timeouts: ExecutionTimeoutsDict
    dispatchedAtMs: UnixTimestampMs | None
    cleanExitOutputCommitOid: str | None
    cleanExitOutputTreeBlake3Hex: str | None
    forgeSessionId: str | None


class SwitchSwarmMemberModelRequestDict(TypedDict, total=True, closed=True):
    """Closed wire request for a Swarm member Profile switch."""

    newProfileId: str | None
    requestId: str | None
    profileId: str | None
    expectedProfileRevision: PositiveInt64 | None
    newPreference: ExecutionPreferenceDict | None


class SwarmWakeupBatchDict(TypedDict, total=True, closed=True):
    """Closed canonical coalesced wakeup batch result."""

    swarmRunId: UUID
    member: SwarmMemberDict
    snapshotId: UUID
    committedSeenSeq: UInt64
    inflightTargetSeq: UInt64
    messages: list[SwarmBoardMessageDict]
    totalBodyBytes: UInt64


class CommittedExecutionSnapshotDict(TypedDict, total=True, closed=True):
    """Closed immutable dispatch execution snapshot result."""

    snapshotId: UUID
    workspaceId: UUID
    goalId: UUID
    dagRevision: DagRevision
    nodeId: UUID
    assignmentId: UUID
    attempt: WorkAttempt
    activityId: UUID
    profileId: UUID
    profileRevision: PositiveInt64
    resolvedEngine: str
    resolvedModel: str
    resolvedReasoning: str | None
    rolePromptDigestHex: str | None
    worktreePath: str
    leaseId: UUID
    leaseRevision: UInt64
    leaseExpiresAtMs: UnixTimestampMs
    mcpGrant: McpGrantDict | None
    permissions: ExecutionPermissionsDict
    timeouts: ExecutionTimeoutsDict
    committedAtMs: UnixTimestampMs


class DispatchedTurnSupervisionDict(TypedDict, total=True, closed=True):
    """Closed process supervision and launch-ledger result."""

    status: str
    ledger: LaunchLedgerRecordDict
    exitCode: SignedInt32 | None
    termination: str | None
    unknownReason: str | None


class DispatchedTurnDispositionDict(TypedDict, total=True, closed=True):
    """Closed source-owned member disposition result."""

    kind: str
    member: SwarmMemberDict
    exitCode: SignedInt32 | None
    timedOut: bool


class DispatchSwarmTurnResponseDict(TypedDict, total=True, closed=True):
    """Closed full Swarm dispatch result."""

    wakeupBatch: SwarmWakeupBatchDict
    committedSnapshot: CommittedExecutionSnapshotDict
    supervision: DispatchedTurnSupervisionDict
    disposition: DispatchedTurnDispositionDict
    usedParentSpawnerSlot: bool


class SwarmModelSwitchResponseDict(TypedDict, total=True, closed=True):
    """Closed result for a Swarm member Profile switch."""

    member: SwarmMemberDict
    profileId: UUID
    profileRevision: PositiveInt64
    resolvedPreference: ExecutionPreferenceResultDict


@dataclass(frozen=True, slots=True, kw_only=True)
class ClaimSwarmWakeupCommandDto:
    """Immutable source request for a Swarm wakeup claim."""

    snapshot_id: UUID

    def to_dict(self) -> ClaimSwarmWakeupRequestDict:
        """Serialize the exact camelCase source request.

        Args:
            None.
        Return:
            Closed typed wakeup-claim request.
        """
        result = ClaimSwarmWakeupRequestDict(snapshotId=str(self.snapshot_id))
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class CompleteSwarmTurnCommandDto:
    """Immutable source request for clean turn completion."""

    expected_snapshot_id: UUID
    output_commit_oid: str | None
    output_tree_blake3_hex: str | None

    def to_dict(self) -> CompleteSwarmTurnRequestDict:
        """Serialize completion fields while preserving both nullable controls.

        Args:
            None.
        Return:
            Closed typed completion request.
        """
        result = CompleteSwarmTurnRequestDict(
            expectedSnapshotId=str(self.expected_snapshot_id),
            outputCommitOid=self.output_commit_oid,
            outputTreeBlake3Hex=self.output_tree_blake3_hex,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class FailSwarmTurnCommandDto:
    """Immutable source request for releasing a failed or suspended turn."""

    expected_snapshot_id: UUID
    disposition: SwarmTurnFailureDispositionEnum
    consume_turn: bool

    def to_dict(self) -> FailSwarmTurnRequestDict:
        """Serialize failure disposition with its canonical source spelling.

        Args:
            None.
        Return:
            Closed typed failure request.
        """
        result = FailSwarmTurnRequestDict(
            expectedSnapshotId=str(self.expected_snapshot_id),
            disposition=self.disposition.value,
            consumeTurn=self.consume_turn,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class DispatchSwarmTurnCommandDto:
    """Immutable source request for one bounded Swarm dispatch."""

    snapshot_request_id: UUID
    snapshot_id: UUID
    activity_id: UUID
    default_worktree_path: str
    lease_id: UUID
    lease_revision: PositiveInt64
    lease_expires_at_ms: UnixTimestampMs
    mcp_grant: McpGrantDto | None
    permissions: ExecutionPermissionsDto
    timeouts: ExecutionTimeoutsDto
    dispatched_at_ms: UnixTimestampMs | None
    clean_exit_output_commit_oid: str | None
    clean_exit_output_tree_blake3_hex: str | None
    forge_session_id: UUID | None

    def to_dict(self) -> DispatchSwarmTurnRequestDict:
        """Serialize all source request controls, including explicit nulls.

        Args:
            None.
        Return:
            Closed typed Swarm dispatch request.
        """
        mcp_grant = self.mcp_grant.to_dict() if self.mcp_grant is not None else None
        forge_session_id = str(self.forge_session_id) if self.forge_session_id is not None else None
        result = DispatchSwarmTurnRequestDict(
            snapshotRequestId=str(self.snapshot_request_id),
            snapshotId=str(self.snapshot_id),
            activityId=str(self.activity_id),
            defaultWorktreePath=self.default_worktree_path,
            leaseId=str(self.lease_id),
            leaseRevision=self.lease_revision,
            leaseExpiresAtMs=self.lease_expires_at_ms,
            mcpGrant=mcp_grant,
            permissions=self.permissions.to_dict(),
            timeouts=self.timeouts.to_dict(),
            dispatchedAtMs=self.dispatched_at_ms,
            cleanExitOutputCommitOid=self.clean_exit_output_commit_oid,
            cleanExitOutputTreeBlake3Hex=self.clean_exit_output_tree_blake3_hex,
            forgeSessionId=forge_session_id,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwitchSwarmMemberModelCommandDto:
    """Immutable source request for changing a Swarm member's model Profile."""

    new_profile_id: UUID | None
    request_id: UUID | None
    profile_id: UUID | None
    expected_profile_revision: PositiveInt64 | None
    new_preference: ExecutionPreferenceDto | None

    def to_dict(self) -> SwitchSwarmMemberModelRequestDict:
        """Serialize one of the source-supported Profile switch requests.

        Args:
            None.
        Return:
            Closed typed model-switch request.
        """
        new_preference = self.new_preference.to_dict() if self.new_preference is not None else None
        new_profile_id = str(self.new_profile_id) if self.new_profile_id is not None else None
        request_id = str(self.request_id) if self.request_id is not None else None
        profile_id = str(self.profile_id) if self.profile_id is not None else None
        result = SwitchSwarmMemberModelRequestDict(
            newProfileId=new_profile_id,
            requestId=request_id,
            profileId=profile_id,
            expectedProfileRevision=self.expected_profile_revision,
            newPreference=new_preference,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmWakeupBatchDto:
    """Immutable source wakeup batch and its parsed board messages."""

    swarm_run_id: UUID
    member: SwarmMemberDto
    snapshot_id: UUID
    committed_seen_seq: UInt64
    inflight_target_seq: UInt64
    messages: tuple[SwarmBoardMessageDto, ...]
    total_body_bytes: UInt64

    def to_dict(self) -> SwarmWakeupBatchDict:
        """Serialize the wakeup batch through its closed typed dictionary.

        Args:
            None.
        Return:
            Closed typed Swarm wakeup batch result.
        """
        from app.shared.types.threaded_mapping import threaded_map

        messages = threaded_map(lambda message: message.to_dict(), self.messages)
        result = SwarmWakeupBatchDict(
            swarmRunId=self.swarm_run_id,
            member=self.member.to_dict(),
            snapshotId=self.snapshot_id,
            committedSeenSeq=self.committed_seen_seq,
            inflightTargetSeq=self.inflight_target_seq,
            messages=messages,
            totalBodyBytes=self.total_body_bytes,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class CommittedExecutionSnapshotDto:
    """Immutable execution snapshot sealed immediately before dispatch."""

    snapshot_id: UUID
    workspace_id: UUID
    goal_id: UUID
    dag_revision: DagRevision
    node_id: UUID
    assignment_id: UUID
    attempt: WorkAttempt
    activity_id: UUID
    profile_id: UUID
    profile_revision: PositiveInt64
    resolved_engine: str
    resolved_model: str
    resolved_reasoning: str | None
    role_prompt_digest_hex: str | None
    worktree_path: str
    lease_id: UUID
    lease_revision: UInt64
    lease_expires_at_ms: UnixTimestampMs
    mcp_grant: McpGrantDto | None
    permissions: ExecutionPermissionsDto
    timeouts: ExecutionTimeoutsDto
    committed_at_ms: UnixTimestampMs

    def to_dict(self) -> CommittedExecutionSnapshotDict:
        """Serialize the frozen snapshot using source field names.

        Args:
            None.
        Return:
            Closed typed committed execution snapshot.
        """
        mcp_grant = self.mcp_grant.to_dict() if self.mcp_grant is not None else None
        result = CommittedExecutionSnapshotDict(
            snapshotId=self.snapshot_id,
            workspaceId=self.workspace_id,
            goalId=self.goal_id,
            dagRevision=self.dag_revision,
            nodeId=self.node_id,
            assignmentId=self.assignment_id,
            attempt=self.attempt,
            activityId=self.activity_id,
            profileId=self.profile_id,
            profileRevision=self.profile_revision,
            resolvedEngine=self.resolved_engine,
            resolvedModel=self.resolved_model,
            resolvedReasoning=self.resolved_reasoning,
            rolePromptDigestHex=self.role_prompt_digest_hex,
            worktreePath=self.worktree_path,
            leaseId=self.lease_id,
            leaseRevision=self.lease_revision,
            leaseExpiresAtMs=self.lease_expires_at_ms,
            mcpGrant=mcp_grant,
            permissions=self.permissions.to_dict(),
            timeouts=self.timeouts.to_dict(),
            committedAtMs=self.committed_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class DispatchedTurnSupervisionDto:
    """Immutable supervision state and durable launch-ledger result."""

    status: str
    ledger: LaunchLedgerRecordDto
    exit_code: SignedInt32 | None
    termination: str | None
    unknown_reason: str | None

    def to_dict(self) -> DispatchedTurnSupervisionDict:
        """Serialize process supervision and launch-ledger fields.

        Args:
            None.
        Return:
            Closed typed dispatch supervision result.
        """
        result = DispatchedTurnSupervisionDict(
            status=self.status,
            ledger=self.ledger.to_dict(),
            exitCode=self.exit_code,
            termination=self.termination,
            unknownReason=self.unknown_reason,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class DispatchedTurnDispositionDto:
    """Immutable source-owned disposition for one completed dispatch."""

    kind: str
    member: SwarmMemberDto
    exit_code: SignedInt32 | None
    timed_out: bool

    def to_dict(self) -> DispatchedTurnDispositionDict:
        """Serialize the member disposition using source field names.

        Args:
            None.
        Return:
            Closed typed turn disposition result.
        """
        result = DispatchedTurnDispositionDict(
            kind=self.kind,
            member=self.member.to_dict(),
            exitCode=self.exit_code,
            timedOut=self.timed_out,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class DispatchSwarmTurnInnerDto:
    """Immutable full receipt for one dispatched and supervised member turn."""

    wakeup_batch: SwarmWakeupBatchDto
    committed_snapshot: CommittedExecutionSnapshotDto
    supervision: DispatchedTurnSupervisionDto
    disposition: DispatchedTurnDispositionDto
    used_parent_spawner_slot: bool

    def to_dict(self) -> DispatchSwarmTurnResponseDict:
        """Serialize the full dispatch result using closed nested dictionaries.

        Args:
            None.
        Return:
            Closed typed Swarm dispatch response.
        """
        result = DispatchSwarmTurnResponseDict(
            wakeupBatch=self.wakeup_batch.to_dict(),
            committedSnapshot=self.committed_snapshot.to_dict(),
            supervision=self.supervision.to_dict(),
            disposition=self.disposition.to_dict(),
            usedParentSpawnerSlot=self.used_parent_spawner_slot,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmModelSwitchInnerDto:
    """Immutable model-switch receipt for one Swarm member."""

    member: SwarmMemberDto
    profile_id: UUID
    profile_revision: PositiveInt64
    resolved_preference: ExecutionPreferenceDto

    def to_dict(self) -> SwarmModelSwitchResponseDict:
        """Serialize the model switch with validated Profile preference values.

        Args:
            None.
        Return:
            Closed typed model-switch result.
        """
        result = SwarmModelSwitchResponseDict(
            member=self.member.to_dict(),
            profileId=self.profile_id,
            profileRevision=self.profile_revision,
            resolvedPreference=self.resolved_preference.to_schema_dict(),
        )
        return result
