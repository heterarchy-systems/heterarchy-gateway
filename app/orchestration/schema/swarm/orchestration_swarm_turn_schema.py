"""Strict request and response contracts for Native Swarm member turns."""

from typing import Annotated, Self

from pydantic import Field, model_validator

from app.orchestration.schema.autonomy.orchestration_autonomy_snapshot_schema import (
    LaunchLedgerRecordSchema,
)
from app.orchestration.schema.execution.orchestration_execution_schema import (
    ExecutionPermissionsSchema,
    ExecutionPreferenceSchema,
    ExecutionTimeoutsSchema,
    McpGrantSchema,
)
from app.orchestration.schema.swarm.orchestration_swarm_state_schema import (
    SwarmBoardMessageSchema,
    SwarmMemberSchema,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    PositiveInt64,
    SignedInt32,
    UnixTimestampMs,
    WorkAttempt,
)
from app.orchestration.schema.types.orchestration_types import UInt64
from app.orchestration.schema.types.swarm_types import (
    NonNilSwarmUUID,
    NonZeroDigestHex,
    SwarmCommitOid,
    SwarmTurnFailureDispositionInput,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.types.wire_scalar_types import WireUUID


class SwarmMcpGrantRequestSchema(McpGrantSchema):
    """Validate the exact non-nil MCP grant window accepted by Swarm dispatch."""

    token_id: Annotated[
        NonNilSwarmUUID,
        Field(alias="tokenId", description="Canonical non-nil MCP token UUID."),
    ]
    issued_at_ms: Annotated[
        UnixTimestampMs,
        Field(alias="issuedAtMs", description="Grant issue time in milliseconds."),
    ]
    expires_at_ms: Annotated[
        UnixTimestampMs,
        Field(alias="expiresAtMs", description="Grant expiration time in milliseconds."),
    ]

    @model_validator(mode="after")
    def validate_grant_window(self) -> Self:
        """Require a grant that expires after it was issued.

        Args:
            None.
        Return:
            Validated immutable MCP grant request.
        """
        if self.expires_at_ms <= self.issued_at_ms:
            raise ValueError("MCP grant expiration must follow issue time")
        result = self
        return result


class ClaimSwarmWakeupRequest(StrictSchemaModel):
    """Claim the coalesced wakeup batch for one execution snapshot."""

    snapshot_id: Annotated[
        NonNilSwarmUUID,
        Field(alias="snapshotId", description="Canonical non-nil execution snapshot UUID."),
    ]


class CompleteSwarmTurnRequest(StrictSchemaModel):
    """Complete one working turn and optionally provide both output digests."""

    expected_snapshot_id: Annotated[
        NonNilSwarmUUID,
        Field(
            alias="expectedSnapshotId",
            description="Canonical execution snapshot UUID fencing this turn.",
        ),
    ]
    output_commit_oid: Annotated[
        SwarmCommitOid | None,
        Field(alias="outputCommitOid", description="Output commit OID, or null."),
    ]
    output_tree_blake3_hex: Annotated[
        NonZeroDigestHex | None,
        Field(alias="outputTreeBlake3Hex", description="Nonzero output tree digest, or null."),
    ]

    @model_validator(mode="after")
    def validate_output_pair(self) -> Self:
        """Require commit and tree output together as the source client does.

        Args:
            None.
        Return:
            Validated immutable completion request.
        """
        if (self.output_commit_oid is None) != (self.output_tree_blake3_hex is None):
            raise ValueError("Turn output commit and tree digest must be provided together")
        result = self
        return result


class FailSwarmTurnRequest(StrictSchemaModel):
    """Release one working turn with its source-owned failure disposition."""

    expected_snapshot_id: Annotated[
        NonNilSwarmUUID,
        Field(
            alias="expectedSnapshotId",
            description="Canonical execution snapshot UUID fencing this turn.",
        ),
    ]
    disposition: Annotated[
        SwarmTurnFailureDispositionInput,
        Field(description="Source-accepted turn failure disposition."),
    ]
    consume_turn: Annotated[
        bool,
        Field(alias="consumeTurn", description="Whether the failed attempt consumes a turn."),
    ]


class DispatchSwarmTurnRequest(StrictSchemaModel):
    """Dispatch and supervise one queued member turn using frozen execution inputs."""

    snapshot_request_id: Annotated[
        NonNilSwarmUUID,
        Field(alias="snapshotRequestId", description="Canonical snapshot request UUID."),
    ]
    snapshot_id: Annotated[
        NonNilSwarmUUID,
        Field(alias="snapshotId", description="Canonical execution snapshot UUID."),
    ]
    activity_id: Annotated[
        NonNilSwarmUUID,
        Field(alias="activityId", description="Canonical activity UUID."),
    ]
    default_worktree_path: Annotated[
        str,
        Field(alias="defaultWorktreePath", description="Requested default worktree path."),
    ]
    lease_id: Annotated[
        NonNilSwarmUUID,
        Field(alias="leaseId", description="Canonical lease UUID."),
    ]
    lease_revision: Annotated[
        PositiveInt64,
        Field(alias="leaseRevision", description="Positive signed-64-bit lease revision."),
    ]
    lease_expires_at_ms: Annotated[
        UnixTimestampMs,
        Field(alias="leaseExpiresAtMs", description="Lease expiration time in milliseconds."),
    ]
    mcp_grant: Annotated[
        SwarmMcpGrantRequestSchema | None,
        Field(alias="mcpGrant", description="Optional bounded MCP grant metadata."),
    ]
    permissions: Annotated[
        ExecutionPermissionsSchema,
        Field(description="Explicit execution permission flags."),
    ]
    timeouts: Annotated[
        ExecutionTimeoutsSchema,
        Field(description="Positive bounded process supervision timeouts."),
    ]
    dispatched_at_ms: Annotated[
        UnixTimestampMs | None,
        Field(alias="dispatchedAtMs", description="Dispatch timestamp override, or null."),
    ]
    clean_exit_output_commit_oid: Annotated[
        SwarmCommitOid | None,
        Field(
            alias="cleanExitOutputCommitOid", description="Clean-exit output commit OID, or null."
        ),
    ]
    clean_exit_output_tree_blake3_hex: Annotated[
        NonZeroDigestHex | None,
        Field(
            alias="cleanExitOutputTreeBlake3Hex",
            description="Clean-exit nonzero output tree digest, or null.",
        ),
    ]
    forge_session_id: Annotated[
        NonNilSwarmUUID | None,
        Field(alias="forgeSessionId", description="Forge session UUID, or null."),
    ]

    @model_validator(mode="after")
    def validate_dispatch_controls(self) -> Self:
        """Require the source client's worktree and optional-output controls.

        Args:
            None.
        Return:
            Validated immutable dispatch request.
        """
        if not self.default_worktree_path.strip() and self.forge_session_id is None:
            raise ValueError("An empty worktree path requires a Forge session UUID")
        if (self.clean_exit_output_commit_oid is None) != (
            self.clean_exit_output_tree_blake3_hex is None
        ):
            raise ValueError("Clean-exit commit and tree digest must be provided together")
        result = self
        return result


class SwitchSwarmMemberModelRequest(StrictSchemaModel):
    """Rebind a quota-suspended member or update its profile preference."""

    new_profile_id: Annotated[
        NonNilSwarmUUID | None,
        Field(alias="newProfileId", description="Existing active profile UUID, or null."),
    ]
    request_id: Annotated[
        NonNilSwarmUUID | None,
        Field(alias="requestId", description="Profile preference mutation request UUID, or null."),
    ]
    profile_id: Annotated[
        NonNilSwarmUUID | None,
        Field(alias="profileId", description="Target profile UUID, or null."),
    ]
    expected_profile_revision: Annotated[
        PositiveInt64 | None,
        Field(
            alias="expectedProfileRevision",
            description="Expected positive profile revision, or null.",
        ),
    ]
    new_preference: Annotated[
        ExecutionPreferenceSchema | None,
        Field(alias="newPreference", description="New execution preference, or null."),
    ]

    @model_validator(mode="after")
    def validate_switch_target(self) -> Self:
        """Require exactly one source-supported switch target shape.

        Args:
            None.
        Return:
            Validated immutable model-switch request.
        """
        rebind_shape = self.new_profile_id is not None and all(
            value is None
            for value in (
                self.request_id,
                self.profile_id,
                self.expected_profile_revision,
                self.new_preference,
            )
        )
        update_shape = self.new_profile_id is None and all(
            value is not None
            for value in (
                self.request_id,
                self.profile_id,
                self.expected_profile_revision,
                self.new_preference,
            )
        )
        if not (rebind_shape or update_shape):
            raise ValueError("Model switch must match one source-supported target shape")
        result = self
        return result


class SwarmWakeupBatchResponse(StrictSchemaModel):
    """Coalesced wakeup batch returned after claiming a member turn."""

    swarm_run_id: Annotated[
        WireUUID,
        Field(alias="swarmRunId", description="Swarm run UUID bound to this wakeup."),
    ]
    member: Annotated[SwarmMemberSchema, Field(description="Member after claiming the turn.")]
    snapshot_id: Annotated[
        WireUUID,
        Field(alias="snapshotId", description="Fenced execution snapshot UUID."),
    ]
    committed_seen_seq: Annotated[
        UInt64,
        Field(alias="committedSeenSeq", description="Committed board sequence watermark."),
    ]
    inflight_target_seq: Annotated[
        UInt64,
        Field(alias="inflightTargetSeq", description="In-flight board sequence watermark."),
    ]
    messages: Annotated[
        list[SwarmBoardMessageSchema],
        Field(description="Ordered unread messages coalesced into this wakeup."),
    ]
    total_body_bytes: Annotated[
        UInt64,
        Field(alias="totalBodyBytes", description="UTF-8 body bytes included in the batch."),
    ]


class CommittedExecutionSnapshotSchema(StrictSchemaModel):
    """Immutable execution snapshot sealed for this dispatch."""

    snapshot_id: Annotated[WireUUID, Field(alias="snapshotId", description="Snapshot UUID.")]
    workspace_id: Annotated[WireUUID, Field(alias="workspaceId", description="Workspace UUID.")]
    goal_id: Annotated[WireUUID, Field(alias="goalId", description="Goal UUID.")]
    dag_revision: Annotated[DagRevision, Field(alias="dagRevision", description="DAG revision.")]
    node_id: Annotated[WireUUID, Field(alias="nodeId", description="DAG node UUID.")]
    assignment_id: Annotated[
        WireUUID,
        Field(alias="assignmentId", description="Agent assignment UUID."),
    ]
    attempt: Annotated[WorkAttempt, Field(description="Zero-based execution attempt.")]
    activity_id: Annotated[WireUUID, Field(alias="activityId", description="Activity UUID.")]
    profile_id: Annotated[WireUUID, Field(alias="profileId", description="Agent Profile UUID.")]
    profile_revision: Annotated[
        PositiveInt64,
        Field(alias="profileRevision", description="Committed Profile revision."),
    ]
    resolved_engine: Annotated[
        str,
        Field(alias="resolvedEngine", description="Resolved execution engine name."),
    ]
    resolved_model: Annotated[
        str,
        Field(alias="resolvedModel", description="Resolved execution model."),
    ]
    resolved_reasoning: Annotated[
        str | None,
        Field(alias="resolvedReasoning", description="Resolved reasoning mode, or null."),
    ]
    role_prompt_digest_hex: Annotated[
        str | None,
        Field(alias="rolePromptDigestHex", description="Role-prompt digest, or null."),
    ]
    worktree_path: Annotated[
        str,
        Field(alias="worktreePath", description="Committed worktree path."),
    ]
    lease_id: Annotated[WireUUID, Field(alias="leaseId", description="Lease UUID.")]
    lease_revision: Annotated[
        UInt64,
        Field(alias="leaseRevision", description="Committed lease revision."),
    ]
    lease_expires_at_ms: Annotated[
        UnixTimestampMs,
        Field(alias="leaseExpiresAtMs", description="Lease expiration timestamp."),
    ]
    mcp_grant: Annotated[
        McpGrantSchema | None,
        Field(alias="mcpGrant", description="Committed MCP grant, or null."),
    ]
    permissions: Annotated[
        ExecutionPermissionsSchema,
        Field(description="Committed execution permissions."),
    ]
    timeouts: Annotated[
        ExecutionTimeoutsSchema,
        Field(description="Committed supervision timeouts."),
    ]
    committed_at_ms: Annotated[
        UnixTimestampMs,
        Field(alias="committedAtMs", description="Snapshot commit timestamp."),
    ]


class DispatchedTurnSupervisionSchema(StrictSchemaModel):
    """Process supervision observation and durable launch-ledger record."""

    status: Annotated[str, Field(min_length=1, description="Non-empty supervision result.")]
    ledger: Annotated[
        LaunchLedgerRecordSchema,
        Field(description="Durable launch-ledger record for this dispatch."),
    ]
    exit_code: Annotated[
        SignedInt32 | None,
        Field(alias="exitCode", description="Process exit code, or null."),
    ]
    termination: Annotated[
        str | None,
        Field(description="Termination disposition, or null."),
    ]
    unknown_reason: Annotated[
        str | None,
        Field(alias="unknownReason", description="Unknown supervision reason, or null."),
    ]


class DispatchedTurnDispositionSchema(StrictSchemaModel):
    """Source member disposition applied after turn supervision."""

    kind: Annotated[str, Field(min_length=1, description="Non-empty source disposition kind.")]
    member: Annotated[SwarmMemberSchema, Field(description="Member after disposition.")]
    exit_code: Annotated[
        SignedInt32 | None,
        Field(alias="exitCode", description="Process exit code, or null."),
    ]
    timed_out: Annotated[
        bool,
        Field(alias="timedOut", description="Whether the turn reached its timeout."),
    ]


class DispatchSwarmTurnResponse(StrictSchemaModel):
    """Full receipt for one supervised Swarm member turn."""

    wakeup_batch: Annotated[
        SwarmWakeupBatchResponse,
        Field(alias="wakeupBatch", description="Claimed input messages and member state."),
    ]
    committed_snapshot: Annotated[
        CommittedExecutionSnapshotSchema,
        Field(alias="committedSnapshot", description="Frozen execution input snapshot."),
    ]
    supervision: Annotated[
        DispatchedTurnSupervisionSchema,
        Field(description="Process supervision and launch ledger."),
    ]
    disposition: Annotated[
        DispatchedTurnDispositionSchema,
        Field(description="Source-owned member turn disposition."),
    ]
    used_parent_spawner_slot: Annotated[
        bool,
        Field(
            alias="usedParentSpawnerSlot", description="Whether parent-spawner capacity was used."
        ),
    ]


class SwarmModelSwitchResponse(StrictSchemaModel):
    """Receipt after a quota-suspended member is switched and requeued."""

    member: Annotated[SwarmMemberSchema, Field(description="Member after profile switch.")]
    profile_id: Annotated[WireUUID, Field(alias="profileId", description="Resolved Profile UUID.")]
    profile_revision: Annotated[
        PositiveInt64,
        Field(alias="profileRevision", description="Resolved positive Profile revision."),
    ]
    resolved_preference: Annotated[
        ExecutionPreferenceSchema,
        Field(alias="resolvedPreference", description="Resolved execution preference."),
    ]
