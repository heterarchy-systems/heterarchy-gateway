"""Typed HTTP entry points for the Mixed observation routes."""

from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Header, Query, Request, Response, status

from app.mixed_module.exceptions.mixed_exceptions import (
    MIXED_DAG_GOVERNANCE_RESPONSES,
    MIXED_SWARM_OVERVIEW_RESPONSES,
    MixedDependencyFailureResponse,
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
