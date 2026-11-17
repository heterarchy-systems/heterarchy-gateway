"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing import NotRequired
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.types.orchestration_execution_types import (
    PrincipalIdentityDict,
    PrincipalIdentityResultDict,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt32, UInt64
from app.orchestration.schema.types.swarm_types import SwarmDagRevision, SwarmRevision, SwarmUInt8
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmDoorbellReasonEnum,
    SwarmMemberStateEnum,
    SwarmPanelSeatKindEnum,
    SwarmRoleKindEnum,
    SwarmRunModeEnum,
    SwarmRunStateEnum,
    SwarmVerdictOutcomeEnum,
    SwarmWorkspaceModeEnum,
)


class DagNodeHybridTargetDict(TypedDict, total=True, closed=True):
    """Typed result fields for a DAG-node hybrid target."""

    goalId: UUID
    dagRevision: SwarmDagRevision
    nodeId: UUID
    declaredWriteManifestBlake3Hex: str


class DagNodeHybridTargetRequestDict(TypedDict, total=True, closed=True):
    """Primitive JSON fields for a DAG-node hybrid request target."""

    goalId: str
    dagRevision: SwarmDagRevision
    nodeId: str
    declaredWriteManifestBlake3Hex: str


class SwarmRunModeDict(TypedDict, total=True, closed=True):
    """Typed result fields for canonical Swarm run mode."""

    kind: SwarmRunModeEnum
    hybridTarget: DagNodeHybridTargetDict | None


class SwarmRunModeRequestDict(TypedDict, total=True, closed=True):
    """Primitive JSON fields for a Swarm run mode request."""

    kind: str
    hybridTarget: NotRequired[DagNodeHybridTargetRequestDict | None]


class SwarmRunDict(TypedDict, total=True, closed=True):
    """Typed canonical Swarm run projection."""

    swarmRunId: UUID
    workspaceId: UUID
    title: str
    mode: SwarmRunModeDict
    state: SwarmRunStateEnum
    maxMembers: UInt32
    maxSpawnDepth: SwarmUInt8
    maxTotalTurns: UInt64
    totalTurnsUsed: UInt64
    requiredVerifierQuorum: UInt32
    allowWorkerAllMention: bool
    baselineCommitOid: str
    baselineTreeBlake3Hex: str
    convergedCommitOid: str | None
    convergedTreeBlake3Hex: str | None
    convergedDiffDigestHex: str | None
    stallNudgeCount: UInt32
    settlementRequestId: UUID | None
    revision: SwarmRevision
    createdAtMs: Int64
    updatedAtMs: Int64
    replayed: bool


class SwarmChannelDict(TypedDict, total=True, closed=True):
    """Typed canonical Swarm channel projection."""

    channelId: UUID
    swarmRunId: UUID
    workspaceId: UUID
    name: str
    purpose: str | None
    createdByMemberId: UUID | None
    createdAtMs: Int64


class SwarmChannelSubscriptionDict(TypedDict, total=True, closed=True):
    """Typed member-to-channel subscription edge."""

    channelId: UUID
    memberId: UUID


class SwarmDoorbellDict(TypedDict, total=True, closed=True):
    """Typed pending Swarm wakeup doorbell."""

    swarmRunId: UUID
    targetMemberId: UUID
    sequence: UInt64
    reason: SwarmDoorbellReasonEnum
    enqueuedAtMs: Int64


class SwarmMemberIdentityDict(TypedDict, total=True, closed=True):
    """Typed three-axis identity projection for a Swarm member."""

    profileId: UUID
    participantId: UUID
    principal: PrincipalIdentityResultDict


class SwarmMemberIdentityRequestDict(TypedDict, total=True, closed=True):
    """Primitive request fields for a member identity."""

    profileId: str
    participantId: str
    principal: PrincipalIdentityDict


class SwarmMemberDict(TypedDict, total=True, closed=True):
    """Typed canonical Swarm member projection."""

    memberId: UUID
    swarmRunId: UUID
    workspaceId: UUID
    rosterName: str
    roleKind: SwarmRoleKindEnum
    parentMemberId: UUID | None
    spawnDepth: SwarmUInt8
    workspaceMode: SwarmWorkspaceModeEnum
    worktreePath: str | None
    memberState: SwarmMemberStateEnum
    identity: SwarmMemberIdentityDict
    committedSeenSeq: UInt64
    inflightTargetSeq: UInt64
    activeSnapshotId: UUID | None
    attemptEpoch: UInt64
    turnsUsed: UInt64
    pingPongPeerId: UUID | None
    pingPongStreak: UInt32
    lastOutputCommitOid: str | None
    lastOutputTreeBlake3Hex: str | None
    createdAtMs: Int64
    updatedAtMs: Int64


class SwarmBoardMessageDict(TypedDict, total=True, closed=True):
    """Typed canonical Swarm board message projection."""

    messageId: UUID
    workspaceId: UUID
    sequence: UInt64
    swarmRunId: UUID
    channelId: UUID
    channelName: str
    authorMemberId: UUID | None
    authorRosterName: str
    authorEpoch: UInt64 | None
    body: str
    submittedAtMs: Int64


class SwarmPanelSeatDict(TypedDict, total=True, closed=True):
    """Typed verification panel seat projection."""

    memberId: UUID
    seatKind: SwarmPanelSeatKindEnum
    assignedAtMs: Int64


class SwarmVerificationPanelDict(TypedDict, total=True, closed=True):
    """Typed verification panel projection."""

    panelId: UUID
    swarmRunId: UUID
    workspaceId: UUID
    requiredQuorum: UInt32
    autoCreated: bool
    seats: list[SwarmPanelSeatDict]
    createdAtMs: Int64
    replayed: bool


class SwarmVerdictDict(TypedDict, total=True, closed=True):
    """Typed immutable verifier verdict projection."""

    verdictId: UUID
    requestId: UUID
    panelId: UUID
    swarmRunId: UUID
    verifierMemberId: UUID
    outcome: SwarmVerdictOutcomeEnum
    reviewedDiffDigestHex: str
    rationale: str
    recordedAtMs: Int64
    replayed: bool


class SwarmConvergenceGateDict(TypedDict, total=True, closed=True):
    """Typed verifier quorum proof attached to convergence."""

    panelId: UUID
    swarmRunId: UUID
    convergedDiffDigestHex: str
    requiredQuorum: UInt32
    acceptedVerdicts: list[SwarmVerdictDict]
