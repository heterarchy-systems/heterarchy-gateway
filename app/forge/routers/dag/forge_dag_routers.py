"""Typed Forge HTTP entry points for the cohesive feature area."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status
from fastapi import Response as FastAPIResponse

from app.forge.application.forge_workspace_app import ForgeWorkspaceApplication
from app.forge.exceptions.forge_exceptions import FORGE_ERROR_RESPONSES, ForgeFailureEnvelope
from app.forge.schema.dag.forge_dag_schema import (
    ForgeDagReadCurrentRequest,
    ForgeDagReadCurrentResponse,
    ForgeDagSettleRequest,
    ForgeDagSettleResponse,
)
from app.forge.utils.forge_route_utils import forge_http_response
from app.shared.api_calling_box.forge_calling import ForgeCalling

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/dags/current",
    response_model=ForgeDagReadCurrentResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def read_current_dag_route(
    request: ForgeDagReadCurrentRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeDagReadCurrentResponse | ForgeFailureEnvelope:
    """Read the current stored revision for one Goal."""
    outcome = await ForgeWorkspaceApplication(forge_calling=forge_calling).read_current_dag(
        request=request
    )
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeDagReadCurrentResponse,
    )
    return result


@router.post(
    "/dags/settle",
    response_model=ForgeDagSettleResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def settle_dag_route(
    request: ForgeDagSettleRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeDagSettleResponse | ForgeFailureEnvelope:
    """Settle one exact Goal and DAG revision."""
    outcome = await ForgeWorkspaceApplication(forge_calling=forge_calling).settle_dag(
        request=request
    )
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeDagSettleResponse,
    )
    return result
