"""Typed Forge HTTP entry points for the cohesive feature area."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status
from fastapi import Response as FastAPIResponse

from app.forge.application.forge_swarm_app import ForgeSwarmApplication
from app.forge.exceptions.forge_exceptions import FORGE_ERROR_RESPONSES, ForgeFailureEnvelope
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import (
    ForgeSwarmMemberCaptureCommandRequest,
    ForgeSwarmMemberCaptureResponse,
)
from app.forge.schema.swarm.convergence.forge_swarm_convergence_schema import (
    ForgeSwarmConvergeCommandRequest,
    ForgeSwarmConvergeResponse,
)
from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmMaterializeHybridCommandRequest,
    ForgeSwarmMaterializeHybridResponse,
    ForgeSwarmSettleCommandRequest,
    ForgeSwarmSettlementGetCommandRequest,
    ForgeSwarmSettlementGetResponse,
    ForgeSwarmSettleResponse,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeCommandRequest,
    ForgeSwarmPurgeResponse,
    ForgeSwarmWorkspaceGetCommandRequest,
    ForgeSwarmWorkspaceGetResponse,
    ForgeSwarmWorkspaceProvisionCommandRequest,
    ForgeSwarmWorkspaceProvisionResponse,
)
from app.forge.utils.forge_route_utils import forge_http_response
from app.shared.api_calling_box.forge_calling import ForgeCalling

router = APIRouter(route_class=DishkaRoute)


@router.post(
    "/swarms/workspaces/provision",
    response_model=ForgeSwarmWorkspaceProvisionResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def provision_swarm_workspace_route(
    request: ForgeSwarmWorkspaceProvisionCommandRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeSwarmWorkspaceProvisionResponse | ForgeFailureEnvelope:
    """Provision one isolated Swarm member workspace."""
    outcome = await ForgeSwarmApplication(calling=forge_calling).provision_workspace(
        request=request
    )
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeSwarmWorkspaceProvisionResponse,
    )
    return result


@router.post(
    "/swarms/workspaces/inspect",
    response_model=ForgeSwarmWorkspaceGetResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def inspect_swarm_workspace_route(
    request: ForgeSwarmWorkspaceGetCommandRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeSwarmWorkspaceGetResponse | ForgeFailureEnvelope:
    """Inspect one provisioned Swarm member workspace."""
    outcome = await ForgeSwarmApplication(calling=forge_calling).fetch_workspace(request=request)
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeSwarmWorkspaceGetResponse,
    )
    return result


@router.post(
    "/swarms/members/capture",
    response_model=ForgeSwarmMemberCaptureResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def capture_swarm_member_route(
    request: ForgeSwarmMemberCaptureCommandRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeSwarmMemberCaptureResponse | ForgeFailureEnvelope:
    """Capture a completed member workspace snapshot."""
    outcome = await ForgeSwarmApplication(calling=forge_calling).capture_member(request=request)
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeSwarmMemberCaptureResponse,
    )
    return result


@router.post(
    "/swarms/converge",
    response_model=ForgeSwarmConvergeResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def converge_swarm_route(
    request: ForgeSwarmConvergeCommandRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeSwarmConvergeResponse | ForgeFailureEnvelope:
    """Converge captured Swarm member outputs."""
    outcome = await ForgeSwarmApplication(calling=forge_calling).converge(request=request)
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeSwarmConvergeResponse,
    )
    return result


@router.post(
    "/swarms/settle",
    response_model=ForgeSwarmSettleResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def settle_swarm_route(
    request: ForgeSwarmSettleCommandRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeSwarmSettleResponse | ForgeFailureEnvelope:
    """Settle a converged standalone Swarm run."""
    outcome = await ForgeSwarmApplication(calling=forge_calling).settle(request=request)
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeSwarmSettleResponse,
    )
    return result


@router.post(
    "/swarms/materialize-hybrid",
    response_model=ForgeSwarmMaterializeHybridResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def materialize_hybrid_swarm_route(
    request: ForgeSwarmMaterializeHybridCommandRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeSwarmMaterializeHybridResponse | ForgeFailureEnvelope:
    """Materialize a converged hybrid Swarm result into its DAG node."""
    outcome = await ForgeSwarmApplication(calling=forge_calling).materialize_hybrid(request=request)
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeSwarmMaterializeHybridResponse,
    )
    return result


@router.post(
    "/swarms/settlement",
    response_model=ForgeSwarmSettlementGetResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def fetch_swarm_settlement_route(
    request: ForgeSwarmSettlementGetCommandRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeSwarmSettlementGetResponse | ForgeFailureEnvelope:
    """Read durable Swarm settlement and outbox state."""
    outcome = await ForgeSwarmApplication(calling=forge_calling).fetch_settlement(request=request)
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeSwarmSettlementGetResponse,
    )
    return result


@router.post(
    "/swarms/purge",
    response_model=ForgeSwarmPurgeResponse | ForgeFailureEnvelope,
    status_code=status.HTTP_200_OK,
    responses=FORGE_ERROR_RESPONSES,
)
async def purge_swarm_route(
    request: ForgeSwarmPurgeCommandRequest,
    response: FastAPIResponse,
    forge_calling: FromDishka[ForgeCalling],
) -> ForgeSwarmPurgeResponse | ForgeFailureEnvelope:
    """Purge ephemeral Swarm workspace projections."""
    outcome = await ForgeSwarmApplication(calling=forge_calling).purge(request=request)
    result = forge_http_response(
        outcome=outcome,
        request_id=request.request_id,
        response=response,
        success_model=ForgeSwarmPurgeResponse,
    )
    return result
