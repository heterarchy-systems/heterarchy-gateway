"""Typed HTTP entry points for East-West Forge bridge operations."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Response, status

from app.orchestration.application.forge_bridge_app import ForgeBridgeApplication
from app.orchestration.exceptions.orchestration_exceptions import (
    ORCHESTRATION_ERROR_RESPONSES,
    OrchestrationBackendErrorResponse,
)
from app.orchestration.schema.forge_bridge.orchestration_forge_bridge_schema import (
    ForgeConvergeSwarmRequest,
    ForgeConvergeSwarmResponse,
    ForgeSettleSwarmRequest,
    ForgeSettleSwarmResponse,
    SyncAutonomyOutboxRequest,
    SyncAutonomyOutboxResponse,
)
from app.orchestration.schema.types.swarm_types import NonNilSwarmUUID
from app.orchestration.utils.orchestration_route_utils import orchestration_http_response
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling

router = APIRouter(prefix="/workspaces", route_class=DishkaRoute)


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/forge-converge",
    response_model=ForgeConvergeSwarmResponse | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_200_OK,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def forge_converge_swarm_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: ForgeConvergeSwarmRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ForgeConvergeSwarmResponse | OrchestrationBackendErrorResponse:
    """Forward one Swarm candidate convergence request.

    Args:
        workspace_id: Workspace identity selected by the URL path.
        swarm_run_id: Swarm identity selected by the URL path.
        payload: Strict caller convergence request.
        response: HTTP response whose status follows Orchestration.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed convergence receipt or Orchestration error response.
    """
    outcome = await ForgeBridgeApplication(calling=calling).forge_converge_swarm(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ForgeConvergeSwarmResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/forge-settle",
    response_model=ForgeSettleSwarmResponse | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_200_OK,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def forge_settle_swarm_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: ForgeSettleSwarmRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ForgeSettleSwarmResponse | OrchestrationBackendErrorResponse:
    """Forward one gate-checked Forge Swarm settlement request.

    Args:
        workspace_id: Workspace identity selected by the URL path.
        swarm_run_id: Swarm identity selected by the URL path.
        payload: Strict caller settlement request.
        response: HTTP response whose status follows Orchestration.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed settlement receipt or Orchestration error response.
    """
    outcome = await ForgeBridgeApplication(calling=calling).forge_settle_swarm(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ForgeSettleSwarmResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/autonomy-outbox/sync",
    response_model=SyncAutonomyOutboxResponse | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_200_OK,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def sync_autonomy_outbox_route(
    workspace_id: NonNilSwarmUUID,
    payload: SyncAutonomyOutboxRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SyncAutonomyOutboxResponse | OrchestrationBackendErrorResponse:
    """Forward one bounded autonomy outbox reconciliation page.

    Args:
        workspace_id: Workspace identity selected by the URL path.
        payload: Strict migration cursor and bounded page request.
        response: HTTP response whose status follows Orchestration.
        calling: Request-scoped authenticated Orchestration caller.
    Return:
        Typed sync summary or Orchestration error response.
    """
    outcome = await ForgeBridgeApplication(calling=calling).sync_autonomy_outbox(
        workspace_id=workspace_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SyncAutonomyOutboxResponse,
        workspace_id=workspace_id,
    )
    return result
