"""Wire parsers and identity validators for the Native Swarm run lane."""

from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.inner_dto.swarm.swarm_run_inner_dto import (
    CreateSwarmRunInnerDto,
    KillSwarmMemberInnerDto,
    SubscribeSwarmChannelInnerDto,
    SwarmRunInspectionInnerDto,
    SwarmRunListInnerDto,
)
from app.orchestration.application.inner_dto.swarm.swarm_state_inner_dto import (
    SwarmChannelDto,
    SwarmMemberDto,
    SwarmRunDto,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_run_types import (
    CreateSwarmRunResponseDict,
    KillSwarmMemberResponseDict,
    SubscribeSwarmChannelResponseDict,
    SwarmRunInspectionResponseDict,
    SwarmRunListResponseDict,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import (
    SwarmChannelDict,
    SwarmMemberDict,
)
from app.orchestration.application.orchestration_wire_parsers import (
    parse_wire_array,
    require_wire_object,
    wire_optional,
)
from app.orchestration.application.swarm.swarm_state_parsers import (
    parse_swarm_channel,
    parse_swarm_channel_subscription,
    parse_swarm_doorbell,
    parse_swarm_member,
    parse_swarm_run,
)
from app.orchestration.application.swarm.swarm_verification_parsers import (
    parse_swarm_verdict,
    parse_swarm_verification_panel,
)
from app.orchestration.schema.swarm.orchestration_swarm_run_schema import (
    CreateSwarmRunRequest,
    SubscribeSwarmChannelResponse,
    SwarmChannelScopeIdentity,
    SwarmMemberScopeIdentity,
    SwarmRunScopeIdentity,
    SwarmSubscriptionPathIdentity,
)
from app.shared.exception import OrchestrationExcept
from app.shared.types.threaded_mapping import threaded_map


def validate_create_scope(workspace_id: UUID, request: CreateSwarmRunRequest) -> None:
    """Match the source client's Workspace-scope request preflight.

    Args:
        workspace_id: Workspace selected by the Gateway path.
        request: Strict public Swarm run command.
    Return:
        None.
    """
    scope = request.scope
    if scope is not None and (scope.workspace_id != workspace_id or scope.location_id.int == 0):
        raise OrchestrationExcept(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="orchestration_invalid_request",
            message="Swarm scope does not match the Workspace path or has a nil Location identity",
            retryable=False,
            workspace_id=workspace_id,
        )


def validate_create_swarm_run_status(
    status_code: int,
    result: CreateSwarmRunResponseDict,
) -> None:
    """Keep new-run and exact-replay source statuses paired with replay state.

    Args:
        status_code: Original Orchestration HTTP status.
        result: Parsed create or replay result.
    Return:
        None.
    """
    expected_status = status.HTTP_200_OK if result["run"]["replayed"] else status.HTTP_201_CREATED
    if status_code != expected_status:
        raise ValueError("Swarm run replay marker does not match source HTTP status")


def parse_create_swarm_run(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
) -> CreateSwarmRunResponseDict:
    """Parse and echo-check a Swarm run create response.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Workspace selected by the Gateway path.
    Return:
        Typed create result with normalized source-omitted optional values.
    """
    payload = require_wire_object(
        payload=value, required_keys=("run", "mainChannel"), optional_keys=()
    )
    run = parse_swarm_run(value=payload["run"])
    channel = parse_swarm_channel(value=payload["mainChannel"])
    _require_run_scope(expected_workspace_id=expected_workspace_id, run=run)
    _require_channel_scope(
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=run.swarm_run_id,
        channel=channel,
    )
    result = CreateSwarmRunInnerDto(run=run, main_channel=channel).to_dict()
    return result


def parse_swarm_run_list(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    max_result_count: int,
) -> SwarmRunListResponseDict:
    """Parse and workspace-check one bounded run list.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Workspace selected by the Gateway path.
        max_result_count: Maximum number of results selected by the source query.
    Return:
        Typed Swarm run list result.
    """
    payload = require_wire_object(payload=value, required_keys=("runs",), optional_keys=())
    raw_runs = parse_wire_array(value=payload["runs"], label="runs")
    if len(raw_runs) > max_result_count:
        raise ValueError("Swarm run list exceeded the requested result limit")
    runs = tuple(threaded_map(function=parse_swarm_run, values=raw_runs))
    for run in runs:
        _require_run_scope(expected_workspace_id=expected_workspace_id, run=run)
    result = SwarmRunListInnerDto(runs=runs).to_dict()
    return result


def parse_swarm_run_inspection(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
) -> SwarmRunInspectionResponseDict:
    """Parse a full inspection and check every source run scope echo.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
    Return:
        Typed immutable inspection snapshot.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=(
            "run",
            "channels",
            "members",
            "subscriptions",
            "pendingDoorbells",
            "verdicts",
        ),
        optional_keys=("verificationPanel",),
    )
    run = parse_swarm_run(value=payload["run"])
    channels = tuple(
        threaded_map(
            function=parse_swarm_channel,
            values=parse_wire_array(value=payload["channels"], label="channels"),
        )
    )
    members = tuple(
        threaded_map(
            function=parse_swarm_member,
            values=parse_wire_array(value=payload["members"], label="members"),
        )
    )
    subscriptions = tuple(
        threaded_map(
            function=parse_swarm_channel_subscription,
            values=parse_wire_array(value=payload["subscriptions"], label="subscriptions"),
        )
    )
    doorbells = tuple(
        threaded_map(
            function=parse_swarm_doorbell,
            values=parse_wire_array(value=payload["pendingDoorbells"], label="pendingDoorbells"),
        )
    )
    panel = wire_optional(
        value=payload.get("verificationPanel"), parser=parse_swarm_verification_panel
    )
    verdicts = tuple(
        threaded_map(
            function=parse_swarm_verdict,
            values=parse_wire_array(value=payload["verdicts"], label="verdicts"),
        )
    )
    _require_run_path_identity(
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=expected_swarm_run_id,
        observed_workspace_id=run.workspace_id,
        observed_swarm_run_id=run.swarm_run_id,
    )
    for channel in channels:
        _require_channel_scope(
            expected_workspace_id=expected_workspace_id,
            expected_swarm_run_id=expected_swarm_run_id,
            channel=channel,
        )
    for member in members:
        _require_member_scope(
            expected_workspace_id=expected_workspace_id,
            expected_swarm_run_id=expected_swarm_run_id,
            member=member,
        )
    for doorbell in doorbells:
        if doorbell.swarm_run_id != expected_swarm_run_id:
            raise ValueError("Swarm doorbell run identity does not match its path")
    for verdict in verdicts:
        if verdict.swarm_run_id != expected_swarm_run_id:
            raise ValueError("Swarm verdict run identity does not match its path")
    if panel is not None:
        _require_run_path_identity(
            expected_workspace_id=expected_workspace_id,
            expected_swarm_run_id=expected_swarm_run_id,
            observed_workspace_id=panel.workspace_id,
            observed_swarm_run_id=panel.swarm_run_id,
        )
    result = SwarmRunInspectionInnerDto(
        run=run,
        channels=channels,
        members=members,
        subscriptions=subscriptions,
        pending_doorbells=doorbells,
        verification_panel=panel,
        verdicts=verdicts,
    ).to_dict()
    return result


def parse_created_channel(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_channel_id: UUID,
) -> SwarmChannelDict:
    """Parse and check one created channel response.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        expected_channel_id: Channel identity from the public request.
    Return:
        Typed channel response.
    """
    channel = parse_swarm_channel(value=value)
    _require_channel_path_identity(
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=expected_swarm_run_id,
        expected_channel_id=expected_channel_id,
        channel=channel,
    )
    result = channel.to_dict()
    return result


def parse_subscribe_swarm_channel(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_channel_id: UUID,
    expected_member_id: UUID,
) -> SubscribeSwarmChannelResponseDict:
    """Parse and path-check one channel subscription response.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        expected_channel_id: Channel selected by the Gateway path.
        expected_member_id: Member selected by the request body.
    Return:
        Typed subscription result.
    """
    source = require_wire_object(
        payload=value,
        required_keys=("swarmRunId", "channelId", "memberId", "newlySubscribed"),
        optional_keys=(),
    )
    response = SubscribeSwarmChannelResponse.model_validate(source)
    _require_subscription_path_identity(
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=expected_swarm_run_id,
        expected_channel_id=expected_channel_id,
        expected_member_id=expected_member_id,
        response=response,
    )
    result = SubscribeSwarmChannelInnerDto(
        swarm_run_id=response.swarm_run_id,
        channel_id=response.channel_id,
        member_id=response.member_id,
        newly_subscribed=response.newly_subscribed,
    ).to_dict()
    return result


def parse_added_member(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_member_id: UUID,
) -> SwarmMemberDict:
    """Parse and path-check one added member response.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        expected_member_id: Member identity from the public request.
    Return:
        Typed member response.
    """
    member = parse_swarm_member(value=value)
    _require_member_path_identity(
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=expected_swarm_run_id,
        expected_member_id=expected_member_id,
        member=member,
    )
    result = member.to_dict()
    return result


def parse_killed_members(
    value: JsonValue,
    *,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_member_id: UUID,
) -> KillSwarmMemberResponseDict:
    """Parse and scope-check the target and cascade-killed members.

    Args:
        value: Decoded Orchestration response JSON.
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        expected_member_id: Target member selected by the Gateway path.
    Return:
        Typed killed-member result.
    """
    payload = require_wire_object(payload=value, required_keys=("killedMembers",), optional_keys=())
    members = tuple(
        threaded_map(
            function=parse_swarm_member,
            values=parse_wire_array(value=payload["killedMembers"], label="killedMembers"),
        )
    )
    for member in members:
        _require_member_scope(
            expected_workspace_id=expected_workspace_id,
            expected_swarm_run_id=expected_swarm_run_id,
            member=member,
        )
    if not any(member.member_id == expected_member_id for member in members):
        raise ValueError("Swarm kill response omitted the requested member")
    result = KillSwarmMemberInnerDto(killed_members=members).to_dict()
    return result


def _require_run_scope(expected_workspace_id: UUID, run: SwarmRunDto) -> None:
    """Require one source run to remain inside the requested Workspace.

    Args:
        expected_workspace_id: Workspace selected by the Gateway path.
        run: Parsed source run record.
    Return:
        None.
    """
    expected = SwarmRunScopeIdentity(
        workspace_id=expected_workspace_id,
        swarm_run_id=run.swarm_run_id,
    )
    observed = SwarmRunScopeIdentity(
        workspace_id=run.workspace_id,
        swarm_run_id=run.swarm_run_id,
    )
    if expected != observed or run.swarm_run_id.int == 0:
        raise ValueError("Swarm run response identity does not match its Workspace path")


def _require_run_path_identity(
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    observed_workspace_id: UUID,
    observed_swarm_run_id: UUID,
) -> None:
    """Require a source run identity to match both Gateway path coordinates.

    Args:
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        observed_workspace_id: Workspace echoed by Orchestration.
        observed_swarm_run_id: Swarm run echoed by Orchestration.
    Return:
        None.
    """
    expected = SwarmRunScopeIdentity(
        workspace_id=expected_workspace_id,
        swarm_run_id=expected_swarm_run_id,
    )
    observed = SwarmRunScopeIdentity(
        workspace_id=observed_workspace_id,
        swarm_run_id=observed_swarm_run_id,
    )
    if expected != observed:
        raise ValueError("Swarm response identity does not match its Workspace and run path")


def _require_channel_scope(
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    channel: SwarmChannelDto,
) -> None:
    """Require one source channel to remain inside the requested run.

    Args:
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        channel: Parsed source channel record.
    Return:
        None.
    """
    _require_channel_path_identity(
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=expected_swarm_run_id,
        expected_channel_id=channel.channel_id,
        channel=channel,
    )


def _require_channel_path_identity(
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_channel_id: UUID,
    channel: SwarmChannelDto,
) -> None:
    """Require one channel identity to echo its route and request.

    Args:
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        expected_channel_id: Channel identity selected by the request.
        channel: Parsed source channel record.
    Return:
        None.
    """
    expected = SwarmChannelScopeIdentity(
        workspace_id=expected_workspace_id,
        swarm_run_id=expected_swarm_run_id,
        channel_id=expected_channel_id,
    )
    observed = SwarmChannelScopeIdentity(
        workspace_id=channel.workspace_id,
        swarm_run_id=channel.swarm_run_id,
        channel_id=channel.channel_id,
    )
    if expected != observed or channel.channel_id.int == 0:
        raise ValueError("Swarm channel response identity does not match its route and request")


def _require_member_scope(
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    member: SwarmMemberDto,
) -> None:
    """Require one source member to remain inside the requested run.

    Args:
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        member: Parsed source member record.
    Return:
        None.
    """
    _require_member_path_identity(
        expected_workspace_id=expected_workspace_id,
        expected_swarm_run_id=expected_swarm_run_id,
        expected_member_id=member.member_id,
        member=member,
    )


def _require_member_path_identity(
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_member_id: UUID,
    member: SwarmMemberDto,
) -> None:
    """Require one member identity to echo its route and request.

    Args:
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        expected_member_id: Member identity selected by the route or request.
        member: Parsed source member record.
    Return:
        None.
    """
    expected = SwarmMemberScopeIdentity(
        workspace_id=expected_workspace_id,
        swarm_run_id=expected_swarm_run_id,
        member_id=expected_member_id,
    )
    observed = SwarmMemberScopeIdentity(
        workspace_id=member.workspace_id,
        swarm_run_id=member.swarm_run_id,
        member_id=member.member_id,
    )
    if expected != observed or member.member_id.int == 0:
        raise ValueError("Swarm member response identity does not match its route and request")


def _require_subscription_path_identity(
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_channel_id: UUID,
    expected_member_id: UUID,
    response: SubscribeSwarmChannelResponse,
) -> None:
    """Require one subscription result to match its path/body identities.

    Args:
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm run selected by the Gateway path.
        expected_channel_id: Channel selected by the Gateway path.
        expected_member_id: Member selected by the request body.
        response: Validated source subscription result.
    Return:
        None.
    """
    expected = SwarmSubscriptionPathIdentity(
        workspace_id=expected_workspace_id,
        swarm_run_id=expected_swarm_run_id,
        channel_id=expected_channel_id,
        member_id=expected_member_id,
    )
    observed = SwarmSubscriptionPathIdentity(
        workspace_id=expected_workspace_id,
        swarm_run_id=response.swarm_run_id,
        channel_id=response.channel_id,
        member_id=response.member_id,
    )
    if expected != observed:
        raise ValueError("Swarm subscription result identity does not match its route and request")
