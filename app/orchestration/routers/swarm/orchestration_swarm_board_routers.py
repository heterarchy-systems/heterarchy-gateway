"""Typed HTTP routes for Native Swarm board and convergence operations."""

from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Query, Request, Response, status

from app.orchestration.application.swarm_board_app import (
    SwarmBoardConvergenceApplication,
    SwarmBoardMessageApplication,
    SwarmBoardVerificationApplication,
)
from app.orchestration.exceptions.orchestration_exceptions import (
    ORCHESTRATION_ERROR_RESPONSES,
    OrchestrationBackendErrorResponse,
)
from app.orchestration.schema.swarm.orchestration_swarm_board_schema import (
    AbortSwarmRunRequest,
    ConvergeSwarmRequest,
    ConvergeSwarmResponse,
    CreateSwarmVerificationPanelRequest,
    PostSwarmMessageRequest,
    PostSwarmMessageResponse,
    RecordSwarmVerdictRequest,
    SettleSwarmRequest,
    SwarmBoardMessagesFilter,
    SwarmBoardPageResponse,
    SwarmStallCheckRequest,
    SwarmStallCheckResponse,
)
from app.orchestration.schema.swarm.orchestration_swarm_state_schema import (
    SwarmRunSchema,
    SwarmVerdictSchema,
    SwarmVerificationPanelSchema,
)
from app.orchestration.schema.types.swarm_types import NonNilSwarmUUID
from app.orchestration.utils.orchestration_route_utils import orchestration_http_response
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import OrchestrationErrorResponse
from app.shared.types.http_types import ResponseModels
from app.shared.utils.query_validation import checked_query_filter

router = APIRouter(prefix="/workspaces", route_class=DishkaRoute)
SWARM_ERROR_RESPONSES: ResponseModels = ORCHESTRATION_ERROR_RESPONSES | {
    status.HTTP_413_CONTENT_TOO_LARGE: {"model": OrchestrationErrorResponse},
}


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/messages",
    response_model=(
        PostSwarmMessageResponse | OrchestrationBackendErrorResponse | OrchestrationErrorResponse
    ),
    status_code=status.HTTP_201_CREATED,
    responses=SWARM_ERROR_RESPONSES | {status.HTTP_200_OK: {"model": PostSwarmMessageResponse}},
)
async def post_swarm_message_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: PostSwarmMessageRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> PostSwarmMessageResponse | OrchestrationBackendErrorResponse | OrchestrationErrorResponse:
    """Post or replay one message on a Swarm board.

    Args:
        workspace_id: Workspace UUID selected by the public route.
        swarm_run_id: Swarm run UUID selected by the public route.
        payload: Strictly validated board message command.
        response: FastAPI response carrying source status.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed message result or declared Orchestration error.
    """
    outcome = await SwarmBoardMessageApplication(orchestration_calling=calling).post_message(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=PostSwarmMessageResponse,
        workspace_id=workspace_id,
    )
    return result


@router.get(
    "/{workspace_id}/swarms/{swarm_run_id}/messages",
    response_model=(
        SwarmBoardPageResponse | OrchestrationBackendErrorResponse | OrchestrationErrorResponse
    ),
    responses=SWARM_ERROR_RESPONSES,
)
async def read_swarm_messages_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    request: Request,
    filters: Annotated[SwarmBoardMessagesFilter, Query()],
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmBoardPageResponse | OrchestrationBackendErrorResponse | OrchestrationErrorResponse:
    """Read a bounded incremental board page after a checked cursor.

    Args:
        workspace_id: Workspace UUID selected by the public route.
        swarm_run_id: Swarm run UUID selected by the public route.
        request: Request carrying the original query multimap.
        filters: Parsed board cursor, channel and limit.
        response: FastAPI response carrying source status.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed ordered board page or declared Orchestration error.
    """
    query = checked_query_filter(request=request, filters=filters)
    outcome = await SwarmBoardMessageApplication(orchestration_calling=calling).fetch_board_page(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        filters=query,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmBoardPageResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/panels",
    response_model=(
        SwarmVerificationPanelSchema
        | OrchestrationBackendErrorResponse
        | OrchestrationErrorResponse
    ),
    status_code=status.HTTP_201_CREATED,
    responses=SWARM_ERROR_RESPONSES | {status.HTTP_200_OK: {"model": SwarmVerificationPanelSchema}},
)
async def create_swarm_panel_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: CreateSwarmVerificationPanelRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmVerificationPanelSchema | OrchestrationBackendErrorResponse | OrchestrationErrorResponse:
    """Create or replay a verification panel.

    Args:
        workspace_id: Workspace UUID selected by the public route.
        swarm_run_id: Swarm run UUID selected by the public route.
        payload: Strictly validated verification panel command.
        response: FastAPI response carrying source status.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed verification panel or declared Orchestration error.
    """
    outcome = await SwarmBoardVerificationApplication(orchestration_calling=calling).create_panel(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmVerificationPanelSchema,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/verdicts",
    response_model=SwarmVerdictSchema
    | OrchestrationBackendErrorResponse
    | OrchestrationErrorResponse,
    status_code=status.HTTP_201_CREATED,
    responses=SWARM_ERROR_RESPONSES | {status.HTTP_200_OK: {"model": SwarmVerdictSchema}},
)
async def record_swarm_verdict_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: RecordSwarmVerdictRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmVerdictSchema | OrchestrationBackendErrorResponse | OrchestrationErrorResponse:
    """Record or replay one verifier verdict.

    Args:
        workspace_id: Workspace UUID selected by the public route.
        swarm_run_id: Swarm run UUID selected by the public route.
        payload: Strictly validated verifier verdict command.
        response: FastAPI response carrying source status.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed verifier verdict or declared Orchestration error.
    """
    outcome = await SwarmBoardVerificationApplication(orchestration_calling=calling).record_verdict(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmVerdictSchema,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/converge",
    response_model=ConvergeSwarmResponse
    | OrchestrationBackendErrorResponse
    | OrchestrationErrorResponse,
    responses=SWARM_ERROR_RESPONSES,
)
async def converge_swarm_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: ConvergeSwarmRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ConvergeSwarmResponse | OrchestrationBackendErrorResponse | OrchestrationErrorResponse:
    """Record a converged candidate and validate its run response.

    Args:
        workspace_id: Workspace UUID selected by the public route.
        swarm_run_id: Swarm run UUID selected by the public route.
        payload: Strictly validated convergence command.
        response: FastAPI response carrying source status.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed convergence response or declared Orchestration error.
    """
    outcome = await SwarmBoardConvergenceApplication(orchestration_calling=calling).converge(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ConvergeSwarmResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/settle",
    response_model=ConvergeSwarmResponse
    | OrchestrationBackendErrorResponse
    | OrchestrationErrorResponse,
    responses=SWARM_ERROR_RESPONSES,
)
async def settle_swarm_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: SettleSwarmRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> ConvergeSwarmResponse | OrchestrationBackendErrorResponse | OrchestrationErrorResponse:
    """Settle an already-staged candidate run.

    Args:
        workspace_id: Workspace UUID selected by the public route.
        swarm_run_id: Swarm run UUID selected by the public route.
        payload: Strictly validated settlement request.
        response: FastAPI response carrying source status.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed settled run response or declared Orchestration error.
    """
    outcome = await SwarmBoardConvergenceApplication(orchestration_calling=calling).settle(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=ConvergeSwarmResponse,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/abort",
    response_model=SwarmRunSchema | OrchestrationBackendErrorResponse | OrchestrationErrorResponse,
    responses=SWARM_ERROR_RESPONSES,
)
async def abort_swarm_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: AbortSwarmRunRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmRunSchema | OrchestrationBackendErrorResponse | OrchestrationErrorResponse:
    """Abort a run with an explicit empty request body.

    Args:
        workspace_id: Workspace UUID selected by the public route.
        swarm_run_id: Swarm run UUID selected by the public route.
        payload: Empty validated abort request.
        response: FastAPI response carrying source status.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed aborted run or declared Orchestration error.
    """
    outcome = await SwarmBoardConvergenceApplication(orchestration_calling=calling).abort(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmRunSchema,
        workspace_id=workspace_id,
    )
    return result


@router.post(
    "/{workspace_id}/swarms/{swarm_run_id}/stall-check",
    response_model=SwarmStallCheckResponse
    | OrchestrationBackendErrorResponse
    | OrchestrationErrorResponse,
    responses=SWARM_ERROR_RESPONSES,
)
async def check_swarm_stall_route(
    workspace_id: NonNilSwarmUUID,
    swarm_run_id: NonNilSwarmUUID,
    payload: SwarmStallCheckRequest,
    response: Response,
    calling: FromDishka[OrchestrationCalling],
) -> SwarmStallCheckResponse | OrchestrationBackendErrorResponse | OrchestrationErrorResponse:
    """Evaluate deterministic stall and livelock thresholds.

    Args:
        workspace_id: Workspace UUID selected by the public route.
        swarm_run_id: Swarm run UUID selected by the public route.
        payload: Strictly validated stall check request.
        response: FastAPI response carrying source status.
        calling: Request-scoped Orchestration caller.
    Return:
        Typed stall report or declared Orchestration error.
    """
    outcome = await SwarmBoardConvergenceApplication(orchestration_calling=calling).evaluate_stall(
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        request=payload,
    )
    result = orchestration_http_response(
        outcome=outcome,
        response=response,
        response_model=SwarmStallCheckResponse,
        workspace_id=workspace_id,
    )
    return result
