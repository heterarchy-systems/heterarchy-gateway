"""Typed HTTP entry points for the Mixed observation routes."""

from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, Query, Request, Response, status

from app.mixed_module.exceptions.mixed_exceptions import (
    MixedDependencyFailureResponse,
    MixedHttpDetailResponse,
)
from app.mixed_module.schema.mixed_dag_governance_schema import (
    MixedDagGovernanceRequest,
    MixedDagGovernanceResponse,
)
from app.mixed_module.schema.mixed_swarm_overview_schema import (
    MixedSwarmOverviewResponse,
)
from app.mixed_module.utils.mixed_route_utils import MixedRouteExecutor
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.diagnostics.request_trace import FailureScenario, TraceStore
from app.shared.filter_module.mixed_module_filter import MixedSwarmOverviewFilter
from app.shared.settings_modules.gateway_settings import GatewayRuntimeSettings
from app.shared.types.base_types import JsonObject
from app.shared.types.http_types import (
    ContentResponseDefinition,
    ResponseModelDefinition,
    ResponseModels,
    build_response_models,
)

_FASTAPI_VALIDATION_SCHEMA: JsonObject = {
    "title": "HTTPValidationError",
    "type": "object",
    "properties": {
        "detail": {
            "title": "Detail",
            "type": "array",
            "items": {
                "title": "ValidationError",
                "type": "object",
                "properties": {
                    "loc": {
                        "title": "Location",
                        "type": "array",
                        "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
                    },
                    "msg": {"title": "Message", "type": "string"},
                    "type": {"title": "Error Type", "type": "string"},
                    "input": {},
                    "ctx": {"title": "Context", "type": "object"},
                },
                "required": ["loc", "msg", "type"],
            },
        }
    },
}
_VALIDATION_ERROR_CONTENT: JsonObject = {
    "application/json": {
        "schema": {
            "anyOf": [
                {"$ref": "#/components/schemas/MixedDependencyFailureResponse"},
                _FASTAPI_VALIDATION_SCHEMA,
            ]
        }
    }
}

MIXED_SWARM_OVERVIEW_RESPONSES: ResponseModels = build_response_models(
    definitions=(
        ResponseModelDefinition(
            status_code=status.HTTP_202_ACCEPTED,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_400_BAD_REQUEST,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_401_UNAUTHORIZED,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_403_FORBIDDEN,
            model=MixedDependencyFailureResponse | MixedHttpDetailResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_404_NOT_FOUND,
            model=MixedDependencyFailureResponse | MixedHttpDetailResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_409_CONFLICT,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            model=MixedDependencyFailureResponse,
        ),
        ContentResponseDefinition(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            description="Mixed source rejection or FastAPI request validation error.",
            content=_VALIDATION_ERROR_CONTENT,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_502_BAD_GATEWAY,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(status_code="default", model=MixedDependencyFailureResponse),
    )
)

MIXED_DAG_GOVERNANCE_RESPONSES: ResponseModels = build_response_models(
    definitions=(
        ResponseModelDefinition(
            status_code=status.HTTP_202_ACCEPTED,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_400_BAD_REQUEST,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_401_UNAUTHORIZED,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_403_FORBIDDEN,
            model=MixedDependencyFailureResponse | MixedHttpDetailResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_404_NOT_FOUND,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_409_CONFLICT,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            model=MixedDependencyFailureResponse,
        ),
        ContentResponseDefinition(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            description="Mixed source rejection or FastAPI request validation error.",
            content=_VALIDATION_ERROR_CONTENT,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_502_BAD_GATEWAY,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            model=MixedDependencyFailureResponse,
        ),
        ResponseModelDefinition(status_code="default", model=MixedDependencyFailureResponse),
    )
)

router = APIRouter(prefix="/mixed", tags=["mixed-module"], route_class=DishkaRoute)


@router.get(
    "/workspaces/{workspace_id}/swarms/{swarm_run_id}/overview",
    response_model=MixedSwarmOverviewResponse | MixedDependencyFailureResponse,
    status_code=status.HTTP_200_OK,
    responses=MIXED_SWARM_OVERVIEW_RESPONSES,
)
async def mixed_swarm_overview_route(
    workspace_id: UUID,
    swarm_run_id: UUID,
    request: Request,
    filters: Annotated[MixedSwarmOverviewFilter, Query()],
    response: Response,
    forge_authorization: Annotated[
        str,
        Header(alias="X-Forge-Authorization", min_length=1),
    ],
    orchestration_authorization: Annotated[
        str,
        Header(alias="X-Orchestration-Authorization", min_length=1),
    ],
    forge_calling: FromDishka[ForgeCalling],
    orchestration_calling: FromDishka[OrchestrationCalling],
    runtime_settings: FromDishka[GatewayRuntimeSettings],
    trace_store: FromDishka[TraceStore],
    failure_scenario: Annotated[
        FailureScenario | None,
        Header(alias="X-BFF-Failure"),
    ] = None,
) -> MixedSwarmOverviewResponse | MixedDependencyFailureResponse:
    """Return the exact Forge and Orchestration observations for one Swarm."""
    result = await MixedRouteExecutor(
        forge_calling=forge_calling,
        orchestration_calling=orchestration_calling,
        runtime_settings=runtime_settings,
        trace_store=trace_store,
    ).execute_swarm_overview(
        request=request,
        response=response,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        filters=filters,
        failure_scenario=failure_scenario,
    )
    return result


@router.post(
    "/workspaces/{workspace_id}/dags/governance-overview",
    response_model=MixedDagGovernanceResponse | MixedDependencyFailureResponse,
    status_code=status.HTTP_200_OK,
    responses=MIXED_DAG_GOVERNANCE_RESPONSES,
)
async def mixed_dag_governance_route(
    workspace_id: UUID,
    request: MixedDagGovernanceRequest,
    response: Response,
    forge_authorization: Annotated[
        str,
        Header(alias="X-Forge-Authorization", min_length=1),
    ],
    orchestration_authorization: Annotated[
        str,
        Header(alias="X-Orchestration-Authorization", min_length=1),
    ],
    forge_calling: FromDishka[ForgeCalling],
    orchestration_calling: FromDishka[OrchestrationCalling],
    runtime_settings: FromDishka[GatewayRuntimeSettings],
    trace_store: FromDishka[TraceStore],
    failure_scenario: Annotated[
        FailureScenario | None,
        Header(alias="X-BFF-Failure"),
    ] = None,
) -> MixedDagGovernanceResponse | MixedDependencyFailureResponse:
    """Return current Forge DAG and selected Orchestration governance reads."""
    result = await MixedRouteExecutor(
        forge_calling=forge_calling,
        orchestration_calling=orchestration_calling,
        runtime_settings=runtime_settings,
        trace_store=trace_store,
    ).execute_dag_governance(
        response=response,
        workspace_id=workspace_id,
        request=request,
        failure_scenario=failure_scenario,
    )
    return result
