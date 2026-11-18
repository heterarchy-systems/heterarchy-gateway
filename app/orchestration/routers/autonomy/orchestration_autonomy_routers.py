"""Typed Workspace scope, review, snapshot, and governance HTTP contracts."""

from typing import Annotated
from uuid import UUID

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Request, Response, status

from app.orchestration.application.autonomy.autonomy_reviewer_app import AutonomyReviewerApplication
from app.orchestration.application.autonomy.autonomy_scope_app import AutonomyScopeApplication
from app.orchestration.application.autonomy.autonomy_settlement_app import (
    AutonomySettlementApplication,
)
from app.orchestration.application.autonomy.autonomy_snapshot_app import AutonomySnapshotApplication
from app.orchestration.exceptions.orchestration_exceptions import (
    ORCHESTRATION_ERROR_RESPONSES,
    OrchestrationBackendErrorResponse,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_reviewer_schema import (
    AssignReviewerRequest,
    RecordReviewVerdictRequest,
    ReviewerOperationResponse,
    VerifyNodeCompletionGateRequest,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_scope_schema import (
    RegisteredWorkspaceScopeResponse,
    WorkspaceScopeListResponse,
    WorkspaceScopeQueryResponse,
    WorkspaceScopeRegisterRequest,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_settlement_schema import (
    DagSettlementAuthorityRequest,
    DagSettlementAuthorityResponse,
    DagSettlementGovernanceResponse,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_snapshot_schema import (
    ExecutionSnapshotOutcomeResponse,
    ExecutionSnapshotQueryResponse,
    PrepareExecutionSnapshotRequest,
)
from app.orchestration.utils.orchestration_route_utils import orchestration_http_response
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.filter_module.autonomy_filter import (
    DagSettlementGovernanceFilter,
    ExecutionSnapshotFilter,
)
from app.shared.types.http_types import (
    ResponseModelDefinition,
    ResponseModels,
    build_response_models,
)
from app.shared.utils.query_validation import checked_query_filter

router = APIRouter(prefix="/workspaces", route_class=DishkaRoute)
_REVIEWER_OPERATION_RESPONSES: ResponseModels = (
    ORCHESTRATION_ERROR_RESPONSES
    | build_response_models(
        definitions=(
            ResponseModelDefinition(
                status_code=status.HTTP_409_CONFLICT,
                model=ReviewerOperationResponse | OrchestrationBackendErrorResponse,
            ),
        )
    )
)
_EXECUTION_SNAPSHOT_RESPONSES: ResponseModels = (
    ORCHESTRATION_ERROR_RESPONSES
    | build_response_models(
        definitions=(
            ResponseModelDefinition(
                status_code=status.HTTP_409_CONFLICT,
                model=ExecutionSnapshotOutcomeResponse | OrchestrationBackendErrorResponse,
            ),
        )
    )
)


@router.get(
    "/scopes",
    response_model=WorkspaceScopeListResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def list_workspace_scopes_route(
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> WorkspaceScopeListResponse | OrchestrationBackendErrorResponse:
    outcome = await AutonomyScopeApplication(orchestration_calling=calling).list_scopes()
    result = orchestration_http_response(
        outcome=outcome, response=response, response_model=WorkspaceScopeListResponse
    )
    return result


@router.post(
    "/scopes",
    response_model=RegisteredWorkspaceScopeResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def register_workspace_scope_route(
    payload: WorkspaceScopeRegisterRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> RegisteredWorkspaceScopeResponse | OrchestrationBackendErrorResponse:
    outcome = await AutonomyScopeApplication(orchestration_calling=calling).register_scope(
        request=payload
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=RegisteredWorkspaceScopeResponse,
        workspace_id=payload.scope.workspace_id,
    )
    return result


@router.get(
    "/{workspace_id}/scopes",
    response_model=WorkspaceScopeQueryResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def fetch_workspace_scope_route(
    workspace_id: UUID,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> WorkspaceScopeQueryResponse | OrchestrationBackendErrorResponse:
    outcome = await AutonomyScopeApplication(orchestration_calling=calling).fetch_workspace_scope(
        workspace_id=workspace_id
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=WorkspaceScopeQueryResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/reviewer-assignments",
    response_model=ReviewerOperationResponse | OrchestrationBackendErrorResponse,
    responses=_REVIEWER_OPERATION_RESPONSES,
)
async def assign_reviewer_route(
    workspace_id: UUID,
    payload: AssignReviewerRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ReviewerOperationResponse | OrchestrationBackendErrorResponse:
    outcome = await AutonomyReviewerApplication(orchestration_calling=calling).assign_reviewer(
        workspace_id=workspace_id, request=payload
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ReviewerOperationResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/reviewer-verdicts",
    response_model=ReviewerOperationResponse | OrchestrationBackendErrorResponse,
    responses=_REVIEWER_OPERATION_RESPONSES,
)
async def record_reviewer_verdict_route(
    workspace_id: UUID,
    payload: RecordReviewVerdictRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ReviewerOperationResponse | OrchestrationBackendErrorResponse:
    outcome = await AutonomyReviewerApplication(
        orchestration_calling=calling
    ).record_reviewer_verdict(workspace_id=workspace_id, request=payload)
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ReviewerOperationResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/node-completion-gate",
    response_model=ReviewerOperationResponse | OrchestrationBackendErrorResponse,
    responses=_REVIEWER_OPERATION_RESPONSES,
)
async def verify_node_completion_gate_route(
    workspace_id: UUID,
    payload: VerifyNodeCompletionGateRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ReviewerOperationResponse | OrchestrationBackendErrorResponse:
    outcome = await AutonomyReviewerApplication(
        orchestration_calling=calling
    ).verify_node_completion_gate(workspace_id=workspace_id, request=payload)
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ReviewerOperationResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/execution-snapshots",
    response_model=ExecutionSnapshotOutcomeResponse | OrchestrationBackendErrorResponse,
    responses=_EXECUTION_SNAPSHOT_RESPONSES,
)
async def prepare_execution_snapshot_route(
    workspace_id: UUID,
    payload: PrepareExecutionSnapshotRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ExecutionSnapshotOutcomeResponse | OrchestrationBackendErrorResponse:
    outcome = await AutonomySnapshotApplication(
        orchestration_calling=calling
    ).prepare_execution_snapshot(workspace_id=workspace_id, request=payload)
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ExecutionSnapshotOutcomeResponse,
        workspace_id=workspace_id,
    )
    return result


@router.get(
    "/{workspace_id}/execution-snapshots",
    response_model=ExecutionSnapshotQueryResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def fetch_execution_snapshot_route(
    workspace_id: UUID,
    request: Request,
    filters: Annotated[ExecutionSnapshotFilter, Query()],
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ExecutionSnapshotQueryResponse | OrchestrationBackendErrorResponse:
    query = checked_query_filter(request=request, filters=filters)
    outcome = await AutonomySnapshotApplication(
        orchestration_calling=calling
    ).fetch_execution_snapshot(workspace_id=workspace_id, filters=query)
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ExecutionSnapshotQueryResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/dag-settlement-authority",
    response_model=DagSettlementAuthorityResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def check_dag_settlement_authority_route(
    workspace_id: UUID,
    payload: DagSettlementAuthorityRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> DagSettlementAuthorityResponse | OrchestrationBackendErrorResponse:
    outcome = await AutonomySettlementApplication(
        orchestration_calling=calling
    ).check_dag_settlement_authority(workspace_id=workspace_id, request=payload)
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=DagSettlementAuthorityResponse,
        workspace_id=workspace_id,
    )
    return result


@router.get(
    "/{workspace_id}/dag-settlement-governance",
    response_model=DagSettlementGovernanceResponse | OrchestrationBackendErrorResponse,
    responses=ORCHESTRATION_ERROR_RESPONSES,
)
async def fetch_dag_settlement_governance_route(
    workspace_id: UUID,
    request: Request,
    filters: Annotated[DagSettlementGovernanceFilter, Query()],
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> DagSettlementGovernanceResponse | OrchestrationBackendErrorResponse:
    query = checked_query_filter(request=request, filters=filters)
    outcome = await AutonomySettlementApplication(
        orchestration_calling=calling
    ).fetch_dag_settlement_governance(workspace_id=workspace_id, filters=query)
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=DagSettlementGovernanceResponse,
        workspace_id=workspace_id,
    )
    return result
