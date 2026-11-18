"""Typed command applications for Forge Swarm workspace operations."""

from collections.abc import Callable
from functools import partial

from pydantic import JsonValue

from app.forge.application.forge_command_utils import (
    execute_forge_command,
    session_actor_dto,
    workspace_scope_dto,
)
from app.forge.application.forge_swarm_parsers import (
    parse_converge,
    parse_materialize_hybrid,
    parse_member_capture,
    parse_purge,
    parse_settle,
    parse_settlement_get,
    parse_workspace_get,
    parse_workspace_provision,
)
from app.forge.application.inner_dto.forge_envelope_dto import ForgeCommandOutcomeDto
from app.forge.application.inner_dto.forge_swarm_command_dto import (
    ForgeSwarmConvergeCommandDto,
    ForgeSwarmMaterializeHybridCommandDto,
    ForgeSwarmMemberCaptureCommandDto,
    ForgeSwarmPurgeCommandDto,
    ForgeSwarmSettleCommandDto,
    ForgeSwarmSettlementGetCommandDto,
    ForgeSwarmWorkspaceGetCommandDto,
    ForgeSwarmWorkspaceProvisionCommandDto,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmCommandPayloadDict,
    ForgeSwarmConvergenceResponseDict,
    ForgeSwarmMemberOutputResponseDict,
    ForgeSwarmPurgeResponseDict,
    ForgeSwarmSettlementGetResponseDict,
    ForgeSwarmSettlementReceiptResponseDict,
    ForgeSwarmSettleResponseDict,
    ForgeSwarmWorkspaceGetResponseDict,
    ForgeSwarmWorkspaceReceiptResponseDict,
)
from app.forge.schema.envelope.forge_envelope_schema import ForgeCommandRequest
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import (
    ForgeSwarmMemberCaptureCommandRequest,
)
from app.forge.schema.swarm.convergence.forge_swarm_convergence_schema import (
    ForgeSwarmConvergeCommandRequest,
)
from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmMaterializeHybridCommandRequest,
    ForgeSwarmSettleCommandRequest,
    ForgeSwarmSettlementGetCommandRequest,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeCommandRequest,
    ForgeSwarmWorkspaceGetCommandRequest,
    ForgeSwarmWorkspaceProvisionCommandRequest,
)
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum


class ForgeSwarmApplication:
    """Execute Forge Swarm commands without taking domain authority."""

    def __init__(self, calling: ForgeCalling) -> None:
        """Bind one request-scoped Forge caller.

        Args:
            calling: Request-scoped authenticated Forge caller.
        Return:
            None.
        """
        self._calling = calling

    async def provision_workspace(
        self,
        request: ForgeSwarmWorkspaceProvisionCommandRequest,
    ) -> ForgeCommandOutcomeDto[ForgeSwarmWorkspaceReceiptResponseDict]:
        """Provision a member workspace through the Forge command endpoint.

        Args:
            request: Complete versioned Forge request and typed payload.
        Return:
            Validated Forge response envelope with its source status.
        """
        payload = request.payload
        command = ForgeSwarmWorkspaceProvisionCommandDto.from_request(
            request=payload,
            scope=workspace_scope_dto(scope=payload.scope).to_dict(),
            actor=session_actor_dto(actor=payload.actor),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_WORKSPACE_PROVISION,
            payload=command.to_dict(),
            parse_result=partial(parse_workspace_provision, payload),
        )
        return result

    async def fetch_workspace(
        self,
        request: ForgeSwarmWorkspaceGetCommandRequest,
    ) -> ForgeCommandOutcomeDto[ForgeSwarmWorkspaceGetResponseDict]:
        """Read a member workspace receipt through Forge.

        Args:
            request: Complete versioned Forge request and typed payload.
        Return:
            Validated Forge response envelope with its source status.
        """
        payload = request.payload
        command = ForgeSwarmWorkspaceGetCommandDto.from_request(
            request=payload,
            scope=workspace_scope_dto(scope=payload.scope).to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_WORKSPACE_GET,
            payload=command.to_dict(),
            parse_result=partial(parse_workspace_get, payload),
        )
        return result

    async def capture_member(
        self,
        request: ForgeSwarmMemberCaptureCommandRequest,
    ) -> ForgeCommandOutcomeDto[ForgeSwarmMemberOutputResponseDict]:
        """Capture a member workspace result through Forge.

        Args:
            request: Complete versioned Forge request and typed payload.
        Return:
            Validated Forge response envelope with its source status.
        """
        payload = request.payload
        command = ForgeSwarmMemberCaptureCommandDto.from_request(
            request=payload,
            scope=workspace_scope_dto(scope=payload.scope).to_dict(),
            actor=session_actor_dto(actor=payload.actor),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_MEMBER_CAPTURE,
            payload=command.to_dict(),
            parse_result=partial(parse_member_capture, payload),
        )
        return result

    async def converge(
        self,
        request: ForgeSwarmConvergeCommandRequest,
    ) -> ForgeCommandOutcomeDto[ForgeSwarmConvergenceResponseDict]:
        """Compare captured member outputs through Forge.

        Args:
            request: Complete versioned Forge request and typed payload.
        Return:
            Validated Forge response envelope with its source status.
        """
        payload = request.payload
        command = ForgeSwarmConvergeCommandDto.from_request(
            request=payload,
            scope=workspace_scope_dto(scope=payload.scope).to_dict(),
            actor=session_actor_dto(actor=payload.actor),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_CONVERGE,
            payload=command.to_dict(),
            parse_result=partial(parse_converge, payload),
        )
        return result

    async def settle(
        self,
        request: ForgeSwarmSettleCommandRequest,
    ) -> ForgeCommandOutcomeDto[ForgeSwarmSettleResponseDict]:
        """Settle a converged Swarm run through Forge.

        Args:
            request: Complete versioned Forge request and typed payload.
        Return:
            Validated Forge response envelope with its source status.
        """
        payload = request.payload
        command = ForgeSwarmSettleCommandDto.from_request(
            request=payload,
            scope=workspace_scope_dto(scope=payload.scope).to_dict(),
            actor=session_actor_dto(actor=payload.actor),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_SETTLE,
            payload=command.to_dict(),
            parse_result=partial(parse_settle, payload),
        )
        return result

    async def materialize_hybrid(
        self,
        request: ForgeSwarmMaterializeHybridCommandRequest,
    ) -> ForgeCommandOutcomeDto[ForgeSwarmSettlementReceiptResponseDict]:
        """Materialize a Swarm settlement into a fenced DAG node through Forge.

        Args:
            request: Complete versioned Forge request and typed payload.
        Return:
            Validated Forge response envelope with its source status.
        """
        payload = request.payload
        command = ForgeSwarmMaterializeHybridCommandDto.from_request(
            request=payload,
            scope=workspace_scope_dto(scope=payload.scope).to_dict(),
            actor=session_actor_dto(actor=payload.actor),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_MATERIALIZE_HYBRID,
            payload=command.to_dict(),
            parse_result=partial(parse_materialize_hybrid, payload),
        )
        return result

    async def fetch_settlement(
        self,
        request: ForgeSwarmSettlementGetCommandRequest,
    ) -> ForgeCommandOutcomeDto[ForgeSwarmSettlementGetResponseDict]:
        """Read the settlement and outbox projection through Forge.

        Args:
            request: Complete versioned Forge request and typed payload.
        Return:
            Validated Forge response envelope with its source status.
        """
        payload = request.payload
        command = ForgeSwarmSettlementGetCommandDto.from_request(
            request=payload,
            scope=workspace_scope_dto(scope=payload.scope).to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_SETTLEMENT_GET,
            payload=command.to_dict(),
            parse_result=partial(parse_settlement_get, payload),
        )
        return result

    async def purge(
        self,
        request: ForgeSwarmPurgeCommandRequest,
    ) -> ForgeCommandOutcomeDto[ForgeSwarmPurgeResponseDict]:
        """Purge a Swarm workspace projection through Forge.

        Args:
            request: Complete versioned Forge request and typed payload.
        Return:
            Validated Forge response envelope with its source status.
        """
        payload = request.payload
        command = ForgeSwarmPurgeCommandDto.from_request(
            request=payload,
            scope=workspace_scope_dto(scope=payload.scope).to_dict(),
            actor=session_actor_dto(actor=payload.actor),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_PURGE,
            payload=command.to_dict(),
            parse_result=partial(parse_purge, payload),
        )
        return result

    async def _execute[RequestPayload: StrictSchemaModel, ResultDict](
        self,
        request: ForgeCommandRequest[RequestPayload],
        operation: ForgeCommandOpEnum,
        payload: ForgeSwarmCommandPayloadDict,
        parse_result: Callable[[JsonValue], ResultDict],
    ) -> ForgeCommandOutcomeDto[ResultDict]:
        """Execute one strict Swarm command and preserve its typed result.

        Args:
            request: Complete command request with typed request payload.
            operation: Operation fixed by the selected public route.
            payload: Closed TypedDict operation payload.
            parse_result: Source-aware parser returning its closed result TypedDict.
        Return:
            Validated success or failure envelope preserving source status.
        """
        if ForgeCommandOpEnum(request.op) is not operation:
            raise ValueError("Forge command operation does not match its route")
        envelope = request.to_inner_dto(payload=payload)
        result = await execute_forge_command(
            calling=self._calling, envelope=envelope, parse_result=parse_result
        )
        return result
