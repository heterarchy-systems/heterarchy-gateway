"""Application operations for the Native Swarm run lane."""

from functools import partial
from uuid import UUID

from fastapi import status

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.swarm.swarm_run_inner_dto import (
    AddSwarmMemberCommandDto,
    CreateSwarmChannelCommandDto,
    CreateSwarmRunCommandDto,
    KillSwarmMemberCommandDto,
    SubscribeSwarmChannelCommandDto,
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
from app.orchestration.application.swarm.swarm_run_parsers import (
    parse_added_member,
    parse_create_swarm_run,
    parse_created_channel,
    parse_killed_members,
    parse_subscribe_swarm_channel,
    parse_swarm_run_inspection,
    parse_swarm_run_list,
    validate_create_scope,
    validate_create_swarm_run_status,
)
from app.orchestration.schema.swarm.orchestration_swarm_run_schema import (
    MAX_SWARM_RUN_LIST_SIZE,
    AddSwarmMemberRequest,
    CreateSwarmChannelRequest,
    CreateSwarmRunRequest,
    KillSwarmMemberRequest,
    SubscribeSwarmChannelRequest,
    SwarmRunListFilter,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling


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
        validate_create_scope(workspace_id=workspace_id, request=request)
        command: CreateSwarmRunCommandDto = request.to_inner_dto()
        path = f"/v1/workspaces/{workspace_id}/swarms"
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=path,
            parse_result=partial(parse_create_swarm_run, expected_workspace_id=workspace_id),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_201_CREATED),
            validate_result_status=validate_create_swarm_run_status,
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
                parse_swarm_run_list,
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
                parse_swarm_run_inspection,
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
                parse_created_channel,
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
                parse_subscribe_swarm_channel,
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
                parse_added_member,
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
                parse_killed_members,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                expected_member_id=member_id,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result
