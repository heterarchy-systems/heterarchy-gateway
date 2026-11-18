"""Immutable DTOs for reusable Orchestration Swarm wire records."""

from dataclasses import dataclass
from uuid import UUID

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    PrincipalIdentityDto,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import (
    DagNodeHybridTargetDict,
    DagNodeHybridTargetRequestDict,
    SwarmBoardMessageDict,
    SwarmChannelDict,
    SwarmChannelSubscriptionDict,
    SwarmConvergenceGateDict,
    SwarmDoorbellDict,
    SwarmMemberDict,
    SwarmMemberIdentityDict,
    SwarmMemberIdentityRequestDict,
    SwarmPanelSeatDict,
    SwarmRunDict,
    SwarmRunModeDict,
    SwarmRunModeRequestDict,
    SwarmVerdictDict,
    SwarmVerificationPanelDict,
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


@dataclass(frozen=True, slots=True, kw_only=True)
class DagNodeHybridTargetDto:
    """Immutable DAG-node hybrid target record."""

    goal_id: UUID
    dag_revision: SwarmDagRevision
    node_id: UUID
    declared_write_manifest_blake3_hex: str

    def to_dict(self) -> DagNodeHybridTargetDict:
        """Serialize the result target with typed UUID fields.

        Args:
            None.
        Return:
            Complete typed DAG-node hybrid target.
        """
        result = DagNodeHybridTargetDict(
            goalId=self.goal_id,
            dagRevision=self.dag_revision,
            nodeId=self.node_id,
            declaredWriteManifestBlake3Hex=self.declared_write_manifest_blake3_hex,
        )
        return result

    def to_request_dict(self) -> DagNodeHybridTargetRequestDict:
        """Serialize the target to primitive JSON request values.

        Args:
            None.
        Return:
            Complete request-compatible target dictionary.
        """
        result = DagNodeHybridTargetRequestDict(
            goalId=str(self.goal_id),
            dagRevision=self.dag_revision,
            nodeId=str(self.node_id),
            declaredWriteManifestBlake3Hex=self.declared_write_manifest_blake3_hex,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmRunModeDto:
    """Immutable canonical Swarm run mode record."""

    kind: SwarmRunModeEnum
    hybrid_target: DagNodeHybridTargetDto | None

    def to_dict(self) -> SwarmRunModeDict:
        """Serialize canonical mode while retaining typed nested UUIDs.

        Args:
            None.
        Return:
            Complete typed Swarm run mode result.
        """
        target = self.hybrid_target.to_dict() if self.hybrid_target is not None else None
        result = SwarmRunModeDict(kind=self.kind, hybridTarget=target)
        return result

    def to_request_dict(self) -> SwarmRunModeRequestDict:
        """Serialize canonical mode to primitive request JSON values.

        Args:
            None.
        Return:
            Complete request-compatible Swarm run mode.
        """
        if self.hybrid_target is None:
            result = SwarmRunModeRequestDict(kind=self.kind.value)
        else:
            result = SwarmRunModeRequestDict(
                kind=self.kind.value,
                hybridTarget=self.hybrid_target.to_request_dict(),
            )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmRunDto:
    """Immutable canonical Swarm run response record."""

    swarm_run_id: UUID
    workspace_id: UUID
    title: str
    mode: SwarmRunModeDto
    state: SwarmRunStateEnum
    max_members: UInt32
    max_spawn_depth: SwarmUInt8
    max_total_turns: UInt64
    total_turns_used: UInt64
    required_verifier_quorum: UInt32
    allow_worker_all_mention: bool
    baseline_commit_oid: str
    baseline_tree_blake3_hex: str
    converged_commit_oid: str | None
    converged_tree_blake3_hex: str | None
    converged_diff_digest_hex: str | None
    stall_nudge_count: UInt32
    settlement_request_id: UUID | None
    revision: SwarmRevision
    created_at_ms: Int64
    updated_at_ms: Int64
    replayed: bool

    def to_dict(self) -> SwarmRunDict:
        """Serialize the run with typed nested UUID and enum values.

        Args:
            None.
        Return:
            Complete typed Swarm run result.
        """
        result = SwarmRunDict(
            swarmRunId=self.swarm_run_id,
            workspaceId=self.workspace_id,
            title=self.title,
            mode=self.mode.to_dict(),
            state=self.state,
            maxMembers=self.max_members,
            maxSpawnDepth=self.max_spawn_depth,
            maxTotalTurns=self.max_total_turns,
            totalTurnsUsed=self.total_turns_used,
            requiredVerifierQuorum=self.required_verifier_quorum,
            allowWorkerAllMention=self.allow_worker_all_mention,
            baselineCommitOid=self.baseline_commit_oid,
            baselineTreeBlake3Hex=self.baseline_tree_blake3_hex,
            convergedCommitOid=self.converged_commit_oid,
            convergedTreeBlake3Hex=self.converged_tree_blake3_hex,
            convergedDiffDigestHex=self.converged_diff_digest_hex,
            stallNudgeCount=self.stall_nudge_count,
            settlementRequestId=self.settlement_request_id,
            revision=self.revision,
            createdAtMs=self.created_at_ms,
            updatedAtMs=self.updated_at_ms,
            replayed=self.replayed,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmChannelDto:
    """Immutable canonical Swarm channel record."""

    channel_id: UUID
    swarm_run_id: UUID
    workspace_id: UUID
    name: str
    purpose: str | None
    created_by_member_id: UUID | None
    created_at_ms: Int64

    def to_dict(self) -> SwarmChannelDict:
        """Serialize the channel with typed UUID values.

        Args:
            None.
        Return:
            Complete typed Swarm channel result.
        """
        result = SwarmChannelDict(
            channelId=self.channel_id,
            swarmRunId=self.swarm_run_id,
            workspaceId=self.workspace_id,
            name=self.name,
            purpose=self.purpose,
            createdByMemberId=self.created_by_member_id,
            createdAtMs=self.created_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmChannelSubscriptionDto:
    """Immutable Swarm member-to-channel subscription record."""

    channel_id: UUID
    member_id: UUID

    def to_dict(self) -> SwarmChannelSubscriptionDict:
        """Serialize the subscription with typed UUID values.

        Args:
            None.
        Return:
            Complete typed subscription edge.
        """
        result = SwarmChannelSubscriptionDict(
            channelId=self.channel_id,
            memberId=self.member_id,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmDoorbellDto:
    """Immutable pending wakeup doorbell record."""

    swarm_run_id: UUID
    target_member_id: UUID
    sequence: UInt64
    reason: SwarmDoorbellReasonEnum
    enqueued_at_ms: Int64

    def to_dict(self) -> SwarmDoorbellDict:
        """Serialize the doorbell with typed UUID and enum values.

        Args:
            None.
        Return:
            Complete typed doorbell result.
        """
        result = SwarmDoorbellDict(
            swarmRunId=self.swarm_run_id,
            targetMemberId=self.target_member_id,
            sequence=self.sequence,
            reason=self.reason,
            enqueuedAtMs=self.enqueued_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmMemberIdentityDto:
    """Immutable three-axis identity attached to a Swarm member."""

    profile_id: UUID
    participant_id: UUID
    principal: PrincipalIdentityDto

    def to_dict(self) -> SwarmMemberIdentityDict:
        """Serialize identity with typed UUID and principal enum values.

        Args:
            None.
        Return:
            Complete typed Swarm member identity.
        """
        result = SwarmMemberIdentityDict(
            profileId=self.profile_id,
            participantId=self.participant_id,
            principal=self.principal.to_schema_dict(),
        )
        return result

    def to_request_dict(self) -> SwarmMemberIdentityRequestDict:
        """Serialize identity to primitive request JSON values.

        Args:
            None.
        Return:
            Complete request-compatible identity dictionary.
        """
        result = SwarmMemberIdentityRequestDict(
            profileId=str(self.profile_id),
            participantId=str(self.participant_id),
            principal=self.principal.to_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmMemberDto:
    """Immutable canonical Swarm member response record."""

    member_id: UUID
    swarm_run_id: UUID
    workspace_id: UUID
    roster_name: str
    role_kind: SwarmRoleKindEnum
    parent_member_id: UUID | None
    spawn_depth: SwarmUInt8
    workspace_mode: SwarmWorkspaceModeEnum
    worktree_path: str | None
    member_state: SwarmMemberStateEnum
    identity: SwarmMemberIdentityDto
    committed_seen_seq: UInt64
    inflight_target_seq: UInt64
    active_snapshot_id: UUID | None
    attempt_epoch: UInt64
    turns_used: UInt64
    ping_pong_peer_id: UUID | None
    ping_pong_streak: UInt32
    last_output_commit_oid: str | None
    last_output_tree_blake3_hex: str | None
    created_at_ms: Int64
    updated_at_ms: Int64

    def to_dict(self) -> SwarmMemberDict:
        """Serialize the member with typed UUID and enum values.

        Args:
            None.
        Return:
            Complete typed Swarm member result.
        """
        result = SwarmMemberDict(
            memberId=self.member_id,
            swarmRunId=self.swarm_run_id,
            workspaceId=self.workspace_id,
            rosterName=self.roster_name,
            roleKind=self.role_kind,
            parentMemberId=self.parent_member_id,
            spawnDepth=self.spawn_depth,
            workspaceMode=self.workspace_mode,
            worktreePath=self.worktree_path,
            memberState=self.member_state,
            identity=self.identity.to_dict(),
            committedSeenSeq=self.committed_seen_seq,
            inflightTargetSeq=self.inflight_target_seq,
            activeSnapshotId=self.active_snapshot_id,
            attemptEpoch=self.attempt_epoch,
            turnsUsed=self.turns_used,
            pingPongPeerId=self.ping_pong_peer_id,
            pingPongStreak=self.ping_pong_streak,
            lastOutputCommitOid=self.last_output_commit_oid,
            lastOutputTreeBlake3Hex=self.last_output_tree_blake3_hex,
            createdAtMs=self.created_at_ms,
            updatedAtMs=self.updated_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmBoardMessageDto:
    """Immutable canonical Swarm board message record."""

    message_id: UUID
    workspace_id: UUID
    sequence: UInt64
    swarm_run_id: UUID
    channel_id: UUID
    channel_name: str
    author_member_id: UUID | None
    author_roster_name: str
    author_epoch: UInt64 | None
    body: str
    submitted_at_ms: Int64

    def to_dict(self) -> SwarmBoardMessageDict:
        """Serialize the board message with typed UUID values.

        Args:
            None.
        Return:
            Complete typed Swarm board message.
        """
        result = SwarmBoardMessageDict(
            messageId=self.message_id,
            workspaceId=self.workspace_id,
            sequence=self.sequence,
            swarmRunId=self.swarm_run_id,
            channelId=self.channel_id,
            channelName=self.channel_name,
            authorMemberId=self.author_member_id,
            authorRosterName=self.author_roster_name,
            authorEpoch=self.author_epoch,
            body=self.body,
            submittedAtMs=self.submitted_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmPanelSeatDto:
    """Immutable verification panel seat record."""

    member_id: UUID
    seat_kind: SwarmPanelSeatKindEnum
    assigned_at_ms: Int64

    def to_dict(self) -> SwarmPanelSeatDict:
        """Serialize the panel seat with typed UUID and enum values.

        Args:
            None.
        Return:
            Complete typed panel seat.
        """
        result = SwarmPanelSeatDict(
            memberId=self.member_id,
            seatKind=self.seat_kind,
            assignedAtMs=self.assigned_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmVerificationPanelDto:
    """Immutable verification panel response record."""

    panel_id: UUID
    swarm_run_id: UUID
    workspace_id: UUID
    required_quorum: UInt32
    auto_created: bool
    seats: tuple[SwarmPanelSeatDto, ...]
    created_at_ms: Int64
    replayed: bool

    def to_dict(self) -> SwarmVerificationPanelDict:
        """Serialize the panel with typed UUID and nested seat values.

        Args:
            None.
        Return:
            Complete typed verification panel.
        """
        result = SwarmVerificationPanelDict(
            panelId=self.panel_id,
            swarmRunId=self.swarm_run_id,
            workspaceId=self.workspace_id,
            requiredQuorum=self.required_quorum,
            autoCreated=self.auto_created,
            seats=[seat.to_dict() for seat in self.seats],
            createdAtMs=self.created_at_ms,
            replayed=self.replayed,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmVerdictDto:
    """Immutable recorded Swarm verifier verdict."""

    verdict_id: UUID
    request_id: UUID
    panel_id: UUID
    swarm_run_id: UUID
    verifier_member_id: UUID
    outcome: SwarmVerdictOutcomeEnum
    reviewed_diff_digest_hex: str
    rationale: str
    recorded_at_ms: Int64
    replayed: bool

    def to_dict(self) -> SwarmVerdictDict:
        """Serialize the verdict with typed UUID and outcome values.

        Args:
            None.
        Return:
            Complete typed Swarm verdict.
        """
        result = SwarmVerdictDict(
            verdictId=self.verdict_id,
            requestId=self.request_id,
            panelId=self.panel_id,
            swarmRunId=self.swarm_run_id,
            verifierMemberId=self.verifier_member_id,
            outcome=self.outcome,
            reviewedDiffDigestHex=self.reviewed_diff_digest_hex,
            rationale=self.rationale,
            recordedAtMs=self.recorded_at_ms,
            replayed=self.replayed,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmConvergenceGateDto:
    """Immutable verified quorum proof attached to convergence."""

    panel_id: UUID
    swarm_run_id: UUID
    converged_diff_digest_hex: str
    required_quorum: UInt32
    accepted_verdicts: tuple[SwarmVerdictDto, ...]

    def to_dict(self) -> SwarmConvergenceGateDict:
        """Serialize the quorum gate with typed nested verdict values.

        Args:
            None.
        Return:
            Complete typed Swarm convergence gate.
        """
        result = SwarmConvergenceGateDict(
            panelId=self.panel_id,
            swarmRunId=self.swarm_run_id,
            convergedDiffDigestHex=self.converged_diff_digest_hex,
            requiredQuorum=self.required_quorum,
            acceptedVerdicts=[verdict.to_dict() for verdict in self.accepted_verdicts],
        )
        return result
