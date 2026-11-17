"""Typed HTTP entrypoints for Native Swarm run operations."""

from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends, Request, Response, status

from app.orchestration.application.swarm_run_app import SwarmRunApplication
from app.orchestration.exceptions.orchestration_exceptions import (
    ORCHESTRATION_ERROR_RESPONSES,
    OrchestrationBackendErrorResponse,
)
from app.orchestration.schema.swarm.orchestration_swarm_run_schema import (
    AddSwarmMemberRequest,
    CreateSwarmChannelRequest,
    CreateSwarmRunRequest,
    CreateSwarmRunResponse,
    KillSwarmMemberRequest,
    KillSwarmMemberResponse,
    SubscribeSwarmChannelRequest,
    SubscribeSwarmChannelResponse,
    SwarmRunInspectionResponse,
    SwarmRunListFilter,
    SwarmRunListResponse,
)
from app.orchestration.schema.swarm.orchestration_swarm_state_schema import (
    SwarmChannelSchema,
    SwarmMemberSchema,
)
from app.orchestration.schema.types.swarm_types import NonNilCanonicalSwarmUUID
from app.orchestration.utils.orchestration_route_utils import orchestration_http_response
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.types.http_types import ResponseModels
from app.shared.utils.query_validation import checked_query_filter

router = APIRouter(
    prefix="/workspaces/{workspace_id}/swarms",
    route_class=DishkaRoute,
)

_CREATE_RUN_RESPONSES: ResponseModels = {
    **ORCHESTRATION_ERROR_RESPONSES,
    status.HTTP_200_OK: {"model": CreateSwarmRunResponse},
}


@router.post(
    "",
    response_model=CreateSwarmRunResponse | OrchestrationBackendErrorResponse,
    responses=_CREATE_RUN_RESPONSES,
    status_code=status.HTTP_201_CREATED,
)
async def create_swarm_run_route(
    workspace_id: NonNilCanonicalSwarmUUID,
    payload: CreateSwarmRunRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> CreateSwarmRunResponse | OrchestrationBackendErrorResponse:
    """Create or replay one Swarm run.

    Args:
        workspace_id: Workspace selected by the Gateway path.
        payload: Strict Swarm run command.
        response: HTTP response carrying the original source status.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed run result or backend rejection.
    """
    outcome = await SwarmRunApplication(calling=calling).create_swarm_run(
        workspace_id=workspace_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=CreateSwarmRunResponse,
        workspace_id=workspace_id,
    )
    return result


@router.get(
    "",
    response_model=SwarmRunListResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
    status_code=status.HTTP_200_OK,
)
async def list_swarm_runs_route(
    workspace_id: NonNilCanonicalSwarmUUID,
    request: Request,
    response: Response,
    filters: Annotated[SwarmRunListFilter, Depends()],
    calling: FromDishka[OrchestrationCalling],
) -> SwarmRunListResponse | OrchestrationBackendErrorResponse:
    """List bounded Swarm runs in one Workspace.

    Args:
        workspace_id: Workspace selected by the Gateway path.
        request: Incoming HTTP request used to reject unknown query keys.
        response: HTTP response carrying the original source status.
        filters: Optional list limit bound to the query string.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed run list or backend rejection.
    """
    checked_filters = checked_query_filter(request=request, filters=filters)
    outcome = await SwarmRunApplication(calling=calling).fetch_swarm_runs(
        workspace_id=workspace_id, filters=checked_filters
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmRunListResponse,
        workspace_id=workspace_id,
    )
    return result


@router.get(
    "/{swarm_run_id}",
    response_model=SwarmRunInspectionResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
    status_code=status.HTTP_200_OK,
)
async def inspect_swarm_run_route(
    workspace_id: NonNilCanonicalSwarmUUID,
    swarm_run_id: NonNilCanonicalSwarmUUID,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmRunInspectionResponse | OrchestrationBackendErrorResponse:
    """Read one full Swarm run inspection snapshot.

    Args:
        workspace_id: Workspace selected by the Gateway path.
        swarm_run_id: Swarm run selected by the Gateway path.
        response: HTTP response carrying the original source status.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed inspection snapshot or backend rejection.
    """
    outcome = await SwarmRunApplication(calling=calling).inspect_swarm_run(
        workspace_id=workspace_id, swarm_run_id=swarm_run_id
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmRunInspectionResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{swarm_run_id}/channels",
    response_model=SwarmChannelSchema | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
    status_code=status.HTTP_201_CREATED,
)
async def create_swarm_channel_route(
    workspace_id: NonNilCanonicalSwarmUUID,
    swarm_run_id: NonNilCanonicalSwarmUUID,
    payload: CreateSwarmChannelRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmChannelSchema | OrchestrationBackendErrorResponse:
    """Create a channel inside one Swarm run.

    Args:
        workspace_id: Workspace selected by the Gateway path.
        swarm_run_id: Swarm run selected by the Gateway path.
        payload: Strict Swarm channel command.
        response: HTTP response carrying the original source status.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed channel result or backend rejection.
    """
    outcome = await SwarmRunApplication(calling=calling).create_swarm_channel(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmChannelSchema,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{swarm_run_id}/channels/{channel_id}/subscriptions",
    response_model=SubscribeSwarmChannelResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
    status_code=status.HTTP_200_OK,
)
async def subscribe_swarm_channel_route(
    workspace_id: NonNilCanonicalSwarmUUID,
    swarm_run_id: NonNilCanonicalSwarmUUID,
    channel_id: NonNilCanonicalSwarmUUID,
    payload: SubscribeSwarmChannelRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SubscribeSwarmChannelResponse | OrchestrationBackendErrorResponse:
    """Subscribe one member to a Swarm channel.

    Args:
        workspace_id: Workspace selected by the Gateway path.
        swarm_run_id: Swarm run selected by the Gateway path.
        channel_id: Channel selected by the Gateway path.
        payload: Strict subscription request naming a member.
        response: HTTP response carrying the original source status.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed subscription result or backend rejection.
    """
    outcome = await SwarmRunApplication(calling=calling).subscribe_swarm_channel(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        channel_id=channel_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SubscribeSwarmChannelResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{swarm_run_id}/members",
    response_model=SwarmMemberSchema | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
    status_code=status.HTTP_201_CREATED,
)
async def add_swarm_member_route(
    workspace_id: NonNilCanonicalSwarmUUID,
    swarm_run_id: NonNilCanonicalSwarmUUID,
    payload: AddSwarmMemberRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmMemberSchema | OrchestrationBackendErrorResponse:
    """Add one typed execution identity to a Swarm roster.

    Args:
        workspace_id: Workspace selected by the Gateway path.
        swarm_run_id: Swarm run selected by the Gateway path.
        payload: Strict Swarm member command.
        response: HTTP response carrying the original source status.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed member result or backend rejection.
    """
    outcome = await SwarmRunApplication(calling=calling).add_swarm_member(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmMemberSchema,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{swarm_run_id}/members/{member_id}/kill",
    response_model=KillSwarmMemberResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
    status_code=status.HTTP_200_OK,
)
async def kill_swarm_member_route(
    workspace_id: NonNilCanonicalSwarmUUID,
    swarm_run_id: NonNilCanonicalSwarmUUID,
    member_id: NonNilCanonicalSwarmUUID,
    payload: KillSwarmMemberRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> KillSwarmMemberResponse | OrchestrationBackendErrorResponse:
    """Kill one member and return all source-reported cascade kills.

    Args:
        workspace_id: Workspace selected by the Gateway path.
        swarm_run_id: Swarm run selected by the Gateway path.
        member_id: Member selected by the Gateway path.
        payload: Required empty request body.
        response: HTTP response carrying the original source status.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed killed member list or backend rejection.
    """
    outcome = await SwarmRunApplication(calling=calling).kill_swarm_member(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=KillSwarmMemberResponse,
        workspace_id=workspace_id,
    )
    return result
