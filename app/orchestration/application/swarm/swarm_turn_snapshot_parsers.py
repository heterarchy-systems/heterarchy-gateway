"""Wire parsers for committed snapshots and launch ledgers in Swarm turn receipts."""

from functools import partial

from pydantic import JsonValue

from app.orchestration.application.inner_dto.autonomy.autonomy_snapshot_inner_dto import (
    LaunchLedgerRecordDto,
    LaunchLedgerStateDto,
    ProcessOwnershipDto,
)
from app.orchestration.application.inner_dto.orchestration_execution_dto import McpGrantDto
from app.orchestration.application.inner_dto.swarm.swarm_turn_inner_dto import (
    CommittedExecutionSnapshotDto,
)
from app.orchestration.application.orchestration_wire_parsers import (
    INT32_MAX,
    INT32_MIN,
    INT64_MAX,
    UINT32_MAX,
    UINT64_MAX,
    parse_wire_int,
    parse_wire_str,
    require_wire_object,
    wire_optional,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_snapshot_schema import (
    ProcessOwnershipSchema,
)
from app.orchestration.schema.execution.orchestration_execution_schema import (
    ExecutionPermissionsSchema,
    ExecutionTimeoutsSchema,
    McpGrantSchema,
)
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    LaunchLedgerStatusEnum,
    LaunchUnknownReasonEnum,
)
from app.shared.types.wire_scalar_types import parse_wire_enum, parse_wire_uuid

_COMMITTED_SNAPSHOT_REQUIRED_KEYS = (
    "snapshotId",
    "workspaceId",
    "goalId",
    "dagRevision",
    "nodeId",
    "assignmentId",
    "attempt",
    "activityId",
    "profileId",
    "profileRevision",
    "resolvedEngine",
    "resolvedModel",
    "worktreePath",
    "leaseId",
    "leaseRevision",
    "leaseExpiresAtMs",
    "permissions",
    "timeouts",
    "committedAtMs",
)


def parse_committed_snapshot(value: JsonValue) -> CommittedExecutionSnapshotDto:
    """Parse the full source-committed execution snapshot projection.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable committed execution snapshot DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=_COMMITTED_SNAPSHOT_REQUIRED_KEYS,
        optional_keys=("resolvedReasoning", "rolePromptDigestHex", "mcpGrant"),
    )
    permissions = ExecutionPermissionsSchema.model_validate(payload["permissions"]).to_inner_dto()
    timeouts = ExecutionTimeoutsSchema.model_validate(payload["timeouts"]).to_inner_dto()
    mcp_grant = wire_optional(value=payload.get("mcpGrant"), parser=_parse_mcp_grant)
    result = CommittedExecutionSnapshotDto(
        snapshot_id=parse_wire_uuid(value=payload["snapshotId"]),
        workspace_id=parse_wire_uuid(value=payload["workspaceId"]),
        goal_id=parse_wire_uuid(value=payload["goalId"]),
        dag_revision=parse_wire_int(
            value=payload["dagRevision"], minimum=1, maximum=INT64_MAX, label="dagRevision"
        ),
        node_id=parse_wire_uuid(value=payload["nodeId"]),
        assignment_id=parse_wire_uuid(value=payload["assignmentId"]),
        attempt=parse_wire_int(
            value=payload["attempt"], minimum=0, maximum=UINT32_MAX, label="attempt"
        ),
        activity_id=parse_wire_uuid(value=payload["activityId"]),
        profile_id=parse_wire_uuid(value=payload["profileId"]),
        profile_revision=parse_wire_int(
            value=payload["profileRevision"],
            minimum=1,
            maximum=INT64_MAX,
            label="profileRevision",
        ),
        resolved_engine=parse_wire_str(value=payload["resolvedEngine"], label="resolvedEngine"),
        resolved_model=parse_wire_str(value=payload["resolvedModel"], label="resolvedModel"),
        resolved_reasoning=wire_optional(
            value=payload.get("resolvedReasoning"),
            parser=partial(parse_wire_str, label="resolvedReasoning"),
        ),
        role_prompt_digest_hex=wire_optional(
            value=payload.get("rolePromptDigestHex"),
            parser=partial(parse_wire_str, label="rolePromptDigestHex"),
        ),
        worktree_path=parse_wire_str(value=payload["worktreePath"], label="worktreePath"),
        lease_id=parse_wire_uuid(value=payload["leaseId"]),
        lease_revision=parse_wire_int(
            value=payload["leaseRevision"],
            minimum=0,
            maximum=UINT64_MAX,
            label="leaseRevision",
        ),
        lease_expires_at_ms=parse_wire_int(
            value=payload["leaseExpiresAtMs"],
            minimum=0,
            maximum=INT64_MAX,
            label="leaseExpiresAtMs",
        ),
        mcp_grant=mcp_grant,
        permissions=permissions,
        timeouts=timeouts,
        committed_at_ms=parse_wire_int(
            value=payload["committedAtMs"],
            minimum=0,
            maximum=INT64_MAX,
            label="committedAtMs",
        ),
    )
    return result


def parse_launch_ledger_record(value: JsonValue) -> LaunchLedgerRecordDto:
    """Parse one launch-ledger record while normalizing skipped nullable fields.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable launch-ledger record DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=(
            "snapshotId",
            "workspaceId",
            "goalId",
            "dagRevision",
            "nodeId",
            "assignmentId",
            "attempt",
            "state",
            "revision",
            "updatedAtMs",
        ),
    )
    result = LaunchLedgerRecordDto(
        snapshot_id=parse_wire_uuid(value=payload["snapshotId"]),
        workspace_id=parse_wire_uuid(value=payload["workspaceId"]),
        goal_id=parse_wire_uuid(value=payload["goalId"]),
        dag_revision=parse_wire_int(
            value=payload["dagRevision"], minimum=1, maximum=INT64_MAX, label="dagRevision"
        ),
        node_id=parse_wire_uuid(value=payload["nodeId"]),
        assignment_id=parse_wire_uuid(value=payload["assignmentId"]),
        attempt=parse_wire_int(
            value=payload["attempt"], minimum=0, maximum=UINT32_MAX, label="attempt"
        ),
        state=_parse_launch_ledger_state(value=payload["state"]),
        revision=parse_wire_int(
            value=payload["revision"], minimum=0, maximum=UINT64_MAX, label="revision"
        ),
        updated_at_ms=parse_wire_int(
            value=payload["updatedAtMs"], minimum=0, maximum=INT64_MAX, label="updatedAtMs"
        ),
    )
    return result


def _parse_mcp_grant(value: JsonValue) -> McpGrantDto:
    """Validate and convert one optional source MCP grant object.

    Args:
        value: Decoded Orchestration MCP grant JSON object.
    Return:
        Immutable validated MCP grant DTO.
    """
    if not isinstance(value, dict):
        raise ValueError("Orchestration response field mcpGrant must be an object or null")
    result = McpGrantSchema.model_validate(value).to_inner_dto()
    return result


def _parse_process_ownership(value: JsonValue) -> ProcessOwnershipDto:
    """Parse one optional source process-group witness.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable process ownership DTO.
    """
    payload = require_wire_object(
        payload=value, required_keys=("pid", "pgid", "startTime", "bootId")
    )
    schema = ProcessOwnershipSchema.model_validate(payload)
    result = ProcessOwnershipDto(
        pid=schema.pid,
        pgid=schema.pgid,
        start_time=schema.start_time,
        boot_id=schema.boot_id,
    )
    return result


def _parse_launch_ledger_state(value: JsonValue) -> LaunchLedgerStateDto:
    """Parse a launch-ledger state and source-omittable nullable observations.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable launch-ledger state DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=("status",),
        optional_keys=("ownership", "exitCode", "unknownReason", "observedAtMs"),
    )
    ownership = wire_optional(value=payload.get("ownership"), parser=_parse_process_ownership)
    unknown_reason = wire_optional(
        value=payload.get("unknownReason"),
        parser=partial(parse_wire_enum, LaunchUnknownReasonEnum),
    )
    ledger_status = parse_wire_enum(enum_type=LaunchLedgerStatusEnum, value=payload["status"])
    result = LaunchLedgerStateDto(
        status=ledger_status,
        ownership=ownership,
        exit_code=wire_optional(
            value=payload.get("exitCode"),
            parser=partial(parse_wire_int, minimum=INT32_MIN, maximum=INT32_MAX, label="exitCode"),
        ),
        unknown_reason=unknown_reason,
        observed_at_ms=wire_optional(
            value=payload.get("observedAtMs"),
            parser=partial(parse_wire_int, minimum=0, maximum=INT64_MAX, label="observedAtMs"),
        ),
    )
    return result
