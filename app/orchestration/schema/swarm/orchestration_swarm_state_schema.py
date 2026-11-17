"""Strict schemas for reusable source-shaped Orchestration Swarm records."""

from typing import Annotated

from pydantic import Field

from app.orchestration.schema.execution.orchestration_execution_schema import (
    PrincipalIdentitySchema,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt32, UInt64
from app.orchestration.schema.types.swarm_types import (
    NonNilCanonicalSwarmUUID,
    NonZeroDigestHex,
    SwarmDagRevision,
    SwarmDoorbellReason,
    SwarmMemberState,
    SwarmPanelSeatKind,
    SwarmRevision,
    SwarmRoleKind,
    SwarmRunModeKind,
    SwarmRunState,
    SwarmUInt8,
    SwarmUUID,
    SwarmVerdictOutcome,
    SwarmWorkspaceMode,
)
from app.shared.base_schema import StrictSchemaModel


class DagNodeHybridTargetSchema(StrictSchemaModel):
    """Coordinates binding a Swarm run to its Forge DAG node."""

    goal_id: Annotated[
        NonNilCanonicalSwarmUUID,
        Field(alias="goalId", description="Non-nil Goal UUID."),
    ]
    dag_revision: Annotated[
        SwarmDagRevision, Field(alias="dagRevision", description="Positive DAG revision.")
    ]
    node_id: Annotated[
        NonNilCanonicalSwarmUUID,
        Field(alias="nodeId", description="Non-nil DAG node UUID."),
    ]
    declared_write_manifest_blake3_hex: Annotated[
        NonZeroDigestHex,
        Field(
            alias="declaredWriteManifestBlake3Hex", description="Declared-write manifest digest."
        ),
    ]


class SwarmRunModeSchema(StrictSchemaModel):
    """Canonical standalone or DAG-node hybrid run mode."""

    kind: Annotated[SwarmRunModeKind, Field(description="Canonical Swarm run mode.")]
    hybrid_target: Annotated[
        DagNodeHybridTargetSchema | None,
        Field(alias="hybridTarget", description="DAG-node hybrid target or null."),
    ]


class SwarmRunSchema(StrictSchemaModel):
    """Canonical durable Swarm run projection."""

    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    workspace_id: Annotated[SwarmUUID, Field(alias="workspaceId", description="Workspace UUID.")]
    title: Annotated[str, Field(description="Swarm run title.")]
    mode: Annotated[SwarmRunModeSchema, Field(description="Standalone or hybrid run mode.")]
    state: Annotated[SwarmRunState, Field(description="Canonical durable run state.")]
    max_members: Annotated[UInt32, Field(alias="maxMembers", description="Member capacity.")]
    max_spawn_depth: Annotated[
        SwarmUInt8,
        Field(alias="maxSpawnDepth", description="Maximum spawn depth."),
    ]
    max_total_turns: Annotated[
        UInt64,
        Field(alias="maxTotalTurns", description="Total turn budget."),
    ]
    total_turns_used: Annotated[
        UInt64,
        Field(alias="totalTurnsUsed", description="Turns consumed so far."),
    ]
    required_verifier_quorum: Annotated[
        UInt32,
        Field(alias="requiredVerifierQuorum", description="Required verifier quorum."),
    ]
    allow_worker_all_mention: Annotated[
        bool,
        Field(
            alias="allowWorkerAllMention", description="Whether workers may mention all members."
        ),
    ]
    baseline_commit_oid: Annotated[
        str,
        Field(alias="baselineCommitOid", description="Baseline Git commit OID."),
    ]
    baseline_tree_blake3_hex: Annotated[
        str,
        Field(alias="baselineTreeBlake3Hex", description="Baseline tree BLAKE3 digest."),
    ]
    converged_commit_oid: Annotated[
        str | None,
        Field(alias="convergedCommitOid", description="Converged commit OID or null."),
    ]
    converged_tree_blake3_hex: Annotated[
        str | None,
        Field(alias="convergedTreeBlake3Hex", description="Converged tree digest or null."),
    ]
    converged_diff_digest_hex: Annotated[
        str | None,
        Field(alias="convergedDiffDigestHex", description="Converged diff digest or null."),
    ]
    stall_nudge_count: Annotated[
        UInt32,
        Field(alias="stallNudgeCount", description="Stall nudges recorded."),
    ]
    settlement_request_id: Annotated[
        SwarmUUID | None,
        Field(alias="settlementRequestId", description="Settlement request UUID or null."),
    ]
    revision: Annotated[SwarmRevision, Field(description="Positive Swarm run revision.")]
    created_at_ms: Annotated[
        Int64,
        Field(alias="createdAtMs", description="Creation time in milliseconds."),
    ]
    updated_at_ms: Annotated[
        Int64,
        Field(alias="updatedAtMs", description="Update time in milliseconds."),
    ]
    replayed: Annotated[bool, Field(description="Whether the source replayed the request.")]


class SwarmChannelSchema(StrictSchemaModel):
    """Canonical Swarm channel projection."""

    channel_id: Annotated[SwarmUUID, Field(alias="channelId", description="Channel UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    workspace_id: Annotated[SwarmUUID, Field(alias="workspaceId", description="Workspace UUID.")]
    name: Annotated[str, Field(description="Channel name.")]
    purpose: Annotated[str | None, Field(description="Purpose or null.")]
    created_by_member_id: Annotated[
        SwarmUUID | None,
        Field(alias="createdByMemberId", description="Creator member UUID or null."),
    ]
    created_at_ms: Annotated[
        Int64,
        Field(alias="createdAtMs", description="Creation time in milliseconds."),
    ]


class SwarmChannelSubscriptionSchema(StrictSchemaModel):
    """Member-to-channel subscription edge."""

    channel_id: Annotated[SwarmUUID, Field(alias="channelId", description="Channel UUID.")]
    member_id: Annotated[SwarmUUID, Field(alias="memberId", description="Member UUID.")]


class SwarmDoorbellSchema(StrictSchemaModel):
    """Pending Swarm wakeup doorbell."""

    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    target_member_id: Annotated[
        SwarmUUID,
        Field(alias="targetMemberId", description="Target member UUID."),
    ]
    sequence: Annotated[UInt64, Field(description="Doorbell sequence.")]
    reason: Annotated[SwarmDoorbellReason, Field(description="Canonical doorbell reason.")]
    enqueued_at_ms: Annotated[
        Int64,
        Field(alias="enqueuedAtMs", description="Enqueue time in milliseconds."),
    ]


class SwarmMemberIdentitySchema(StrictSchemaModel):
    """Three-axis profile, participant and principal identity for a member."""

    profile_id: Annotated[SwarmUUID, Field(alias="profileId", description="Profile UUID.")]
    participant_id: Annotated[
        SwarmUUID,
        Field(alias="participantId", description="Participant UUID."),
    ]
    principal: Annotated[PrincipalIdentitySchema, Field(description="Authenticated principal.")]


class SwarmMemberSchema(StrictSchemaModel):
    """Canonical durable Swarm member projection."""

    member_id: Annotated[SwarmUUID, Field(alias="memberId", description="Member UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    workspace_id: Annotated[SwarmUUID, Field(alias="workspaceId", description="Workspace UUID.")]
    roster_name: Annotated[str, Field(alias="rosterName", description="Roster display name.")]
    role_kind: Annotated[
        SwarmRoleKind, Field(alias="roleKind", description="Canonical member role.")
    ]
    parent_member_id: Annotated[
        SwarmUUID | None,
        Field(alias="parentMemberId", description="Parent member UUID or null."),
    ]
    spawn_depth: Annotated[SwarmUInt8, Field(alias="spawnDepth", description="Spawn depth.")]
    workspace_mode: Annotated[
        SwarmWorkspaceMode,
        Field(alias="workspaceMode", description="Canonical workspace mode."),
    ]
    worktree_path: Annotated[
        str | None,
        Field(alias="worktreePath", description="Worktree path or null."),
    ]
    member_state: Annotated[
        SwarmMemberState,
        Field(alias="memberState", description="Canonical member state."),
    ]
    identity: Annotated[SwarmMemberIdentitySchema, Field(description="Three-axis member identity.")]
    committed_seen_seq: Annotated[
        UInt64,
        Field(alias="committedSeenSeq", description="Highest committed board sequence seen."),
    ]
    inflight_target_seq: Annotated[
        UInt64,
        Field(alias="inflightTargetSeq", description="In-flight board target sequence."),
    ]
    active_snapshot_id: Annotated[
        SwarmUUID | None,
        Field(alias="activeSnapshotId", description="Active execution snapshot UUID or null."),
    ]
    attempt_epoch: Annotated[
        UInt64, Field(alias="attemptEpoch", description="Member attempt epoch.")
    ]
    turns_used: Annotated[UInt64, Field(alias="turnsUsed", description="Turns consumed by member.")]
    ping_pong_peer_id: Annotated[
        SwarmUUID | None,
        Field(alias="pingPongPeerId", description="Ping-pong peer UUID or null."),
    ]
    ping_pong_streak: Annotated[
        UInt32,
        Field(alias="pingPongStreak", description="Current ping-pong streak."),
    ]
    last_output_commit_oid: Annotated[
        str | None,
        Field(alias="lastOutputCommitOid", description="Last output commit OID or null."),
    ]
    last_output_tree_blake3_hex: Annotated[
        str | None,
        Field(alias="lastOutputTreeBlake3Hex", description="Last output tree digest or null."),
    ]
    created_at_ms: Annotated[
        Int64,
        Field(alias="createdAtMs", description="Creation time in milliseconds."),
    ]
    updated_at_ms: Annotated[
        Int64,
        Field(alias="updatedAtMs", description="Update time in milliseconds."),
    ]


class SwarmBoardMessageSchema(StrictSchemaModel):
    """Canonical incremental Swarm board message."""

    message_id: Annotated[SwarmUUID, Field(alias="messageId", description="Message UUID.")]
    workspace_id: Annotated[SwarmUUID, Field(alias="workspaceId", description="Workspace UUID.")]
    sequence: Annotated[UInt64, Field(description="Monotonic board sequence.")]
    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    channel_id: Annotated[SwarmUUID, Field(alias="channelId", description="Channel UUID.")]
    channel_name: Annotated[str, Field(alias="channelName", description="Channel name.")]
    author_member_id: Annotated[
        SwarmUUID | None,
        Field(alias="authorMemberId", description="Author member UUID or null for system."),
    ]
    author_roster_name: Annotated[
        str,
        Field(alias="authorRosterName", description="Author roster name or System."),
    ]
    author_epoch: Annotated[
        UInt64 | None,
        Field(alias="authorEpoch", description="Author attempt epoch or null."),
    ]
    body: Annotated[str, Field(description="Board message body.")]
    submitted_at_ms: Annotated[
        Int64,
        Field(alias="submittedAtMs", description="Submission time in milliseconds."),
    ]


class SwarmPanelSeatSchema(StrictSchemaModel):
    """Seat projection in a Swarm verification panel."""

    member_id: Annotated[SwarmUUID, Field(alias="memberId", description="Member UUID.")]
    seat_kind: Annotated[
        SwarmPanelSeatKind, Field(alias="seatKind", description="Canonical seat kind.")
    ]
    assigned_at_ms: Annotated[
        Int64,
        Field(alias="assignedAtMs", description="Assignment time in milliseconds."),
    ]


class SwarmVerificationPanelSchema(StrictSchemaModel):
    """Canonical adversarial verifier panel projection."""

    panel_id: Annotated[SwarmUUID, Field(alias="panelId", description="Panel UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    workspace_id: Annotated[SwarmUUID, Field(alias="workspaceId", description="Workspace UUID.")]
    required_quorum: Annotated[
        UInt32,
        Field(alias="requiredQuorum", description="Required accepted verdict count."),
    ]
    auto_created: Annotated[
        bool, Field(alias="autoCreated", description="Whether source auto-created panel.")
    ]
    seats: Annotated[list[SwarmPanelSeatSchema], Field(description="Author and verifier seats.")]
    created_at_ms: Annotated[
        Int64,
        Field(alias="createdAtMs", description="Creation time in milliseconds."),
    ]
    replayed: Annotated[bool, Field(description="Whether source replayed panel creation.")]


class SwarmVerdictSchema(StrictSchemaModel):
    """Canonical recorded Swarm verifier verdict."""

    verdict_id: Annotated[SwarmUUID, Field(alias="verdictId", description="Verdict UUID.")]
    request_id: Annotated[SwarmUUID, Field(alias="requestId", description="Request UUID.")]
    panel_id: Annotated[SwarmUUID, Field(alias="panelId", description="Panel UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    verifier_member_id: Annotated[
        SwarmUUID,
        Field(alias="verifierMemberId", description="Verifier member UUID."),
    ]
    outcome: Annotated[SwarmVerdictOutcome, Field(description="Canonical verdict outcome.")]
    reviewed_diff_digest_hex: Annotated[
        str,
        Field(alias="reviewedDiffDigestHex", description="Reviewed diff digest."),
    ]
    rationale: Annotated[str, Field(description="Verifier rationale.")]
    recorded_at_ms: Annotated[
        Int64,
        Field(alias="recordedAtMs", description="Recording time in milliseconds."),
    ]
    replayed: Annotated[bool, Field(description="Whether source replayed verdict creation.")]


class SwarmConvergenceGateSchema(StrictSchemaModel):
    """Verified quorum proof attached to a converged Swarm run."""

    panel_id: Annotated[SwarmUUID, Field(alias="panelId", description="Panel UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    converged_diff_digest_hex: Annotated[
        str,
        Field(alias="convergedDiffDigestHex", description="Converged diff digest."),
    ]
    required_quorum: Annotated[
        UInt32,
        Field(alias="requiredQuorum", description="Required accepted verdict count."),
    ]
    accepted_verdicts: Annotated[
        list[SwarmVerdictSchema],
        Field(alias="acceptedVerdicts", description="Accepted verifier verdicts."),
    ]
