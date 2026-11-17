"""Application operations for the Native Swarm run lane."""

from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.autonomy_wire_utils import require_wire_object
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.swarm_run_inner_dto import (
    AddSwarmMemberCommandDto,
    CreateSwarmChannelCommandDto,
    CreateSwarmRunCommandDto,
    CreateSwarmRunInnerDto,
    KillSwarmMemberCommandDto,
    KillSwarmMemberInnerDto,
    SubscribeSwarmChannelCommandDto,
    SubscribeSwarmChannelInnerDto,
    SwarmRunInspectionInnerDto,
    SwarmRunListInnerDto,
)
from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
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
from app.orchestration.application.orchestration_command_utils import (
    ORCHESTRATION_SWARM_EXCHANGE_POLICY,
    execute_orchestration_operation,
)
from app.orchestration.application.swarm_state_parsers import (
    parse_swarm_channel,
    parse_swarm_channel_subscription,
    parse_swarm_doorbell,
    parse_swarm_member,
    parse_swarm_run,
    parse_swarm_verdict,
    parse_swarm_verification_panel,
)
from app.orchestration.schema.swarm.orchestration_swarm_run_schema import (
    MAX_SWARM_RUN_LIST_SIZE,
    AddSwarmMemberRequest,
    CreateSwarmChannelRequest,
    CreateSwarmRunRequest,
    KillSwarmMemberRequest,
    SubscribeSwarmChannelRequest,
    SubscribeSwarmChannelResponse,
    SwarmChannelScopeIdentity,
    SwarmMemberScopeIdentity,
    SwarmRunListFilter,
    SwarmRunScopeIdentity,
    SwarmSubscriptionPathIdentity,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import OrchestrationExcept
from app.shared.types.base_types import JsonObject
from app.shared.types.threaded_mapping import threaded_map


class SwarmRunApplication:
    """Forward Native Swarm run operations without taking domain authority."""

    def __init__(self, calling: OrchestrationCalling) -> None:
        """Bind one request-scoped Orchestration caller.

        Args:
            calling: Request-scoped authenticated Orchestration caller.
        Return:
            None.
        """
        self._calling = calling

    async def create_swarm_run(
        self,
        workspace_id: UUID,
        request: CreateSwarmRunRequest,
    ) -> OrchestrationOutcomeDto[CreateSwarmRunResponseDict]:
        """Create or replay one Swarm run through Orchestration.

        Args:
            workspace_id: Workspace selected by the Gateway path.
            request: Strict public run command.
        Return:
            Source status and typed run creation result.
        """
        _validate_create_scope(workspace_id=workspace_id, request=request)
        command: CreateSwarmRunCommandDto = request.to_inner_dto()
        path = f"/v1/workspaces/{workspace_id}/swarms"
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=path,
            parse_result=partial(_parse_create_swarm_run, expected_workspace_id=workspace_id),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_201_CREATED),
            validate_result_status=_validate_create_swarm_run_status,
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def fetch_swarm_runs(
        self,
        workspace_id: UUID,
        filters: SwarmRunListFilter,
    ) -> OrchestrationOutcomeDto[SwarmRunListResponseDict]:
        """Read bounded Swarm runs for one Workspace.

        Args:
            workspace_id: Workspace selected by the Gateway path.
            filters: Optional bounded source query filter.
        Return:
            Source status and typed Swarm run list.
        """
        path = f"/v1/workspaces/{workspace_id}/swarms"
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="GET",
            path=path,
            parse_result=partial(
                _parse_swarm_run_list,
                expected_workspace_id=workspace_id,
                max_result_count=(
                    filters.limit if filters.limit is not None else MAX_SWARM_RUN_LIST_SIZE
                ),
            ),
            params=filters.to_query_params(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def inspect_swarm_run(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
    ) -> OrchestrationOutcomeDto[SwarmRunInspectionResponseDict]:
        """Read one full Swarm run inspection snapshot.

        Args:
            workspace_id: Workspace selected by the Gateway path.
            swarm_run_id: Swarm run selected by the Gateway path.
        Return:
            Source status and typed full inspection snapshot.
        """
        path = f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}"
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="GET",
            path=path,
            parse_result=partial(
                _parse_swarm_run_inspection,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
            ),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def create_swarm_channel(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: CreateSwarmChannelRequest,
    ) -> OrchestrationOutcomeDto[SwarmChannelDict]:
        """Create one channel in the selected Swarm run.

        Args:
            workspace_id: Workspace selected by the Gateway path.
            swarm_run_id: Swarm run selected by the Gateway path.
            request: Strict public channel command.
        Return:
            Source status and typed channel result.
        """
        command: CreateSwarmChannelCommandDto = request.to_inner_dto()
        path = f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/channels"
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=path,
            parse_result=partial(
                _parse_created_channel,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                expected_channel_id=request.channel_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_201_CREATED,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def subscribe_swarm_channel(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        channel_id: UUID,
        request: SubscribeSwarmChannelRequest,
    ) -> OrchestrationOutcomeDto[SubscribeSwarmChannelResponseDict]:
        """Subscribe one run member to the selected channel.

        Args:
            workspace_id: Workspace selected by the Gateway path.
            swarm_run_id: Swarm run selected by the Gateway path.
            channel_id: Channel selected by the Gateway path.
            request: Strict public subscription command.
        Return:
            Source status and typed subscription result.
        """
        command: SubscribeSwarmChannelCommandDto = request.to_inner_dto()
        path = (
            f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/channels/"
            f"{channel_id}/subscriptions"
        )
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=path,
            parse_result=partial(
                _parse_subscribe_swarm_channel,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                expected_channel_id=channel_id,
                expected_member_id=request.member_id,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def add_swarm_member(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: AddSwarmMemberRequest,
    ) -> OrchestrationOutcomeDto[SwarmMemberDict]:
        """Add one member to the selected Swarm run.

        Args:
            workspace_id: Workspace selected by the Gateway path.
            swarm_run_id: Swarm run selected by the Gateway path.
            request: Strict public member command.
        Return:
            Source status and typed member result.
        """
        command: AddSwarmMemberCommandDto = request.to_inner_dto()
        path = f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members"
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=path,
            parse_result=partial(
                _parse_added_member,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                expected_member_id=request.member_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_201_CREATED,),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def kill_swarm_member(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        member_id: UUID,
        request: KillSwarmMemberRequest,
    ) -> OrchestrationOutcomeDto[KillSwarmMemberResponseDict]:
        """Kill one member and return source-reported cascade members.

        Args:
            workspace_id: Workspace selected by the Gateway path.
            swarm_run_id: Swarm run selected by the Gateway path.
            member_id: Member selected by the Gateway path.
            request: Required empty public request body.
        Return:
            Source status and typed killed member result.
        """
        command: KillSwarmMemberCommandDto = request.to_inner_dto()
        path = f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/kill"
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=path,
            parse_result=partial(
                _parse_killed_members,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                expected_member_id=member_id,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result


def _parse_create_swarm_run(
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


def _validate_create_scope(workspace_id: UUID, request: CreateSwarmRunRequest) -> None:
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


def _validate_create_swarm_run_status(
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


def _parse_swarm_run_list(
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
    raw_runs = _required_array(payload=payload, key="runs")
    if len(raw_runs) > max_result_count:
        raise ValueError("Swarm run list exceeded the requested result limit")
    runs = tuple(threaded_map(function=parse_swarm_run, values=raw_runs))
    for run in runs:
        _require_run_scope(expected_workspace_id=expected_workspace_id, run=run)
    result = SwarmRunListInnerDto(runs=runs).to_dict()
    return result


def _parse_swarm_run_inspection(
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
            function=parse_swarm_channel, values=_required_array(payload=payload, key="channels")
        )
    )
    members = tuple(
        threaded_map(
            function=parse_swarm_member, values=_required_array(payload=payload, key="members")
        )
    )
    subscriptions = tuple(
        threaded_map(
            function=parse_swarm_channel_subscription,
            values=_required_array(payload=payload, key="subscriptions"),
        )
    )
    doorbells = tuple(
        threaded_map(
            function=parse_swarm_doorbell,
            values=_required_array(payload=payload, key="pendingDoorbells"),
        )
    )
    panel_value = payload.get("verificationPanel")
    panel = parse_swarm_verification_panel(value=panel_value) if panel_value is not None else None
    verdicts = tuple(
        threaded_map(
            function=parse_swarm_verdict, values=_required_array(payload=payload, key="verdicts")
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


def _parse_created_channel(
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


def _parse_subscribe_swarm_channel(
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


def _parse_added_member(
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


def _parse_killed_members(
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
            values=_required_array(payload=payload, key="killedMembers"),
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


def _required_array(payload: JsonObject, key: str) -> list[JsonValue]:
    """Extract one required source JSON array.

    Args:
        payload: Validated source JSON object.
        key: Required array field name.
    Return:
        Ordered JSON items for typed element parsing.
    """
    value = payload[key]
    if not isinstance(value, list):
        raise ValueError(f"Orchestration field {key} must be an array")
    result: list[JsonValue] = value
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
