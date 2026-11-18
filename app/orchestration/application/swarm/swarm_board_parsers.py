"""Normalize Native Swarm board replies and enforce source client fences."""

from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.inner_dto.swarm.swarm_board_inner_dto import (
    ConvergeSwarmResponseDto,
    PostSwarmMessageResponseDto,
    SwarmBoardPageResponseDto,
    SwarmStallCheckResponseDto,
)
from app.orchestration.application.inner_dto.swarm.swarm_state_inner_dto import SwarmRunDto
from app.orchestration.application.inner_dto.types.swarm.swarm_board_types import (
    ConvergeSwarmResponseDict,
    PostSwarmMessageResponseDict,
    SwarmBoardPageResponseDict,
    SwarmStallCheckResponseDict,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import (
    SwarmRunDict,
    SwarmVerdictDict,
    SwarmVerificationPanelDict,
)
from app.orchestration.application.orchestration_wire_parsers import (
    UINT32_MAX,
    UINT64_MAX,
    parse_wire_array,
    parse_wire_bool,
    parse_wire_int,
    parse_wire_object_items,
    parse_wire_str,
    parse_wire_uuid_tuple,
    require_wire_object,
    wire_optional,
)
from app.orchestration.application.swarm.swarm_state_parsers import (
    parse_swarm_board_message,
    parse_swarm_member,
    parse_swarm_run,
)
from app.orchestration.application.swarm.swarm_verification_parsers import (
    parse_swarm_convergence_gate,
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
        woken_member_ids=parse_wire_uuid_tuple(
            value=payload["wokenMemberIds"], label="wokenMemberIds"
        ),
        coalesced_doorbell_member_ids=parse_wire_uuid_tuple(
            value=payload["coalescedDoorbellMemberIds"],
            label="coalescedDoorbellMemberIds",
        ),
        replayed=parse_wire_bool(value=payload["replayed"], label="replayed"),
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
    message_items = parse_wire_array(value=payload["messages"], label="messages")
    messages = tuple(threaded_map(function=parse_swarm_board_message, values=message_items))
    next_sequence = wire_optional(
        value=payload.get("nextAfterSequence"),
        parser=partial(parse_wire_int, minimum=0, maximum=UINT64_MAX, label="nextAfterSequence"),
    )
    page = SwarmBoardPageResponseDto(
        messages=messages,
        next_after_sequence=next_sequence,
        has_more=parse_wire_bool(value=payload["hasMore"], label="hasMore"),
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
    gate = wire_optional(value=payload.get("gate"), parser=parse_swarm_convergence_gate)
    result = ConvergeSwarmResponseDto(
        run=run,
        settled=parse_wire_bool(value=payload["settled"], label="settled"),
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
    action = parse_wire_str(value=payload["action"], label="action")
    if not action:
        raise ValueError("Swarm stall response action must not be empty")
    run = wire_optional(value=payload.get("run"), parser=parse_swarm_run)
    if run is not None:
        _require_valid_run(
            run=run, workspace_id=expected_workspace_id, swarm_run_id=expected_swarm_run_id
        )
    stopped_members = parse_wire_object_items(
        value=payload.get("stoppedMembers", []),
        parser=parse_swarm_member,
        label="stoppedMembers",
    )
    emitted_message = wire_optional(
        value=payload.get("emittedMessage"), parser=parse_swarm_board_message
    )
    run_state = wire_optional(
        value=payload.get("runState"), parser=partial(parse_wire_enum, SwarmRunStateEnum)
    )
    result = SwarmStallCheckResponseDto(
        action=action,
        run_state=run_state,
        working_members=wire_optional(
            value=payload.get("workingMembers"),
            parser=partial(parse_wire_int, minimum=0, maximum=UINT64_MAX, label="workingMembers"),
        ),
        target_member_id=wire_optional(value=payload.get("targetMemberId"), parser=parse_wire_uuid),
        bottleneck_reason=wire_optional(
            value=payload.get("bottleneckReason"),
            parser=partial(parse_wire_str, label="bottleneckReason"),
        ),
        livelock_reason=wire_optional(
            value=payload.get("livelockReason"),
            parser=partial(parse_wire_str, label="livelockReason"),
        ),
        observed_ping_pong_streak=wire_optional(
            value=payload.get("observedPingPongStreak"),
            parser=partial(
                parse_wire_int,
                minimum=0,
                maximum=UINT32_MAX,
                label="observedPingPongStreak",
            ),
        ),
        observed_member_turns=wire_optional(
            value=payload.get("observedMemberTurns"),
            parser=partial(
                parse_wire_int,
                minimum=0,
                maximum=UINT64_MAX,
                label="observedMemberTurns",
            ),
        ),
        run=run,
        stopped_members=stopped_members,
        emitted_message=emitted_message,
    ).to_dict()
    return result
