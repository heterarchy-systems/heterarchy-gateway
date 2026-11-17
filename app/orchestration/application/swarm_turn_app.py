"""Parse and forward Native Swarm turn operations without domain decisions."""

from dataclasses import replace
from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue, TypeAdapter

from app.orchestration.application.autonomy_wire_utils import require_wire_object
from app.orchestration.application.inner_dto.autonomy_snapshot_inner_dto import (
    LaunchLedgerRecordDto,
    LaunchLedgerStateDto,
    ProcessOwnershipDto,
)
from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPreferenceDto,
)
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
    SwarmMemberDict,
    SwarmMemberDto,
)
from app.orchestration.application.inner_dto.swarm_turn_inner_dto import (
    ClaimSwarmWakeupCommandDto,
    CommittedExecutionSnapshotDto,
    CompleteSwarmTurnCommandDto,
    DispatchedTurnDispositionDto,
    DispatchedTurnSupervisionDto,
    DispatchSwarmTurnCommandDto,
    DispatchSwarmTurnInnerDto,
    DispatchSwarmTurnResponseDict,
    FailSwarmTurnCommandDto,
    SwarmModelSwitchInnerDto,
    SwarmModelSwitchResponseDict,
    SwarmWakeupBatchDict,
    SwarmWakeupBatchDto,
    SwitchSwarmMemberModelCommandDto,
)
from app.orchestration.application.orchestration_command_utils import (
    ORCHESTRATION_SWARM_EXCHANGE_POLICY,
    execute_orchestration_operation,
)
from app.orchestration.application.swarm_state_parsers import (
    parse_swarm_board_message,
    parse_swarm_member,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_snapshot_schema import (
    ProcessOwnershipSchema,
)
from app.orchestration.schema.execution.orchestration_execution_schema import (
    ExecutionPermissionsSchema,
    ExecutionTimeoutsSchema,
    McpGrantSchema,
)
from app.orchestration.schema.swarm.orchestration_swarm_turn_schema import (
    ClaimSwarmWakeupRequest,
    CompleteSwarmTurnRequest,
    DispatchSwarmTurnRequest,
    FailSwarmTurnRequest,
    SwitchSwarmMemberModelRequest,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    PositiveInt64,
    SignedInt32,
    UnixTimestampMs,
    UnsignedRevision,
    WorkAttempt,
)
from app.orchestration.schema.types.orchestration_types import (
    ExecutionPreference,
    Int64,
    UInt64,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    LaunchLedgerStatusEnum,
    LaunchUnknownReasonEnum,
)
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmTurnFailureDispositionEnum,
)
from app.shared.types.base_types import JsonObject
from app.shared.types.threaded_mapping import threaded_map
from app.shared.types.upstream_exchange import UpstreamExchangePolicy
from app.shared.types.wire_scalar_types import parse_wire_enum, parse_wire_uuid

_DISPATCH_SLACK_MS = 5_000
_MAX_DISPATCH_TIMEOUT_SECONDS = 900.0
_DAG_REVISION_ADAPTER: TypeAdapter[DagRevision] = TypeAdapter(DagRevision)
_WORK_ATTEMPT_ADAPTER: TypeAdapter[WorkAttempt] = TypeAdapter(WorkAttempt)
_UNSIGNED_REVISION_ADAPTER: TypeAdapter[UnsignedRevision] = TypeAdapter(UnsignedRevision)
_POSITIVE_INT64_ADAPTER: TypeAdapter[PositiveInt64] = TypeAdapter(PositiveInt64)
_SIGNED_INT32_ADAPTER: TypeAdapter[SignedInt32] = TypeAdapter(SignedInt32)
_INT64_ADAPTER: TypeAdapter[Int64] = TypeAdapter(Int64)
_UNIX_TIMESTAMP_ADAPTER: TypeAdapter[UnixTimestampMs] = TypeAdapter(UnixTimestampMs)
_UINT64_ADAPTER: TypeAdapter[UInt64] = TypeAdapter(UInt64)
_STRING_ADAPTER: TypeAdapter[str] = TypeAdapter(str)
_BOOL_ADAPTER: TypeAdapter[bool] = TypeAdapter(bool)
_EXECUTION_PREFERENCE_ADAPTER: TypeAdapter[ExecutionPreference] = TypeAdapter(ExecutionPreference)


def build_dispatch_exchange_policy(
    request: DispatchSwarmTurnRequest,
    timeout_floor_seconds: float,
) -> UpstreamExchangePolicy:
    """Build request-local bounds matching the Swarm dispatch transport.

    Args:
        request: Strictly validated dispatch request carrying the phase timeouts.
        timeout_floor_seconds: Runtime-configured baseline HTTP timeout.
    Return:
        Policy with Swarm byte caps and the source-compatible total deadline.
    """
    total_timeout_ms = (
        request.timeouts.startup_timeout_ms
        + request.timeouts.execution_timeout_ms
        + request.timeouts.termination_grace_ms
        + _DISPATCH_SLACK_MS
    )
    phase_timeout_seconds = total_timeout_ms / 1000.0
    timeout_seconds = min(
        max(timeout_floor_seconds, phase_timeout_seconds),
        _MAX_DISPATCH_TIMEOUT_SECONDS,
    )
    result = replace(ORCHESTRATION_SWARM_EXCHANGE_POLICY, timeout_seconds=timeout_seconds)
    return result


def _required_value[ValueT](
    payload: JsonObject,
    key: str,
    adapter: TypeAdapter[ValueT],
) -> ValueT:
    """Strictly parse one required scalar using its bounded adapter.

    Args:
        payload: Exact source JSON object.
        key: Required wire field name.
        adapter: Strict Pydantic scalar adapter.
    Return:
        Parsed field value.
    """
    result = adapter.validate_python(payload[key], strict=True)
    return result


def _required_string(payload: JsonObject, key: str) -> str:
    """Read one required JSON string without primitive coercion.

    Args:
        payload: Exact source JSON object.
        key: Required source field name.
    Return:
        Strictly parsed string value.
    """
    result = _required_value(payload=payload, key=key, adapter=_STRING_ADAPTER)
    return result


def _required_uuid(payload: JsonObject, key: str) -> UUID:
    """Read one required source UUID string.

    Args:
        payload: Exact source JSON object.
        key: Required source UUID field name.
    Return:
        Parsed UUID value.
    """
    result = parse_wire_uuid(value=payload[key])
    return result


def _required_integer[ValueT](
    payload: JsonObject,
    key: str,
    adapter: TypeAdapter[ValueT],
) -> ValueT:
    """Read one integer JSON field with the source scalar bounds.

    Args:
        payload: Exact source JSON object.
        key: Required source integer field name.
        adapter: Integer adapter carrying signedness and range constraints.
    Return:
        Strictly bounded integer value.
    """
    result = _required_value(payload=payload, key=key, adapter=adapter)
    return result


def _required_boolean(payload: JsonObject, key: str) -> bool:
    """Read one required JSON boolean without accepting integer substitutes.

    Args:
        payload: Exact source JSON object.
        key: Required source boolean field name.
    Return:
        Strictly parsed boolean value.
    """
    result = _required_value(payload=payload, key=key, adapter=_BOOL_ADAPTER)
    return result


def _required_array(payload: JsonObject, key: str) -> list[JsonValue]:
    """Read one required source JSON array.

    Args:
        payload: Exact source JSON object.
        key: Required source array field name.
    Return:
        JSON values in source order.
    """
    value = payload[key]
    if not isinstance(value, list):
        raise ValueError(f"Orchestration response field {key} must be an array")
    result = value
    return result


def _source_object(
    value: JsonValue,
    required_keys: tuple[str, ...],
    optional_keys: tuple[str, ...] = (),
) -> JsonObject:
    """Require one exact JSON object with only source-declared fields.

    Args:
        value: Decoded Orchestration JSON value.
        required_keys: Required source field names.
        optional_keys: Nullable fields that source serialization may omit.
    Return:
        Validated source object retaining its JSON values.
    """
    result = require_wire_object(
        payload=value, required_keys=required_keys, optional_keys=optional_keys
    )
    return result


def _optional_string(payload: JsonObject, key: str) -> str | None:
    """Normalize one source-omittable nullable string.

    Args:
        payload: Exact source JSON object.
        key: Nullable source field name.
    Return:
        String value or None for omitted/null source values.
    """
    value = payload.get(key)
    if value is None:
        result = None
    else:
        result = _STRING_ADAPTER.validate_python(value, strict=True)
    return result


def _optional_integer[ValueT](
    payload: JsonObject,
    key: str,
    adapter: TypeAdapter[ValueT],
) -> ValueT | None:
    """Normalize one source-omittable nullable integer.

    Args:
        payload: Exact source JSON object.
        key: Nullable source field name.
        adapter: Integer adapter carrying source bounds.
    Return:
        Bounded integer value or None for omitted/null source values.
    """
    value = payload.get(key)
    if value is None:
        result = None
    else:
        result = adapter.validate_python(value, strict=True)
    return result


def _optional_object(payload: JsonObject, key: str) -> JsonObject | None:
    """Normalize one source-omittable nullable object.

    Args:
        payload: Exact source JSON object.
        key: Nullable source object field name.
    Return:
        Validated nested source object or None.
    """
    value = payload.get(key)
    if value is None:
        result = None
    elif isinstance(value, dict):
        result = value
    else:
        raise ValueError(f"Orchestration response field {key} must be an object or null")
    return result


def _require_member_scope(
    member: SwarmMemberDto,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
) -> None:
    """Enforce the source client member identity readback contract.

    Args:
        member: Parsed source member projection.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
    Return:
        None.
    """
    observed = (member.workspace_id, member.swarm_run_id, member.member_id)
    expected = (workspace_id, swarm_run_id, member_id)
    if observed != expected:
        raise ValueError("Swarm member response escaped the requested identity scope")


def _parse_wakeup_batch(value: JsonValue) -> SwarmWakeupBatchDto:
    """Parse one exact source wakeup batch and its bounded board messages.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable source wakeup batch DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=(
            "swarmRunId",
            "member",
            "snapshotId",
            "committedSeenSeq",
            "inflightTargetSeq",
            "messages",
            "totalBodyBytes",
        ),
    )
    message_values = _required_array(payload=payload, key="messages")
    messages = tuple(threaded_map(function=parse_swarm_board_message, values=message_values))
    result = SwarmWakeupBatchDto(
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        member=parse_swarm_member(value=payload["member"]),
        snapshot_id=_required_uuid(payload=payload, key="snapshotId"),
        committed_seen_seq=_required_integer(
            payload=payload, key="committedSeenSeq", adapter=_UINT64_ADAPTER
        ),
        inflight_target_seq=_required_integer(
            payload=payload, key="inflightTargetSeq", adapter=_UINT64_ADAPTER
        ),
        messages=messages,
        total_body_bytes=_required_integer(
            payload=payload, key="totalBodyBytes", adapter=_UINT64_ADAPTER
        ),
    )
    return result


def _require_wakeup_context(
    batch: SwarmWakeupBatchDto,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
    snapshot_id: UUID,
) -> None:
    """Check the source client wakeup and member identity correlations.

    Args:
        batch: Parsed wakeup batch.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
        snapshot_id: Snapshot identity supplied by the request.
    Return:
        None.
    """
    observed = (batch.swarm_run_id, batch.snapshot_id)
    expected = (swarm_run_id, snapshot_id)
    if observed != expected:
        raise ValueError("Swarm wakeup response escaped the requested run snapshot")
    _require_member_scope(
        member=batch.member,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
    )


def _parse_claim_result(
    value: JsonValue,
    *,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
    snapshot_id: UUID,
) -> SwarmWakeupBatchDict:
    """Parse and correlate one wakeup claim result.

    Args:
        value: Decoded Orchestration JSON result.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
        snapshot_id: Snapshot identity supplied by the request.
    Return:
        Closed typed source wakeup response.
    """
    batch = _parse_wakeup_batch(value=value)
    _require_wakeup_context(
        batch=batch,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        snapshot_id=snapshot_id,
    )
    result = batch.to_dict()
    return result


def _parse_member_result(
    value: JsonValue,
    *,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
) -> SwarmMemberDict:
    """Parse and correlate a member mutation receipt.

    Args:
        value: Decoded Orchestration JSON result.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
    Return:
        Closed typed Swarm member result.
    """
    member = parse_swarm_member(value=value)
    _require_member_scope(
        member=member, workspace_id=workspace_id, swarm_run_id=swarm_run_id, member_id=member_id
    )
    result = member.to_dict()
    return result


def _parse_execution_preference(value: JsonValue) -> ExecutionPreferenceDto:
    """Parse a source execution preference and normalize nullable omissions.

    Args:
        value: Decoded Orchestration execution-preference object.
    Return:
        Immutable validated execution preference DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=("cliEngine", "preferredModel", "capabilities"),
        optional_keys=("preferredReasoning", "rolePromptDigestHex"),
    )
    capabilities = _required_array(payload=payload, key="capabilities")
    parsed_capabilities = tuple(
        _STRING_ADAPTER.validate_python(capability, strict=True) for capability in capabilities
    )
    engine_value = payload["cliEngine"]
    cli_engine = _EXECUTION_PREFERENCE_ADAPTER.validate_python(engine_value, strict=True)
    result = ExecutionPreferenceDto(
        cli_engine=cli_engine,
        preferred_model=_required_string(payload=payload, key="preferredModel"),
        preferred_reasoning=_optional_string(payload=payload, key="preferredReasoning"),
        capabilities=parsed_capabilities,
        role_prompt_digest_hex=_optional_string(payload=payload, key="rolePromptDigestHex"),
    )
    return result


def _parse_committed_snapshot(value: JsonValue) -> CommittedExecutionSnapshotDto:
    """Parse the full source-committed execution snapshot projection.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable committed execution snapshot DTO.
    """
    required_keys = (
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
    payload = _source_object(
        value=value,
        required_keys=required_keys,
        optional_keys=("resolvedReasoning", "rolePromptDigestHex", "mcpGrant"),
    )
    permissions = ExecutionPermissionsSchema.model_validate(payload["permissions"]).to_inner_dto()
    timeouts = ExecutionTimeoutsSchema.model_validate(payload["timeouts"]).to_inner_dto()
    mcp_payload = _optional_object(payload=payload, key="mcpGrant")
    mcp_schema = McpGrantSchema.model_validate(mcp_payload) if mcp_payload is not None else None
    mcp_grant = mcp_schema.to_inner_dto() if mcp_schema is not None else None
    result = CommittedExecutionSnapshotDto(
        snapshot_id=_required_uuid(payload=payload, key="snapshotId"),
        workspace_id=_required_uuid(payload=payload, key="workspaceId"),
        goal_id=_required_uuid(payload=payload, key="goalId"),
        dag_revision=_required_integer(
            payload=payload, key="dagRevision", adapter=_DAG_REVISION_ADAPTER
        ),
        node_id=_required_uuid(payload=payload, key="nodeId"),
        assignment_id=_required_uuid(payload=payload, key="assignmentId"),
        attempt=_required_integer(payload=payload, key="attempt", adapter=_WORK_ATTEMPT_ADAPTER),
        activity_id=_required_uuid(payload=payload, key="activityId"),
        profile_id=_required_uuid(payload=payload, key="profileId"),
        profile_revision=_required_integer(
            payload=payload, key="profileRevision", adapter=_POSITIVE_INT64_ADAPTER
        ),
        resolved_engine=_required_string(payload=payload, key="resolvedEngine"),
        resolved_model=_required_string(payload=payload, key="resolvedModel"),
        resolved_reasoning=_optional_string(payload=payload, key="resolvedReasoning"),
        role_prompt_digest_hex=_optional_string(payload=payload, key="rolePromptDigestHex"),
        worktree_path=_required_string(payload=payload, key="worktreePath"),
        lease_id=_required_uuid(payload=payload, key="leaseId"),
        lease_revision=_required_integer(
            payload=payload, key="leaseRevision", adapter=_UINT64_ADAPTER
        ),
        lease_expires_at_ms=_required_integer(
            payload=payload, key="leaseExpiresAtMs", adapter=_UNIX_TIMESTAMP_ADAPTER
        ),
        mcp_grant=mcp_grant,
        permissions=permissions,
        timeouts=timeouts,
        committed_at_ms=_required_integer(
            payload=payload, key="committedAtMs", adapter=_UNIX_TIMESTAMP_ADAPTER
        ),
    )
    return result


def _parse_process_ownership(value: JsonValue) -> ProcessOwnershipDto:
    """Parse one optional source process-group witness.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable process ownership DTO.
    """
    payload = _source_object(value=value, required_keys=("pid", "pgid", "startTime", "bootId"))
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
    payload = _source_object(
        value=value,
        required_keys=("status",),
        optional_keys=("ownership", "exitCode", "unknownReason", "observedAtMs"),
    )
    ownership_payload = _optional_object(payload=payload, key="ownership")
    ownership = (
        _parse_process_ownership(value=ownership_payload) if ownership_payload is not None else None
    )
    unknown_reason_value = payload.get("unknownReason")
    unknown_reason = (
        parse_wire_enum(enum_type=LaunchUnknownReasonEnum, value=unknown_reason_value)
        if unknown_reason_value is not None
        else None
    )
    status_value = _required_string(payload=payload, key="status")
    ledger_status = parse_wire_enum(enum_type=LaunchLedgerStatusEnum, value=status_value)
    result = LaunchLedgerStateDto(
        status=ledger_status,
        ownership=ownership,
        exit_code=_optional_integer(payload=payload, key="exitCode", adapter=_SIGNED_INT32_ADAPTER),
        unknown_reason=unknown_reason,
        observed_at_ms=_optional_integer(
            payload=payload, key="observedAtMs", adapter=_UNIX_TIMESTAMP_ADAPTER
        ),
    )
    return result


def _parse_launch_ledger_record(value: JsonValue) -> LaunchLedgerRecordDto:
    """Parse one launch-ledger record while normalizing skipped nullable fields.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable launch-ledger record DTO.
    """
    payload = _source_object(
        value=value,
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
        snapshot_id=_required_uuid(payload=payload, key="snapshotId"),
        workspace_id=_required_uuid(payload=payload, key="workspaceId"),
        goal_id=_required_uuid(payload=payload, key="goalId"),
        dag_revision=_required_integer(
            payload=payload, key="dagRevision", adapter=_DAG_REVISION_ADAPTER
        ),
        node_id=_required_uuid(payload=payload, key="nodeId"),
        assignment_id=_required_uuid(payload=payload, key="assignmentId"),
        attempt=_required_integer(payload=payload, key="attempt", adapter=_WORK_ATTEMPT_ADAPTER),
        state=_parse_launch_ledger_state(value=payload["state"]),
        revision=_required_integer(
            payload=payload, key="revision", adapter=_UNSIGNED_REVISION_ADAPTER
        ),
        updated_at_ms=_required_integer(
            payload=payload, key="updatedAtMs", adapter=_UNIX_TIMESTAMP_ADAPTER
        ),
    )
    return result


def _parse_supervision(value: JsonValue) -> DispatchedTurnSupervisionDto:
    """Parse one source supervision projection and launch-ledger record.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable dispatch supervision DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=("status", "ledger"),
        optional_keys=("exitCode", "termination", "unknownReason"),
    )
    result = DispatchedTurnSupervisionDto(
        status=_required_string(payload=payload, key="status"),
        ledger=_parse_launch_ledger_record(value=payload["ledger"]),
        exit_code=_optional_integer(payload=payload, key="exitCode", adapter=_SIGNED_INT32_ADAPTER),
        termination=_optional_string(payload=payload, key="termination"),
        unknown_reason=_optional_string(payload=payload, key="unknownReason"),
    )
    return result


def _parse_disposition(value: JsonValue) -> DispatchedTurnDispositionDto:
    """Parse one source-owned member disposition.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable member disposition DTO.
    """
    payload = _source_object(
        value=value, required_keys=("kind", "member", "timedOut"), optional_keys=("exitCode",)
    )
    result = DispatchedTurnDispositionDto(
        kind=_required_string(payload=payload, key="kind"),
        member=parse_swarm_member(value=payload["member"]),
        exit_code=_optional_integer(payload=payload, key="exitCode", adapter=_SIGNED_INT32_ADAPTER),
        timed_out=_required_boolean(payload=payload, key="timedOut"),
    )
    return result


def _require_dispatch_context(
    response: DispatchSwarmTurnInnerDto,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
    snapshot_id: UUID,
) -> None:
    """Apply exactly the Rust client dispatch snapshot and member readback checks.

    Args:
        response: Parsed dispatch receipt.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
        snapshot_id: Snapshot identity supplied by the request.
    Return:
        None.
    """
    batch = response.wakeup_batch
    _require_wakeup_context(
        batch=batch,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        snapshot_id=snapshot_id,
    )
    snapshot = response.committed_snapshot
    if (snapshot.snapshot_id, snapshot.workspace_id) != (snapshot_id, workspace_id):
        raise ValueError("Committed snapshot response escaped the requested scope")
    ledger = response.supervision.ledger
    if (ledger.snapshot_id, ledger.workspace_id) != (snapshot_id, workspace_id):
        raise ValueError("Launch ledger response escaped the requested snapshot scope")
    if not response.supervision.status or not response.disposition.kind:
        raise ValueError("Dispatch response contains an empty supervision or disposition kind")
    _require_member_scope(
        member=response.disposition.member,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
    )


def _parse_dispatch_result(
    value: JsonValue,
    *,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
    snapshot_id: UUID,
) -> DispatchSwarmTurnResponseDict:
    """Parse and correlate the full supervised dispatch receipt.

    Args:
        value: Decoded Orchestration JSON result.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
        snapshot_id: Snapshot identity supplied by the request.
    Return:
        Closed typed dispatch result.
    """
    payload = _source_object(
        value=value,
        required_keys=(
            "wakeupBatch",
            "committedSnapshot",
            "supervision",
            "disposition",
            "usedParentSpawnerSlot",
        ),
    )
    response = DispatchSwarmTurnInnerDto(
        wakeup_batch=_parse_wakeup_batch(value=payload["wakeupBatch"]),
        committed_snapshot=_parse_committed_snapshot(value=payload["committedSnapshot"]),
        supervision=_parse_supervision(value=payload["supervision"]),
        disposition=_parse_disposition(value=payload["disposition"]),
        used_parent_spawner_slot=_required_boolean(payload=payload, key="usedParentSpawnerSlot"),
    )
    _require_dispatch_context(
        response=response,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        snapshot_id=snapshot_id,
    )
    result = response.to_dict()
    return result


def _parse_model_switch_result(
    value: JsonValue,
    *,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
) -> SwarmModelSwitchResponseDict:
    """Parse and correlate a source model-switch receipt.

    Args:
        value: Decoded Orchestration JSON result.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
    Return:
        Closed typed model-switch result.
    """
    payload = _source_object(
        value=value,
        required_keys=("member", "profileId", "profileRevision", "resolvedPreference"),
    )
    preference = _parse_execution_preference(value=payload["resolvedPreference"])
    response = SwarmModelSwitchInnerDto(
        member=parse_swarm_member(value=payload["member"]),
        profile_id=_required_uuid(payload=payload, key="profileId"),
        profile_revision=_required_integer(
            payload=payload, key="profileRevision", adapter=_POSITIVE_INT64_ADAPTER
        ),
        resolved_preference=preference,
    )
    _require_member_scope(
        member=response.member,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
    )
    if response.profile_id.int == 0 or response.profile_revision <= 0:
        raise ValueError("Model-switch response contains an invalid Profile identity or revision")
    result = response.to_dict()
    return result


class SwarmTurnApplication:
    """Execute request-scoped Swarm turn calls and validate source readbacks."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Bind the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying request authority and transport.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def claim_turn(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: ClaimSwarmWakeupRequest,
    ) -> OrchestrationOutcomeDto[SwarmWakeupBatchDict]:
        """Claim one member's coalesced wakeup batch.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible wakeup claim request.
        Return:
            Original HTTP status and typed wakeup result or backend error.
        """
        command = ClaimSwarmWakeupCommandDto(snapshot_id=request.snapshot_id)
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/claim",
            parse_result=partial(
                _parse_claim_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
                snapshot_id=request.snapshot_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def complete_turn(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: CompleteSwarmTurnRequest,
    ) -> OrchestrationOutcomeDto[SwarmMemberDict]:
        """Complete one member turn and commit its optional output receipt.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible completion request.
        Return:
            Original HTTP status and typed member result or backend error.
        """
        command = CompleteSwarmTurnCommandDto(
            expected_snapshot_id=request.expected_snapshot_id,
            output_commit_oid=request.output_commit_oid,
            output_tree_blake3_hex=request.output_tree_blake3_hex,
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/complete",
            parse_result=partial(
                _parse_member_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def fail_turn(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: FailSwarmTurnRequest,
    ) -> OrchestrationOutcomeDto[SwarmMemberDict]:
        """Release one failed or suspended turn using the source disposition.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible failure request.
        Return:
            Original HTTP status and typed member result or backend error.
        """
        command = FailSwarmTurnCommandDto(
            expected_snapshot_id=request.expected_snapshot_id,
            disposition=SwarmTurnFailureDispositionEnum(request.disposition),
            consume_turn=request.consume_turn,
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/fail",
            parse_result=partial(
                _parse_member_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def dispatch_turn(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: DispatchSwarmTurnRequest,
        timeout_floor_seconds: float,
    ) -> OrchestrationOutcomeDto[DispatchSwarmTurnResponseDict]:
        """Dispatch one member turn under the request-local phase deadline.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible dispatch request.
            timeout_floor_seconds: Runtime-configured HTTP timeout baseline.
        Return:
            Original HTTP status and typed dispatch result or backend error.
        """
        command = DispatchSwarmTurnCommandDto(
            snapshot_request_id=request.snapshot_request_id,
            snapshot_id=request.snapshot_id,
            activity_id=request.activity_id,
            default_worktree_path=request.default_worktree_path,
            lease_id=request.lease_id,
            lease_revision=request.lease_revision,
            lease_expires_at_ms=request.lease_expires_at_ms,
            mcp_grant=request.mcp_grant.to_inner_dto() if request.mcp_grant is not None else None,
            permissions=request.permissions.to_inner_dto(),
            timeouts=request.timeouts.to_inner_dto(),
            dispatched_at_ms=request.dispatched_at_ms,
            clean_exit_output_commit_oid=request.clean_exit_output_commit_oid,
            clean_exit_output_tree_blake3_hex=request.clean_exit_output_tree_blake3_hex,
            forge_session_id=request.forge_session_id,
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/dispatch",
            parse_result=partial(
                _parse_dispatch_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
                snapshot_id=request.snapshot_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=build_dispatch_exchange_policy(
                request=request, timeout_floor_seconds=timeout_floor_seconds
            ),
        )
        return result

    async def switch_member_model(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: SwitchSwarmMemberModelRequest,
    ) -> OrchestrationOutcomeDto[SwarmModelSwitchResponseDict]:
        """Switch one quota-suspended member to a source-supported Profile target.

        Args:
            workspace_id: Workspace identity selected by the route.
            swarm_run_id: Swarm run identity selected by the route.
            member_id: Member identity selected by the route.
            request: Strict source-compatible model-switch request.
        Return:
            Original HTTP status and typed model-switch result or backend error.
        """
        command = SwitchSwarmMemberModelCommandDto(
            new_profile_id=request.new_profile_id,
            request_id=request.request_id,
            profile_id=request.profile_id,
            expected_profile_revision=request.expected_profile_revision,
            new_preference=(
                request.new_preference.to_inner_dto()
                if request.new_preference is not None
                else None
            ),
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/model-switch",
            parse_result=partial(
                _parse_model_switch_result,
                workspace_id=workspace_id,
                swarm_run_id=swarm_run_id,
                member_id=member_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result
