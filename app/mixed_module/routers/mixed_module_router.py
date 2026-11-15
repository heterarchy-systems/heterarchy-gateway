"""FastAPI endpoints composing Forge and Orchestration views with diagnostics tracing."""

from time import perf_counter
from typing import Annotated
from uuid import uuid4

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, HTTPException, Query, Response, status
from pydantic import TypeAdapter

from app.forge.application.get_forge import GetForgeApplication
from app.mixed_module.application.get_mixed_module import GetMixedModuleApplication
from app.mixed_module.application.inner_dto.get_mixed_module_inner_dto import (
    GetMixedModuleInnerDto,
)
from app.mixed_module.schema.get_mixed_module import GetMixedModuleResponse
from app.orchestration.application.get_orchestration import GetOrchestrationApplication
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.diagnostics.request_trace import FailureScenario, RequestTrace, TraceStore
from app.shared.filter_module.mixed_module_filter import MixedModuleFilter
from app.shared.settings_modules.gateway_settings import GatewayRuntimeSettings
from app.shared.types.json_contract import decode_json
from app.shared.types.upstream_payload import model_to_json_value

router = APIRouter(prefix="/mixed", tags=["mixed-module"], route_class=DishkaRoute)
_INNER_DTO_ADAPTER: TypeAdapter[GetMixedModuleInnerDto] = TypeAdapter(GetMixedModuleInnerDto)


@router.get("/{forge_id}/tasks/{task_id}", response_model=GetMixedModuleResponse)
async def fetch_mixed_module_route(
    forge_id: str,
    task_id: str,
    filters: Annotated[MixedModuleFilter, Query()],
    response: Response,
    forge_calling: FromDishka[ForgeCalling],
    orchestration_calling: FromDishka[OrchestrationCalling],
    runtime_settings: FromDishka[GatewayRuntimeSettings],
    trace_store: FromDishka[TraceStore],
    failure_scenario: Annotated[
        FailureScenario | None,
        Header(alias="X-BFF-Failure"),
    ] = None,
) -> GetMixedModuleResponse:
    trace_id = str(uuid4())
    trace = RequestTrace(trace_id)
    response.headers["X-Trace-ID"] = trace_id
    if failure_scenario is not None and not runtime_settings.failure_simulation_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Failure simulation is disabled",
        )
    application = GetMixedModuleApplication(
        GetForgeApplication(forge_calling.with_trace(trace, failure_scenario)),
        GetOrchestrationApplication(orchestration_calling.with_trace(trace, failure_scenario)),
    )
    normalize_started = perf_counter()
    try:
        inner_dto = await application.execute(forge_id, task_id)
    except Exception as error:
        trace.record_stage("BFF compose", normalize_started, "failed", str(error))
        trace.finish(status.HTTP_502_BAD_GATEWAY, None, None)
        trace_store.record(trace.snapshot())
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="An upstream dependency failed",
            headers={"X-Trace-ID": trace_id},
        ) from error
    trace.record_stage("BFF compose", normalize_started, "success")
    inner_json = decode_json(_INNER_DTO_ADAPTER.dump_json(inner_dto))
    if not filters.matches(
        inner_dto.forge.name,
        inner_dto.orchestration.status,
        inner_dto.forge.created_at.date(),
    ):
        trace.finish(status.HTTP_404_NOT_FOUND, inner_json, None)
        trace_store.record(trace.snapshot())
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No mixed resource matches the filters",
            headers={"X-Trace-ID": trace_id},
        )
    response_model = GetMixedModuleResponse.model_validate(inner_dto, from_attributes=True)
    public_json = model_to_json_value(response_model)
    trace.finish(status.HTTP_200_OK, inner_json, public_json)
    trace_store.record(trace.snapshot())
    return response_model
