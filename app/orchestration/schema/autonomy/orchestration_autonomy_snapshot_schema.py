"""Strict schemas for immutable execution snapshot operations."""

from functools import partial
from typing import Annotated

from pydantic import BeforeValidator, Field

from app.orchestration.schema.execution.orchestration_execution_schema import (
    ExecutionPermissionsSchema,
    ExecutionTimeoutsSchema,
    McpGrantSchema,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    LaunchUnknownReason,
    PositiveInt64,
    Sha256DigestHex,
    SignedInt32,
    SnapshotUUID,
    UnixTimestampMs,
    UnsignedRevision,
    WorkAttempt,
)
from app.orchestration.schema.types.orchestration_types import (
    ExecutionPreference,
    UInt32,
    UInt64,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    ExecutionSnapshotQueryFieldEnum,
    LaunchLedgerStatusEnum,
)
from app.shared.types.wire_scalar_types import WireUUID, parse_wire_enum

type LaunchLedgerStatus = Annotated[
    LaunchLedgerStatusEnum,
    BeforeValidator(partial(parse_wire_enum, LaunchLedgerStatusEnum)),
]


class PrepareExecutionSnapshotRequest(StrictSchemaModel):
    """Validate and commit one immutable pre-spawn snapshot."""

    request_id: Annotated[
        WireUUID,
        Field(
            description="Stable idempotency identity for this prepare request.", alias="requestId"
        ),
    ]
    snapshot_id: Annotated[
        WireUUID,
        Field(description="Immutable execution snapshot identity.", alias="snapshotId"),
    ]
    goal_id: Annotated[
        WireUUID,
        Field(description="Goal identity.", alias=ExecutionSnapshotQueryFieldEnum.GOAL_ID.value),
    ]
    dag_revision: Annotated[
        DagRevision,
        Field(
            description="Positive DAG revision.",
            alias=ExecutionSnapshotQueryFieldEnum.DAG_REVISION.value,
        ),
    ]
    node_id: Annotated[
        WireUUID,
        Field(
            description="DAG node identity.", alias=ExecutionSnapshotQueryFieldEnum.NODE_ID.value
        ),
    ]
    assignment_id: Annotated[
        WireUUID,
        Field(
            description="Agent assignment identity.",
            alias=ExecutionSnapshotQueryFieldEnum.ASSIGNMENT_ID.value,
        ),
    ]
    attempt: Annotated[
        WorkAttempt,
        Field(
            alias=ExecutionSnapshotQueryFieldEnum.ATTEMPT.value,
            description="Zero-based execution attempt.",
        ),
    ]
    activity_id: Annotated[
        WireUUID,
        Field(description="Orchestration activity identity.", alias="activityId"),
    ]
    profile_id: Annotated[
        WireUUID,
        Field(description="Agent Profile identity.", alias="profileId"),
    ]
    profile_revision: Annotated[
        PositiveInt64,
        Field(description="Positive Agent Profile revision.", gt=0, alias="profileRevision"),
    ]
    resolved_engine: Annotated[
        ExecutionPreference,
        Field(description="Resolved local CLI engine.", alias="resolvedEngine"),
    ]
    resolved_model: Annotated[
        str,
        Field(description="Resolved model identifier.", alias="resolvedModel"),
    ]
    resolved_reasoning: Annotated[
        str | None,
        Field(description="Resolved reasoning setting, or null.", alias="resolvedReasoning"),
    ]
    role_prompt_digest_hex: Annotated[
        Sha256DigestHex | None,
        Field(
            description="Resolved role prompt SHA-256 digest, or null.", alias="rolePromptDigestHex"
        ),
    ]
    worktree_path: Annotated[
        str,
        Field(description="Workspace path selected for this attempt.", alias="worktreePath"),
    ]
    lease_id: Annotated[WireUUID, Field(description="Execution lease identity.", alias="leaseId")]
    lease_revision: Annotated[
        UInt64,
        Field(description="Execution lease revision.", alias="leaseRevision"),
    ]
    lease_expires_at_ms: Annotated[
        UnixTimestampMs,
        Field(description="Lease expiration time in Unix milliseconds.", alias="leaseExpiresAtMs"),
    ]
    mcp_grant: Annotated[
        McpGrantSchema | None,
        Field(description="Secret-free MCP grant metadata, or null.", alias="mcpGrant"),
    ]
    permissions: Annotated[
        ExecutionPermissionsSchema,
        Field(description="Explicit sandbox permission flags."),
    ]
    timeouts: Annotated[
        ExecutionTimeoutsSchema,
        Field(description="Bounded execution timeout values."),
    ]


class ProcessOwnershipSchema(StrictSchemaModel):
    """Optional operating-system process-group witness."""

    pid: Annotated[UInt32, Field(description="Operating-system process identity.")]
    pgid: Annotated[UInt32, Field(description="Operating-system process-group identity.")]
    start_time: Annotated[
        str,
        Field(description="Process start-time witness.", alias="startTime"),
    ]
    boot_id: Annotated[str, Field(description="Operating-system boot identity.", alias="bootId")]


class LaunchLedgerStateSchema(StrictSchemaModel):
    """Recorded launch state and nullable process observations."""

    status: Annotated[
        LaunchLedgerStatus,
        Field(description="Recorded execution launch status."),
    ]
    ownership: Annotated[
        ProcessOwnershipSchema | None,
        Field(description="Process ownership witness, or null."),
    ]
    exit_code: Annotated[
        SignedInt32 | None,
        Field(description="Observed process exit code, or null.", alias="exitCode"),
    ]
    unknown_reason: Annotated[
        LaunchUnknownReason | None,
        Field(description="Reason for unknown execution state, or null.", alias="unknownReason"),
    ]
    observed_at_ms: Annotated[
        UnixTimestampMs | None,
        Field(
            description="State observation time in Unix milliseconds, or null.",
            alias="observedAtMs",
        ),
    ]


class LaunchLedgerRecordSchema(StrictSchemaModel):
    """Durable execution snapshot launch-ledger record."""

    snapshot_id: Annotated[
        SnapshotUUID,
        Field(description="Execution snapshot identity.", alias="snapshotId"),
    ]
    workspace_id: Annotated[
        WireUUID,
        Field(
            description="Workspace identity.",
            alias=ExecutionSnapshotQueryFieldEnum.WORKSPACE_ID.value,
        ),
    ]
    goal_id: Annotated[
        WireUUID,
        Field(description="Goal identity.", alias=ExecutionSnapshotQueryFieldEnum.GOAL_ID.value),
    ]
    dag_revision: Annotated[
        DagRevision,
        Field(
            description="Positive DAG revision.",
            alias=ExecutionSnapshotQueryFieldEnum.DAG_REVISION.value,
        ),
    ]
    node_id: Annotated[
        WireUUID,
        Field(
            description="DAG node identity.", alias=ExecutionSnapshotQueryFieldEnum.NODE_ID.value
        ),
    ]
    assignment_id: Annotated[
        WireUUID,
        Field(
            description="Agent assignment identity.",
            alias=ExecutionSnapshotQueryFieldEnum.ASSIGNMENT_ID.value,
        ),
    ]
    attempt: Annotated[
        WorkAttempt,
        Field(
            alias=ExecutionSnapshotQueryFieldEnum.ATTEMPT.value,
            description="Zero-based execution attempt.",
        ),
    ]
    state: Annotated[LaunchLedgerStateSchema, Field(description="Recorded launch state.")]
    revision: Annotated[
        UnsignedRevision,
        Field(gt=0, description="Positive launch-ledger revision."),
    ]
    updated_at_ms: Annotated[
        UnixTimestampMs,
        Field(description="Last record update time in Unix milliseconds.", alias="updatedAtMs"),
    ]


class ExecutionSnapshotOutcomeResponse(StrictSchemaModel):
    """Typed committed or rejected result from snapshot preparation."""

    committed: Annotated[bool, Field(description="Whether the snapshot was committed.")]
    rejection_code: Annotated[
        str | None,
        Field(description="Stable validation rejection code, or null.", alias="rejectionCode"),
    ]
    detail: Annotated[str | None, Field(description="Validation rejection detail, or null.")]
    record: Annotated[
        LaunchLedgerRecordSchema | None,
        Field(description="Committed launch-ledger record, or null."),
    ]


class ExecutionSnapshotQueryResponse(StrictSchemaModel):
    """Read one exact execution attempt and optional launch-ledger record."""

    workspace_id: Annotated[
        WireUUID,
        Field(
            description="Workspace identity selected by the URL path.",
            alias=ExecutionSnapshotQueryFieldEnum.WORKSPACE_ID.value,
        ),
    ]
    goal_id: Annotated[
        WireUUID,
        Field(description="Goal identity.", alias=ExecutionSnapshotQueryFieldEnum.GOAL_ID.value),
    ]
    dag_revision: Annotated[
        DagRevision,
        Field(
            description="Positive DAG revision.",
            alias=ExecutionSnapshotQueryFieldEnum.DAG_REVISION.value,
        ),
    ]
    node_id: Annotated[
        WireUUID,
        Field(
            description="DAG node identity.", alias=ExecutionSnapshotQueryFieldEnum.NODE_ID.value
        ),
    ]
    assignment_id: Annotated[
        WireUUID,
        Field(
            description="Agent assignment identity.",
            alias=ExecutionSnapshotQueryFieldEnum.ASSIGNMENT_ID.value,
        ),
    ]
    attempt: Annotated[
        WorkAttempt,
        Field(
            alias=ExecutionSnapshotQueryFieldEnum.ATTEMPT.value,
            description="Zero-based execution attempt.",
        ),
    ]
    record: Annotated[
        LaunchLedgerRecordSchema | None,
        Field(description="Matching launch-ledger record, or null when absent."),
    ]
