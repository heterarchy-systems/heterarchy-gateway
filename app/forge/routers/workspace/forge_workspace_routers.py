"""Typed Forge HTTP entry points for the cohesive feature area."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status
from fastapi import Response as FastAPIResponse

from app.forge.application.forge_workspace_app import ForgeWorkspaceApplication
from app.forge.exceptions.forge_exceptions import FORGE_ERROR_RESPONSES, ForgeFailureEnvelope
from app.forge.schema.activity.forge_activity_schema import (
    ForgeActivityListRequest,
    ForgeActivityListResponse,
)
from app.forge.schema.location.forge_location_schema import (
    ForgeLocationListRequest,
    ForgeLocationListResponse,
)
from app.forge.schema.workspace.forge_workspace_schema import (
    ForgeWorkspaceListRequest,
    ForgeWorkspaceListResponse,
)
from app.forge.utils.forge_route_utils import forge_http_response
from app.shared.api_calling_box.forge_calling import ForgeCalling

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/locations/list",
    response_model=ForgeLocationListResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def list_locations_route(
    request: ForgeLocationListRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeLocationListResponse | ForgeFailureEnvelope:
    """List registered Forge Locations."""
    outcome = await ForgeWorkspaceApplication(forge_calling=forge_calling).list_locations(
        request=request
    )
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeLocationListResponse,
    )
    return result


@router.post(
    "/workspaces/list",
    response_model=ForgeWorkspaceListResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def list_workspaces_route(
    request: ForgeWorkspaceListRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeWorkspaceListResponse | ForgeFailureEnvelope:
    """List Workspaces discovered beneath one Location revision."""
    outcome = await ForgeWorkspaceApplication(forge_calling=forge_calling).list_workspaces(
        request=request
    )
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeWorkspaceListResponse,
    )
    return result


@router.post(
    "/activities/list",
    response_model=ForgeActivityListResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def list_activities_route(
    request: ForgeActivityListRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeActivityListResponse | ForgeFailureEnvelope:
    """List bounded Activity projections for one Workspace locator."""
    outcome = await ForgeWorkspaceApplication(forge_calling=forge_calling).list_activities(
        request=request
    )
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeActivityListResponse,
    )
    return result
