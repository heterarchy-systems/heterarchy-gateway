"""FastAPI endpoints for Forge resources."""

from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from app.forge.application.get_forge import GetForgeApplication
from app.forge.application.list_forges import ListForgesApplication
from app.forge.application.mutate_forge import (
    CreateForgeApplication,
    DeleteForgeApplication,
    UpdateForgeApplication,
)
from app.forge.schema.create_forge import CreateForgeRequest, CreateForgeResponse
from app.forge.schema.delete_forge import DeleteForgeResponse
from app.forge.schema.get_forge import GetForgeResponse
from app.forge.schema.update_forge import UpdateForgeRequest, UpdateForgeResponse
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.filter_module.forge_filter import ForgeFilter
from app.shared.types.upstream_payload import model_to_patch_object

router = APIRouter(prefix="/forges", tags=["forge"], route_class=DishkaRoute)


@router.get("", response_model=list[GetForgeResponse])
async def list_forges_route(
    filters: Annotated[ForgeFilter, Query()],
    forge_calling: FromDishka[ForgeCalling],
) -> list[GetForgeResponse]:
    items = await ListForgesApplication(forge_calling).execute(filters)
    response_models = [
        GetForgeResponse.model_validate(item, from_attributes=True) for item in items
    ]
    return response_models


@router.post("", response_model=CreateForgeResponse, status_code=status.HTTP_201_CREATED)
async def create_forge_route(
    request: CreateForgeRequest,
    forge_calling: FromDishka[ForgeCalling],
) -> CreateForgeResponse:
    inner_dto = await CreateForgeApplication(forge_calling).execute(
        request.name,
        request.description,
    )
    response_model = CreateForgeResponse.model_validate(inner_dto, from_attributes=True)
    return response_model


@router.get("/{forge_id}", response_model=GetForgeResponse)
async def fetch_forge_route(
    forge_id: str,
    forge_calling: FromDishka[ForgeCalling],
) -> GetForgeResponse:
    inner_dto = await GetForgeApplication(forge_calling).execute(forge_id)
    response_model = GetForgeResponse.model_validate(inner_dto, from_attributes=True)
    return response_model


@router.put("/{forge_id}", response_model=UpdateForgeResponse)
async def update_forge_route(
    forge_id: str,
    request: UpdateForgeRequest,
    forge_calling: FromDishka[ForgeCalling],
) -> UpdateForgeResponse:
    patch = model_to_patch_object(request)
    inner_dto = await UpdateForgeApplication(forge_calling).execute(forge_id, patch)
    response_model = UpdateForgeResponse.model_validate(inner_dto, from_attributes=True)
    return response_model


@router.delete("/{forge_id}", response_model=DeleteForgeResponse)
async def delete_forge_route(
    forge_id: str,
    forge_calling: FromDishka[ForgeCalling],
) -> DeleteForgeResponse:
    inner_dto = await DeleteForgeApplication(forge_calling).execute(forge_id)
    response_model = DeleteForgeResponse.model_validate(inner_dto, from_attributes=True)
    return response_model
