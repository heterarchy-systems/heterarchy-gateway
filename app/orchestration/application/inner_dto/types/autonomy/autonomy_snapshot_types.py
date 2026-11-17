"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.types.orchestration_execution_types import (
    ExecutionPermissionsDict,
    ExecutionTimeoutsDict,
    McpGrantDict,
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
