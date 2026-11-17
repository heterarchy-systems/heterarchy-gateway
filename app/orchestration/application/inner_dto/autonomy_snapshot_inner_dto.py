"""Immutable DTOs for execution snapshot prepare and read operations."""

from dataclasses import dataclass
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPermissionsDict,
    ExecutionPermissionsDto,
    ExecutionTimeoutsDict,
    ExecutionTimeoutsDto,
    McpGrantDict,
    McpGrantDto,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    PositiveInt64,
    SignedInt32,
    UnixTimestampMs,
    UnsignedRevision,
    WorkAttempt,
)
from app.orchestration.schema.types.orchestration_types import UInt32, UInt64
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    LaunchLedgerStatusEnum,
    LaunchUnknownReasonEnum,
)
from app.shared.ingredient_element.orchestration.profile_enums import CliEngineEnum


class ProcessOwnershipDict(TypedDict, total=True, closed=True):
    """Operating-system process-group ownership witness dictionary."""

    pid: UInt32
    pgid: UInt32
    startTime: str
    bootId: str


class LaunchLedgerStateDict(TypedDict, total=True, closed=True):
    """Launch-ledger state dictionary with explicit nullable observations."""

    status: LaunchLedgerStatusEnum
    ownership: ProcessOwnershipDict | None
    exitCode: SignedInt32 | None
    unknownReason: LaunchUnknownReasonEnum | None
    observedAtMs: UnixTimestampMs | None


class LaunchLedgerRecordDict(TypedDict, total=True, closed=True):
    """Complete durable execution launch-ledger record dictionary."""

    snapshotId: str
    workspaceId: str
    goalId: str
    dagRevision: DagRevision
    nodeId: str
    assignmentId: str
    attempt: WorkAttempt
    state: LaunchLedgerStateDict
    revision: UnsignedRevision
    updatedAtMs: UnixTimestampMs


class PrepareExecutionSnapshotRequestDict(TypedDict, total=True, closed=True):
    """Complete secret-free execution snapshot prepare request dictionary."""

    requestId: str
    snapshotId: str
    goalId: str
    dagRevision: DagRevision
    nodeId: str
    assignmentId: str
    attempt: WorkAttempt
    activityId: str
    profileId: str
    profileRevision: PositiveInt64
    resolvedEngine: CliEngineEnum
    resolvedModel: str
    resolvedReasoning: str | None
    rolePromptDigestHex: str | None
    worktreePath: str
    leaseId: str
    leaseRevision: UInt64
    leaseExpiresAtMs: UnixTimestampMs
    mcpGrant: McpGrantDict | None
    permissions: ExecutionPermissionsDict
    timeouts: ExecutionTimeoutsDict


class ExecutionSnapshotOutcomeResponseDict(TypedDict, total=True, closed=True):
    """Committed or rejected execution snapshot outcome dictionary."""

    committed: bool
    rejectionCode: str | None
    detail: str | None
    record: LaunchLedgerRecordDict | None


class ExecutionSnapshotQueryResponseDict(TypedDict, total=True, closed=True):
    """Exact execution attempt query response with normalized record absence."""

    workspaceId: str
    goalId: str
    dagRevision: DagRevision
    nodeId: str
    assignmentId: str
    attempt: WorkAttempt
    record: LaunchLedgerRecordDict | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessOwnershipDto:
    """Immutable process-group ownership witness."""

    pid: UInt32
    pgid: UInt32
    start_time: str
    boot_id: str

    def to_dict(self) -> ProcessOwnershipDict:
        """Serialize process ownership witness wire fields.

        Args:
            None.
        Return:
            Complete process ownership dictionary.
        """
        result = ProcessOwnershipDict(
            pid=self.pid,
            pgid=self.pgid,
            startTime=self.start_time,
            bootId=self.boot_id,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class LaunchLedgerStateDto:
    """Immutable execution snapshot state projection."""

    status: LaunchLedgerStatusEnum
    ownership: ProcessOwnershipDto | None
    exit_code: SignedInt32 | None
    unknown_reason: LaunchUnknownReasonEnum | None
    observed_at_ms: UnixTimestampMs | None

    def to_dict(self) -> LaunchLedgerStateDict:
        """Serialize launch-ledger state with all source nullable fields.

        Args:
            None.
        Return:
            Complete launch-ledger state dictionary.
        """
        ownership = self.ownership.to_dict() if self.ownership is not None else None
        result = LaunchLedgerStateDict(
            status=self.status,
            ownership=ownership,
            exitCode=self.exit_code,
            unknownReason=self.unknown_reason,
            observedAtMs=self.observed_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class LaunchLedgerRecordDto:
    """Immutable durable execution snapshot ledger record."""

    snapshot_id: UUID
    workspace_id: UUID
    goal_id: UUID
    dag_revision: DagRevision
    node_id: UUID
    assignment_id: UUID
    attempt: WorkAttempt
    state: LaunchLedgerStateDto
    revision: UnsignedRevision
    updated_at_ms: UnixTimestampMs

    def to_dict(self) -> LaunchLedgerRecordDict:
        """Serialize the launch-ledger record using source camelCase keys.

        Args:
            None.
        Return:
            Complete launch-ledger record dictionary.
        """
        result = LaunchLedgerRecordDict(
            snapshotId=str(self.snapshot_id),
            workspaceId=str(self.workspace_id),
            goalId=str(self.goal_id),
            dagRevision=self.dag_revision,
            nodeId=str(self.node_id),
            assignmentId=str(self.assignment_id),
            attempt=self.attempt,
            state=self.state.to_dict(),
            revision=self.revision,
            updatedAtMs=self.updated_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class PrepareExecutionSnapshotCommandDto:
    """Immutable request to validate and commit an execution snapshot."""

    request_id: UUID
    snapshot_id: UUID
    goal_id: UUID
    dag_revision: DagRevision
    node_id: UUID
    assignment_id: UUID
    attempt: WorkAttempt
    activity_id: UUID
    profile_id: UUID
    profile_revision: PositiveInt64
    resolved_engine: CliEngineEnum
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

    def to_dict(self) -> PrepareExecutionSnapshotRequestDict:
        """Serialize the secret-free snapshot request.

        Args:
            None.
        Return:
            Complete execution snapshot prepare dictionary.
        """
        mcp_grant = self.mcp_grant.to_dict() if self.mcp_grant is not None else None
        result = PrepareExecutionSnapshotRequestDict(
            requestId=str(self.request_id),
            snapshotId=str(self.snapshot_id),
            goalId=str(self.goal_id),
            dagRevision=self.dag_revision,
            nodeId=str(self.node_id),
            assignmentId=str(self.assignment_id),
            attempt=self.attempt,
            activityId=str(self.activity_id),
            profileId=str(self.profile_id),
            profileRevision=self.profile_revision,
            resolvedEngine=self.resolved_engine,
            resolvedModel=self.resolved_model,
            resolvedReasoning=self.resolved_reasoning,
            rolePromptDigestHex=self.role_prompt_digest_hex,
            worktreePath=self.worktree_path,
            leaseId=str(self.lease_id),
            leaseRevision=self.lease_revision,
            leaseExpiresAtMs=self.lease_expires_at_ms,
            mcpGrant=mcp_grant,
            permissions=self.permissions.to_dict(),
            timeouts=self.timeouts.to_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionSnapshotOutcomeDto:
    """Immutable committed or rejected execution snapshot result."""

    committed: bool
    rejection_code: str | None
    detail: str | None
    record: LaunchLedgerRecordDto | None

    def to_dict(self) -> ExecutionSnapshotOutcomeResponseDict:
        """Serialize a committed or rejected snapshot result.

        Args:
            None.
        Return:
            Complete execution snapshot outcome dictionary.
        """
        record = self.record.to_dict() if self.record is not None else None
        result = ExecutionSnapshotOutcomeResponseDict(
            committed=self.committed,
            rejectionCode=self.rejection_code,
            detail=self.detail,
            record=record,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionSnapshotQueryDto:
    """Immutable readback for one exact execution attempt."""

    workspace_id: UUID
    goal_id: UUID
    dag_revision: DagRevision
    node_id: UUID
    assignment_id: UUID
    attempt: WorkAttempt
    record: LaunchLedgerRecordDto | None

    def to_dict(self) -> ExecutionSnapshotQueryResponseDict:
        """Serialize the exact execution attempt readback.

        Args:
            None.
        Return:
            Complete execution snapshot query dictionary.
        """
        record = self.record.to_dict() if self.record is not None else None
        result = ExecutionSnapshotQueryResponseDict(
            workspaceId=str(self.workspace_id),
            goalId=str(self.goal_id),
            dagRevision=self.dag_revision,
            nodeId=str(self.node_id),
            assignmentId=str(self.assignment_id),
            attempt=self.attempt,
            record=record,
        )
        return result
