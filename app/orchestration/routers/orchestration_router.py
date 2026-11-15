"""FastAPI endpoints for Orchestration resources."""

from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, status

from app.orchestration.application.cancel_orchestration import CancelOrchestrationApplication
from app.orchestration.application.get_orchestration import GetOrchestrationApplication
from app.orchestration.application.list_orchestrations import ListOrchestrationsApplication
from app.orchestration.application.start_orchestration import StartOrchestrationApplication
from app.orchestration.schema.cancel_orchestration import CancelOrchestrationResponse
from app.orchestration.schema.get_orchestration import GetOrchestrationResponse
from app.orchestration.schema.start_orchestration import (
    StartOrchestrationRequest,
    StartOrchestrationResponse,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.filter_module.orchestration_filter import OrchestrationFilter

router = APIRouter(prefix="/orchestrations", tags=["orchestration"], route_class=DishkaRoute)


@router.get("", response_model=list[GetOrchestrationResponse])
async def list_orchestrations_route(
    filters: Annotated[OrchestrationFilter, Query()],
    orchestration_calling: FromDishka[OrchestrationCalling],
) -> list[GetOrchestrationResponse]:
    items = await ListOrchestrationsApplication(orchestration_calling).execute(filters)
    response_models = [
        GetOrchestrationResponse.model_validate(item, from_attributes=True) for item in items
    ]
    return response_models


@router.post("", response_model=StartOrchestrationResponse, status_code=status.HTTP_202_ACCEPTED)
async def start_orchestration_route(
    request: StartOrchestrationRequest,
    orchestration_calling: FromDishka[OrchestrationCalling],
) -> StartOrchestrationResponse:
    inner_dto = await StartOrchestrationApplication(orchestration_calling).execute(
        request.workflow_name,
        request.inputs,
    )
    response_model = StartOrchestrationResponse.model_validate(inner_dto, from_attributes=True)
    return response_model


@router.get("/{task_id}", response_model=GetOrchestrationResponse)
async def fetch_orchestration_route(
    task_id: str,
    orchestration_calling: FromDishka[OrchestrationCalling],
) -> GetOrchestrationResponse:
    inner_dto = await GetOrchestrationApplication(orchestration_calling).execute(task_id)
    response_model = GetOrchestrationResponse.model_validate(inner_dto, from_attributes=True)
    return response_model


@router.delete("/{task_id}", response_model=CancelOrchestrationResponse)
async def cancel_orchestration_route(
    task_id: str,
    orchestration_calling: FromDishka[OrchestrationCalling],
) -> CancelOrchestrationResponse:
    inner_dto = await CancelOrchestrationApplication(orchestration_calling).execute(task_id)
    response_model = CancelOrchestrationResponse.model_validate(inner_dto, from_attributes=True)
    return response_model
