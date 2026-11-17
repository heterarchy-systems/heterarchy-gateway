"""Normalize Native Swarm board replies and enforce source client fences."""

from collections.abc import Mapping
from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.autonomy_wire_utils import require_wire_object
from app.orchestration.application.inner_dto.swarm_board_inner_dto import (
    ConvergeSwarmResponseDict,
    ConvergeSwarmResponseDto,
    PostSwarmMessageResponseDict,
    PostSwarmMessageResponseDto,
    SwarmBoardPageResponseDict,
    SwarmBoardPageResponseDto,
    SwarmStallCheckResponseDict,
    SwarmStallCheckResponseDto,
)
from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
    SwarmBoardMessageDto,
    SwarmMemberDto,
    SwarmRunDict,
    SwarmRunDto,
    SwarmVerdictDict,
    SwarmVerificationPanelDict,
)
from app.orchestration.application.swarm_state_parsers import (
    parse_swarm_board_message,
    parse_swarm_convergence_gate,
    parse_swarm_member,
    parse_swarm_run,
    parse_swarm_verdict,
    parse_swarm_verification_panel,
)
from app.orchestration.schema.swarm.orchestration_swarm_board_schema import SwarmBoardMessagesFilter
from app.orchestration.schema.types.orchestration_types import UInt32
from app.shared.ingredient_element.orchestration.swarm_enums import SwarmRunStateEnum
from app.shared.types.threaded_mapping import threaded_map
from app.shared.types.wire_scalar_types import parse_wire_enum, parse_wire_uuid

_POST_MESSAGE_REQUIRED_KEYS = (
    "message",
    "wokenMemberIds",
    "coalescedDoorbellMemberIds",
    "replayed",
)
_BOARD_PAGE_REQUIRED_KEYS = ("messages", "hasMore")
_BOARD_PAGE_OPTIONAL_KEYS = ("nextAfterSequence",)
_CONVERGENCE_REQUIRED_KEYS = ("run", "settled")
_CONVERGENCE_OPTIONAL_KEYS = ("gate",)
_STALL_REQUIRED_KEYS = ("action",)
_STALL_OPTIONAL_KEYS = (
    "stoppedMembers",
    "runState",
    "workingMembers",
    "targetMemberId",
    "bottleneckReason",
    "livelockReason",
    "observedPingPongStreak",
    "observedMemberTurns",
    "run",
    "emittedMessage",
)
_MAX_SWARM_BOARD_PAGE_SIZE = 128


def _required_boolean(payload: Mapping[str, JsonValue], key: str) -> bool:
    """Read one source boolean without accepting numeric aliases.

    Args:
        payload: Exact response object.
        key: Required response property.
    Return:
        Exact source boolean value.
    """
    value = payload[key]
    if type(value) is not bool:
        raise ValueError(f"Swarm field {key} must be a boolean")
    result = value
    return result


def _required_string(payload: Mapping[str, JsonValue], key: str) -> str:
    """Read one required source string without coercion.

    Args:
        payload: Exact response object.
        key: Required response property.
    Return:
        Exact source string.
    """
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError(f"Swarm field {key} must be a string")
    result = value
    return result


def _optional_string(payload: Mapping[str, JsonValue], key: str) -> str | None:
    """Read one optional string source field as required nullable data.

    Args:
        payload: Response object allowing the source skip key.
        key: Optional response property.
    Return:
        Source string or None when omitted or null.
    """
    value = payload.get(key)
    if value is None:
        result = None
    elif isinstance(value, str):
        result = value
    else:
        raise ValueError(f"Swarm field {key} must be a string or null")
    return result


def _optional_integer(payload: Mapping[str, JsonValue], key: str) -> int | None:
    """Read one optional integer without accepting booleans.

    Args:
        payload: Response object allowing the source skip key.
        key: Optional response property.
    Return:
        Source integer or None when omitted or null.
    """
    value = payload.get(key)
    if value is None:
        result = None
    elif type(value) is int:
        result = value
    else:
        raise ValueError(f"Swarm field {key} must be an integer or null")
    return result


def _optional_uuid(payload: Mapping[str, JsonValue], key: str) -> UUID | None:
    """Read one optional UUID source field as required nullable data.

    Args:
        payload: Response object allowing the source skip key.
        key: Optional response property.
    Return:
        Parsed source UUID or None when omitted or null.
    """
    value = payload.get(key)
    if value is None:
        result = None
    else:
        result = parse_wire_uuid(value=value)
    return result


def _required_uuid_tuple(payload: Mapping[str, JsonValue], key: str) -> tuple[UUID, ...]:
    """Parse a required source array of UUID strings.

    Args:
        payload: Exact response object.
        key: Required response property.
    Return:
        Immutable parsed UUID sequence.
    """
    value = payload[key]
    if not isinstance(value, list):
        raise ValueError(f"Swarm field {key} must be an array")
    result = tuple(parse_wire_uuid(value=item) for item in value)
    return result


def _required_message_tuple(
    payload: Mapping[str, JsonValue],
    key: str,
) -> tuple[SwarmBoardMessageDto, ...]:
    """Parse a required list of canonical source board messages.

    Args:
        payload: Exact response object.
        key: Required response property.
    Return:
        Immutable parsed board messages.
    """
    value = payload[key]
    if not isinstance(value, list):
        raise ValueError(f"Swarm field {key} must be an array")
    result = tuple(threaded_map(function=parse_swarm_board_message, values=value))
    return result


def _default_member_tuple(payload: Mapping[str, JsonValue], key: str) -> tuple[SwarmMemberDto, ...]:
    """Apply the source deserializer's empty-array default for stopped members.

    Args:
        payload: Stall response allowing an omitted default field.
        key: Source stopped-members property.
    Return:
        Immutable source members or an empty sequence when omitted.
    """
    value = payload.get(key, [])
    if not isinstance(value, list):
        raise ValueError(f"Swarm field {key} must be an array")
    result = tuple(parse_swarm_member(value=item) for item in value)
    return result


def _require_valid_run(run: SwarmRunDto, workspace_id: UUID, swarm_run_id: UUID) -> None:
    """Apply the source client run validity and path identity checks.

    Args:
        run: Parsed source run record.
        workspace_id: Expected path workspace UUID.
        swarm_run_id: Expected path run UUID.
    Return:
        None.
    """
    if (
        run.swarm_run_id.int == 0
        or run.workspace_id != workspace_id
        or run.swarm_run_id != swarm_run_id
    ):
        raise ValueError("Swarm run response path identity mismatch")
    if not run.title or run.revision < 1 or run.created_at_ms < 0:
        raise ValueError("Swarm run response failed source validity checks")
    if run.updated_at_ms < run.created_at_ms:
        raise ValueError("Swarm run response update time precedes creation time")


def _validate_replay_status(status_code: int, replayed: bool) -> None:
    """Require status code to agree with source replay metadata.

    Args:
        status_code: Original Orchestration success status.
        replayed: Source idempotency replay flag.
    Return:
        None.
    """
    expected_status = status.HTTP_200_OK if replayed else status.HTTP_201_CREATED
    if status_code != expected_status:
        raise ValueError("Swarm replay metadata does not match source HTTP status")


def validate_post_message_status(
    status_code: int,
    response: PostSwarmMessageResponseDict,
) -> None:
    """Validate message post status against its replay flag.

    Args:
        status_code: Original Orchestration success status.
        response: Typed message post response.
    Return:
        None.
    """
    _validate_replay_status(status_code=status_code, replayed=response["replayed"])


def validate_panel_status(status_code: int, response: SwarmVerificationPanelDict) -> None:
    """Validate panel creation status against its replay flag.

    Args:
        status_code: Original Orchestration success status.
        response: Typed verification panel response.
    Return:
        None.
    """
    _validate_replay_status(status_code=status_code, replayed=response["replayed"])


def validate_verdict_status(status_code: int, response: SwarmVerdictDict) -> None:
    """Validate verdict recording status against its replay flag.

    Args:
        status_code: Original Orchestration success status.
        response: Typed verifier verdict response.
    Return:
        None.
    """
    _validate_replay_status(status_code=status_code, replayed=response["replayed"])


def parse_post_message_result(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_message_id: UUID,
    expected_channel_id: UUID | None,
    expected_author_member_id: UUID | None,
) -> PostSwarmMessageResponseDict:
    """Parse post response and enforce the source client correlation fences.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Exact Workspace path UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
        expected_message_id: Exact message UUID from the request.
        expected_channel_id: Explicit requested channel, when supplied.
        expected_author_member_id: Requested author or system None.
    Return:
        Complete typed board message result.
    """
    payload = require_wire_object(
        payload=value, required_keys=_POST_MESSAGE_REQUIRED_KEYS, optional_keys=()
    )
    message = parse_swarm_board_message(value=payload["message"])
    if message.message_id != expected_message_id or message.sequence == 0:
        raise ValueError("Swarm message response identity or sequence mismatch")
    if (
        message.workspace_id != expected_workspace_id
        or message.swarm_run_id != expected_swarm_run_id
    ):
        raise ValueError("Swarm message response path identity mismatch")
    if expected_channel_id is not None and message.channel_id != expected_channel_id:
        raise ValueError("Swarm message response channel mismatch")
    if message.author_member_id != expected_author_member_id:
        raise ValueError("Swarm message response author mismatch")
    result = PostSwarmMessageResponseDto(
        message=message,
        woken_member_ids=_required_uuid_tuple(payload=payload, key="wokenMemberIds"),
        coalesced_doorbell_member_ids=_required_uuid_tuple(
            payload=payload, key="coalescedDoorbellMemberIds"
        ),
        replayed=_required_boolean(payload=payload, key="replayed"),
    ).to_dict()
    return result


def parse_board_page_result(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    filters: SwarmBoardMessagesFilter,
) -> SwarmBoardPageResponseDict:
    """Parse one board page and enforce source cursor, channel, order and count.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Exact Workspace path UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
        filters: Validated board query filters.
    Return:
        Complete typed incremental board page.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=_BOARD_PAGE_REQUIRED_KEYS,
        optional_keys=_BOARD_PAGE_OPTIONAL_KEYS,
    )
    messages = _required_message_tuple(payload=payload, key="messages")
    next_sequence = _optional_integer(payload=payload, key="nextAfterSequence")
    page = SwarmBoardPageResponseDto(
        messages=messages,
        next_after_sequence=next_sequence,
        has_more=_required_boolean(payload=payload, key="hasMore"),
    )
    _validate_board_page(
        page=page,
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=expected_swarm_run_id,
        filters=filters,
    )
    result = page.to_dict()
    return result


def _validate_board_page(
    page: SwarmBoardPageResponseDto,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    filters: SwarmBoardMessagesFilter,
) -> None:
    """Apply the source client's bounded, strictly increasing page checks.

    Args:
        page: Parsed immutable source page.
        expected_workspace_id: Exact Workspace path UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
        filters: Validated request query filters.
    Return:
        None.
    """
    result_limit = filters.limit if filters.limit is not None else _MAX_SWARM_BOARD_PAGE_SIZE
    since_sequence = filters.since_sequence if filters.since_sequence is not None else 0
    if len(page.messages) > result_limit:
        raise ValueError("Swarm board page exceeded the requested limit")
    for message in page.messages:
        if message.message_id.int == 0:
            raise ValueError("Swarm board page contains a nil message ID")
        if (
            message.workspace_id != expected_workspace_id
            or message.swarm_run_id != expected_swarm_run_id
        ):
            raise ValueError("Swarm board page contains a foreign path identity")
        if message.sequence <= since_sequence:
            raise ValueError("Swarm board page contains a message at or before its cursor")
        if filters.channel_id is not None and message.channel_id != filters.channel_id:
            raise ValueError("Swarm board page contains a message outside the requested channel")
    for previous, current in zip(page.messages, page.messages[1:], strict=False):
        if previous.sequence >= current.sequence:
            raise ValueError("Swarm board page messages are not strictly increasing")


def parse_panel_result(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_required_quorum: UInt32,
) -> SwarmVerificationPanelDict:
    """Parse a verification panel and validate its source correlation.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Exact Workspace path UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
        expected_required_quorum: Quorum supplied by the request.
    Return:
        Complete typed verification panel.
    """
    panel = parse_swarm_verification_panel(value=value)
    if panel.panel_id.int == 0:
        raise ValueError("Swarm panel response has a nil panel ID")
    if panel.workspace_id != expected_workspace_id or panel.swarm_run_id != expected_swarm_run_id:
        raise ValueError("Swarm panel response path identity mismatch")
    if panel.required_quorum != expected_required_quorum:
        raise ValueError("Swarm panel response quorum mismatch")
    result = panel.to_dict()
    return result


def parse_verdict_result(
    value: JsonValue,
    *,
    expected_request_id: UUID,
    expected_swarm_run_id: UUID,
    expected_verifier_member_id: UUID,
    expected_panel_id: UUID | None,
) -> SwarmVerdictDict:
    """Parse verdict response and validate request, verifier, run and panel.

    Args:
        value: Decoded Orchestration response JSON.
        expected_request_id: Exact request UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
        expected_verifier_member_id: Exact verifier UUID from the request.
        expected_panel_id: Explicit panel UUID, when supplied.
    Return:
        Complete typed verifier verdict.
    """
    verdict = parse_swarm_verdict(value=value)
    if verdict.verdict_id.int == 0 or verdict.panel_id.int == 0:
        raise ValueError("Swarm verdict response contains a nil verdict or panel ID")
    if verdict.request_id != expected_request_id or verdict.swarm_run_id != expected_swarm_run_id:
        raise ValueError("Swarm verdict response request or run identity mismatch")
    if verdict.verifier_member_id != expected_verifier_member_id:
        raise ValueError("Swarm verdict response verifier identity mismatch")
    if expected_panel_id is not None and verdict.panel_id != expected_panel_id:
        raise ValueError("Swarm verdict response panel identity mismatch")
    result = verdict.to_dict()
    return result


def parse_convergence_result(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
) -> ConvergeSwarmResponseDict:
    """Parse convergence response and validate the changed run identity.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Exact Workspace path UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
    Return:
        Complete typed convergence response.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=_CONVERGENCE_REQUIRED_KEYS,
        optional_keys=_CONVERGENCE_OPTIONAL_KEYS,
    )
    run = parse_swarm_run(value=payload["run"])
    _require_valid_run(
        run=run, workspace_id=expected_workspace_id, swarm_run_id=expected_swarm_run_id
    )
    gate_value = payload.get("gate")
    gate = parse_swarm_convergence_gate(value=gate_value) if gate_value is not None else None
    result = ConvergeSwarmResponseDto(
        run=run,
        settled=_required_boolean(payload=payload, key="settled"),
        gate=gate,
    ).to_dict()
    return result


def parse_settlement_result(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
) -> ConvergeSwarmResponseDict:
    """Parse settlement response and require its settled result.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Exact Workspace path UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
    Return:
        Complete typed settlement response.
    """
    result = parse_convergence_result(
        value=value,
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=expected_swarm_run_id,
    )
    if not result["settled"]:
        raise ValueError("Swarm settlement response did not mark the run settled")
    return result


def parse_abort_result(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
) -> SwarmRunDict:
    """Parse aborted run and validate source path identity and run validity.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Exact Workspace path UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
    Return:
        Complete typed Swarm run response.
    """
    run = parse_swarm_run(value=value)
    _require_valid_run(
        run=run, workspace_id=expected_workspace_id, swarm_run_id=expected_swarm_run_id
    )
    result = run.to_dict()
    return result


def parse_stall_check_result(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
) -> SwarmStallCheckResponseDict:
    """Parse a stall report and enforce source action and optional run identity.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Exact Workspace path UUID.
        expected_swarm_run_id: Exact Swarm run path UUID.
    Return:
        Complete typed deterministic stall report.
    """
    payload = require_wire_object(
        payload=value, required_keys=_STALL_REQUIRED_KEYS, optional_keys=_STALL_OPTIONAL_KEYS
    )
    action = _required_string(payload=payload, key="action")
    if not action:
        raise ValueError("Swarm stall response action must not be empty")
    run_value = payload.get("run")
    run = parse_swarm_run(value=run_value) if run_value is not None else None
    if run is not None:
        _require_valid_run(
            run=run, workspace_id=expected_workspace_id, swarm_run_id=expected_swarm_run_id
        )
    stopped_members = _default_member_tuple(payload=payload, key="stoppedMembers")
    message_value = payload.get("emittedMessage")
    emitted_message = (
        parse_swarm_board_message(value=message_value) if message_value is not None else None
    )
    run_state_value = payload.get("runState")
    run_state = (
        parse_wire_enum(enum_type=SwarmRunStateEnum, value=run_state_value)
        if run_state_value is not None
        else None
    )
    result = SwarmStallCheckResponseDto(
        action=action,
        run_state=run_state,
        working_members=_optional_integer(payload=payload, key="workingMembers"),
        target_member_id=_optional_uuid(payload=payload, key="targetMemberId"),
        bottleneck_reason=_optional_string(payload=payload, key="bottleneckReason"),
        livelock_reason=_optional_string(payload=payload, key="livelockReason"),
        observed_ping_pong_streak=_optional_integer(payload=payload, key="observedPingPongStreak"),
        observed_member_turns=_optional_integer(payload=payload, key="observedMemberTurns"),
        run=run,
        stopped_members=stopped_members,
        emitted_message=emitted_message,
    ).to_dict()
    return result
