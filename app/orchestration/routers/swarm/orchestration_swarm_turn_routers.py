"""Typed HTTP routes for Native Swarm member turn operations."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from app.orchestration.application.swarm_turn_app import SwarmTurnApplication
from app.orchestration.exceptions.orchestration_exceptions import (
    ORCHESTRATION_ERROR_RESPONSES,
    OrchestrationBackendErrorResponse,
)
from app.orchestration.schema.swarm.orchestration_swarm_state_schema import SwarmMemberSchema
from app.orchestration.schema.swarm.orchestration_swarm_turn_schema import (
    ClaimSwarmWakeupRequest,
    CompleteSwarmTurnRequest,
    DispatchSwarmTurnRequest,
    DispatchSwarmTurnResponse,
    FailSwarmTurnRequest,
    SwarmModelSwitchResponse,
    SwarmWakeupBatchResponse,
    SwitchSwarmMemberModelRequest,
)
from app.orchestration.schema.types.swarm_types import NonNilSwarmUUID
from app.orchestration.utils.orchestration_route_utils import orchestration_http_response
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.settings_modules.gateway_settings import GatewayRuntimeSettings

router = APIRouter(prefix="/workspaces", route_class=DishkaRoute)


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/claim",
    response_model=SwarmWakeupBatchResponse | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_200_OK,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def claim_swarm_turn_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    member_id: NonNilSwarmUUID,
    payload: ClaimSwarmWakeupRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmWakeupBatchResponse | OrchestrationBackendErrorResponse:
    """Claim the source wakeup batch for one member turn.

    Args:
        workspace_id: Workspace identity selected by the URL path.
        swarm_run_id: Swarm run identity selected by the URL path.
        member_id: Member identity selected by the URL path.
        payload: Strict wakeup-claim request.
        response: FastAPI response whose status follows the source.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed wakeup batch or backend error response.
    """
    outcome = await SwarmTurnApplication(orchestration_calling=calling).claim_turn(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmWakeupBatchResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/complete",
    response_model=SwarmMemberSchema | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_200_OK,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def complete_swarm_turn_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    member_id: NonNilSwarmUUID,
    payload: CompleteSwarmTurnRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmMemberSchema | OrchestrationBackendErrorResponse:
    """Complete the member turn and preserve the source response status.

    Args:
        workspace_id: Workspace identity selected by the URL path.
        swarm_run_id: Swarm run identity selected by the URL path.
        member_id: Member identity selected by the URL path.
        payload: Strict completion request.
        response: FastAPI response whose status follows the source.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed member receipt or backend error response.
    """
    outcome = await SwarmTurnApplication(orchestration_calling=calling).complete_turn(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
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
    "/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/fail",
    response_model=SwarmMemberSchema | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_200_OK,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def fail_swarm_turn_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    member_id: NonNilSwarmUUID,
    payload: FailSwarmTurnRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmMemberSchema | OrchestrationBackendErrorResponse:
    """Release an unsuccessful member turn using the source disposition.

    Args:
        workspace_id: Workspace identity selected by the URL path.
        swarm_run_id: Swarm run identity selected by the URL path.
        member_id: Member identity selected by the URL path.
        payload: Strict failure-release request.
        response: FastAPI response whose status follows the source.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed member receipt or backend error response.
    """
    outcome = await SwarmTurnApplication(orchestration_calling=calling).fail_turn(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
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
    "/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/turns/dispatch",
    response_model=DispatchSwarmTurnResponse | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_200_OK,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def dispatch_swarm_turn_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    member_id: NonNilSwarmUUID,
    payload: DispatchSwarmTurnRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
    runtime_settings: FromDishka[GatewayRuntimeSettings],
) -> DispatchSwarmTurnResponse | OrchestrationBackendErrorResponse:
    """Dispatch one member turn with the configured timeout floor.

    Args:
        workspace_id: Workspace identity selected by the URL path.
        swarm_run_id: Swarm run identity selected by the URL path.
        member_id: Member identity selected by the URL path.
        payload: Strict dispatch request and phase timeouts.
        response: FastAPI response whose status follows the source.
        calling: Request-scoped Orchestration caller.
        runtime_settings: Runtime timeout floor and shared-client bounds.
    Return:
        Typed dispatch receipt or backend error response.
    """
    outcome = await SwarmTurnApplication(orchestration_calling=calling).dispatch_turn(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        request=payload,
        timeout_floor_seconds=runtime_settings.http_timeout_seconds,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=DispatchSwarmTurnResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/members/{member_id}/model-switch",
    response_model=SwarmModelSwitchResponse | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_200_OK,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def switch_swarm_member_model_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    member_id: NonNilSwarmUUID,
    payload: SwitchSwarmMemberModelRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmModelSwitchResponse | OrchestrationBackendErrorResponse:
    """Switch a suspended member to one supported profile target.

    Args:
        workspace_id: Workspace identity selected by the URL path.
        swarm_run_id: Swarm run identity selected by the URL path.
        member_id: Member identity selected by the URL path.
        payload: Strict Profile rebind or preference update request.
        response: FastAPI response whose status follows the source.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed model-switch receipt or backend error response.
    """
    outcome = await SwarmTurnApplication(orchestration_calling=calling).switch_member_model(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmModelSwitchResponse,
        workspace_id=workspace_id,
    )
    return result
