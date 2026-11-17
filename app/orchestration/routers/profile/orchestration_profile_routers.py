"""Typed Profile HTTP contracts backed by Orchestration."""

from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Request, Response, status

from app.orchestration.application.profile_app import ProfileApplication
from app.orchestration.exceptions.orchestration_exceptions import (
    ORCHESTRATION_ERROR_RESPONSES,
    OrchestrationBackendErrorResponse,
)
from app.orchestration.schema.profile.orchestration_profile_schema import (
    CreateProfileRequest,
    ProfileCreateResponse,
    ProfileLifecycleRequest,
    ProfileListFilter,
    ProfileListResponse,
    ProfileMutationResponse,
    ProfileResponse,
    UpdateProfileConfigRequest,
)
from app.orchestration.utils.orchestration_route_utils import orchestration_http_response
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.utils.query_validation import checked_query_filter

router = APIRouter(prefix="/profiles", route_class=DishkaRoute)


@router.post(
    "",
    response_model=ProfileCreateResponse | OrchestrationBackendErrorResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ORCHESTRATION_ERROR_RESPONSES
    | {status.HTTP_200_OK: {"model": ProfileCreateResponse}},
)
async def create_profile_route(
    payload: CreateProfileRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ProfileCreateResponse | OrchestrationBackendErrorResponse:
    outcome = await ProfileApplication(orchestration_calling=calling).create_profile(
        request=payload
    )
    result = orchestration_http_response(
        outcome=outcome, response=response, response_model=ProfileCreateResponse
    )
    return result


@router.get(
    "",
    response_model=ProfileListResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def list_profiles_route(
    request: Request,
    filters: Annotated[ProfileListFilter, Query()],
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ProfileListResponse | OrchestrationBackendErrorResponse:
    query = checked_query_filter(request=request, filters=filters)
    outcome = await ProfileApplication(orchestration_calling=calling).fetch_profiles(filters=query)
    result = orchestration_http_response(
        outcome=outcome, response=response, response_model=ProfileListResponse
    )
    return result


@router.get(
    "/{profile_id}",
    response_model=ProfileResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def fetch_profile_route(
    profile_id: UUID,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ProfileResponse | OrchestrationBackendErrorResponse:
    outcome = await ProfileApplication(orchestration_calling=calling).fetch_profile(
        profile_id=profile_id
    )
    result = orchestration_http_response(
        outcome=outcome, response=response, response_model=ProfileResponse
    )
    return result


@router.put(
    "/{profile_id}/configuration",
    response_model=ProfileMutationResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def update_profile_configuration_route(
    profile_id: UUID,
    payload: UpdateProfileConfigRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ProfileMutationResponse | OrchestrationBackendErrorResponse:
    outcome = await ProfileApplication(orchestration_calling=calling).update_profile_config(
        profile_id=profile_id, request=payload
    )
    result = orchestration_http_response(
        outcome=outcome, response=response, response_model=ProfileMutationResponse
    )
    return result


@router.post(
    "/{profile_id}/disable",
    response_model=ProfileMutationResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def disable_profile_route(
    profile_id: UUID,
    payload: ProfileLifecycleRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ProfileMutationResponse | OrchestrationBackendErrorResponse:
    outcome = await ProfileApplication(orchestration_calling=calling).disable_profile(
        profile_id=profile_id, request=payload
    )
    result = orchestration_http_response(
        outcome=outcome, response=response, response_model=ProfileMutationResponse
    )
    return result


@router.post(
    "/{profile_id}/retire",
    response_model=ProfileMutationResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def retire_profile_route(
    profile_id: UUID,
    payload: ProfileLifecycleRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ProfileMutationResponse | OrchestrationBackendErrorResponse:
    outcome = await ProfileApplication(orchestration_calling=calling).retire_profile(
        profile_id=profile_id, request=payload
    )
    result = orchestration_http_response(
        outcome=outcome, response=response, response_model=ProfileMutationResponse
    )
    return result
