"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.types.autonomy.autonomy_snapshot_types import (
    LaunchLedgerRecordDict,
)
from app.orchestration.application.inner_dto.types.orchestration_execution_types import (
    ExecutionPermissionsDict,
    ExecutionPreferenceDict,
    ExecutionPreferenceResultDict,
    ExecutionTimeoutsDict,
    McpGrantDict,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import (
    SwarmBoardMessageDict,
    SwarmMemberDict,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    PositiveInt64,
    SignedInt32,
    UnixTimestampMs,
    WorkAttempt,
)
from app.orchestration.schema.types.orchestration_types import UInt64


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
