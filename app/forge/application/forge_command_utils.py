"""Typed request mapping and Source envelope validation for Forge commands."""

from collections.abc import Callable
from uuid import UUID

from fastapi import status
from pydantic import JsonValue, ValidationError

from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandEnvelopeDto,
    ForgeCommandOutcomeDto,
    ForgeCommandSuccessEnvelopeDto,
    ForgeLocatorDto,
    ForgePrincipalDto,
    ForgeSessionActorDto,
    ForgeWorkspaceScopeDto,
)
from app.forge.exceptions.forge_exceptions import (
    ForgeFailureEnvelope,
    ForgeReadbackHint,
    ForgeSwarmSettlementReadback,
    ForgeSwarmWorkspaceReadback,
)
from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeSessionActor,
    ForgeSuccessEnvelope,
    ForgeWorkspaceScope,
)
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.exception import ForgeExcept
from app.shared.ingredient_element.forge.forge_enums import (
    ForgeCommandOpEnum,
    ForgeErrorCodeEnum,
    ForgePrincipalKindEnum,
    ForgeReadbackKindEnum,
)
from app.shared.types.upstream_exchange import UpstreamJsonExchange
from app.shared.types.wire_scalar_types import parse_wire_uuid

_PRE_ENVELOPE_REJECTIONS: dict[int, tuple[ForgeErrorCodeEnum, ...]] = {
    status.HTTP_400_BAD_REQUEST: (
        ForgeErrorCodeEnum.AUTH_FAILED,
        ForgeErrorCodeEnum.INVALID_INPUT,
    ),
    status.HTTP_503_SERVICE_UNAVAILABLE: (ForgeErrorCodeEnum.CAPACITY_EXCEEDED,),
}
_SOURCE_FAILURE_STATUSES = (
    status.HTTP_202_ACCEPTED,
    status.HTTP_400_BAD_REQUEST,
    status.HTTP_409_CONFLICT,
    status.HTTP_503_SERVICE_UNAVAILABLE,
)


def workspace_scope_dto(scope: ForgeWorkspaceScope) -> ForgeWorkspaceScopeDto:
    """Convert the strict Workspace scope schema to its immutable DTO.

    Args:
        scope: Validated Forge Workspace scope.
    Return:
        Immutable Forge Workspace scope DTO.
    """
    locator = ForgeLocatorDto(
        location_id=scope.locator.location_id,
        expected_revision=scope.locator.expected_revision,
        relative_root=scope.locator.relative_root,
    )
    result = ForgeWorkspaceScopeDto(
        workspace_id=scope.workspace_id,
        workspace_revision=scope.workspace_revision,
        locator=locator,
    )
    return result


def session_actor_dto(actor: ForgeSessionActor) -> ForgeSessionActorDto:
    """Convert the strict Session actor schema to its immutable DTO.

    Args:
        actor: Validated Forge Session actor.
    Return:
        Immutable Forge Session actor DTO.
    """
    principal = actor.principal
    principal_dto = ForgePrincipalDto(
        kind=ForgePrincipalKindEnum(principal.kind),
        token_id=principal.token_id,
        grant_id=principal.grant_id,
    )
    result = ForgeSessionActorDto(
        session_id=actor.session_id,
        principal=principal_dto,
        workspace_id=actor.workspace_id,
    )
    return result


async def execute_forge_command[ResultDictT](
    calling: ForgeCalling,
    envelope: ForgeCommandEnvelopeDto,
    parse_result: Callable[[JsonValue], ResultDictT],
) -> ForgeCommandOutcomeDto[ResultDictT]:
    """Send and validate one versioned Forge command exchange.

    Args:
        calling: Request-scoped Forge HTTP caller.
        envelope: Immutable command envelope with caller-supplied identity.
        parse_result: Operation parser returning its concrete result TypedDict.
    Return:
        Typed Source response DTO with its original HTTP status.
    """
    exchange = await calling.call_command(
        op=envelope.op,
        request_id=envelope.request_id,
        envelope=envelope.to_dict(),
    )
    result = validate_command_exchange(
        exchange=exchange, envelope=envelope, parse_result=parse_result
    )
    if result.status_code == status.HTTP_202_ACCEPTED:
        calling.record_unknown_outcome()
    return result


def validate_command_exchange[ResultDictT](
    exchange: UpstreamJsonExchange,
    envelope: ForgeCommandEnvelopeDto,
    parse_result: Callable[[JsonValue], ResultDictT],
) -> ForgeCommandOutcomeDto[ResultDictT]:
    """Validate Source status, common envelope, identity, and operation result.

    Args:
        exchange: Decoded JSON value and HTTP status from the bounded caller.
        envelope: Original caller-supplied command identity and readback scope.
        parse_result: Operation parser returning its concrete result TypedDict.
    Return:
        Typed Source response DTO preserving its original HTTP status.
    """
    request_id = envelope.request_id
    if exchange.status_code == status.HTTP_200_OK:
        result = _validate_success(
            payload=exchange.payload, request_id=request_id, parse_result=parse_result
        )
    else:
        failure = _validate_failure(
            status_code=exchange.status_code, payload=exchange.payload, request_id=request_id
        )
        _validate_readback_identity(envelope=envelope, readback=failure.error.readback)
        result = ForgeCommandOutcomeDto(
            status_code=exchange.status_code,
            response=failure.to_inner_dto(),
        )
    return result


def _workspace_readback(payload: JsonValue) -> ForgeSwarmWorkspaceReadback:
    """Project the exact source workspace readback identity from a command payload."""
    if not isinstance(payload, dict):
        raise ValueError("Forge command payload must be an object")
    scope = ForgeWorkspaceScope.model_validate(payload["scope"])
    result = ForgeSwarmWorkspaceReadback(
        kind=ForgeReadbackKindEnum.SWARM_WORKSPACE,
        workspace_id=scope.workspace_id,
        swarm_run_id=parse_wire_uuid(value=payload["swarm_run_id"]),
        member_id=parse_wire_uuid(value=payload["member_id"]),
    )
    return result


def _settlement_readback(payload: JsonValue) -> ForgeSwarmSettlementReadback:
    """Project the exact source settlement readback identity from a command payload."""
    if not isinstance(payload, dict):
        raise ValueError("Forge command payload must be an object")
    scope = ForgeWorkspaceScope.model_validate(payload["scope"])
    result = ForgeSwarmSettlementReadback(
        kind=ForgeReadbackKindEnum.SWARM_SETTLEMENT,
        workspace_id=scope.workspace_id,
        swarm_run_id=parse_wire_uuid(value=payload["swarm_run_id"]),
        settlement_id=parse_wire_uuid(value=payload["settlement_id"]),
    )
    return result


_READBACK_IDENTITIES: dict[ForgeCommandOpEnum, Callable[[JsonValue], ForgeReadbackHint]] = {
    ForgeCommandOpEnum.SWARM_WORKSPACE_PROVISION: _workspace_readback,
    ForgeCommandOpEnum.SWARM_MEMBER_CAPTURE: _workspace_readback,
    ForgeCommandOpEnum.SWARM_SETTLE: _settlement_readback,
    ForgeCommandOpEnum.SWARM_MATERIALIZE_HYBRID: _settlement_readback,
}


def _validate_readback_identity(
    envelope: ForgeCommandEnvelopeDto,
    readback: ForgeReadbackHint | None,
) -> None:
    """Fence a present source readback to the exact operation and caller scope."""
    if readback is None:
        return
    try:
        expected = _READBACK_IDENTITIES[envelope.op](envelope.payload)
    except (KeyError, ValueError) as error:
        raise _invalid_forge_exchange(request_id=envelope.request_id) from error
    if readback != expected:
        raise _invalid_forge_exchange(request_id=envelope.request_id)


def _validate_success[ResultDictT](
    payload: JsonValue,
    request_id: UUID,
    parse_result: Callable[[JsonValue], ResultDictT],
) -> ForgeCommandOutcomeDto[ResultDictT]:
    try:
        response = ForgeSuccessEnvelope[JsonValue].model_validate(payload)
    except (ValidationError, ValueError) as error:
        raise _invalid_forge_exchange(request_id=request_id) from error
    if response.request_id != request_id:
        raise _invalid_forge_exchange(request_id=request_id)
    try:
        result_dict = parse_result(response.result)
    except (ValidationError, ValueError) as error:
        raise _invalid_forge_exchange(request_id=request_id) from error
    success = ForgeCommandSuccessEnvelopeDto[ResultDictT](
        forge_api=response.forge_api,
        request_id=response.request_id,
        result=result_dict,
    )
    result: ForgeCommandOutcomeDto[ResultDictT] = ForgeCommandOutcomeDto(
        status_code=status.HTTP_200_OK,
        response=success,
    )
    return result


def _validate_failure(
    status_code: int,
    payload: JsonValue,
    request_id: UUID,
) -> ForgeFailureEnvelope:
    if status_code not in _SOURCE_FAILURE_STATUSES:
        raise _invalid_forge_exchange(request_id=request_id)
    try:
        response = ForgeFailureEnvelope.model_validate(payload)
    except (ValidationError, ValueError) as error:
        raise _invalid_forge_exchange(request_id=request_id) from error

    error_code = ForgeErrorCodeEnum(response.error.code)
    response_request_id = response.request_id
    if response_request_id != request_id and not _is_pre_envelope_rejection(
        status_code=status_code,
        error_code=error_code,
        request_id=response_request_id,
    ):
        raise _invalid_forge_exchange(request_id=request_id)
    if (
        status_code == status.HTTP_202_ACCEPTED
        and error_code is not ForgeErrorCodeEnum.UNKNOWN_OUTCOME
    ):
        raise _invalid_forge_exchange(request_id=request_id)
    if error_code is ForgeErrorCodeEnum.UNKNOWN_OUTCOME and status_code != status.HTTP_202_ACCEPTED:
        raise _invalid_forge_exchange(request_id=request_id)
    return response


def _is_pre_envelope_rejection(
    status_code: int,
    error_code: ForgeErrorCodeEnum,
    request_id: UUID,
) -> bool:
    allowed_codes = _PRE_ENVELOPE_REJECTIONS.get(status_code, ())
    result = request_id.int == 0 and error_code in allowed_codes
    return result


def _invalid_forge_exchange(request_id: UUID) -> ForgeExcept:
    result = ForgeExcept(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="forge_invalid_payload",
        message="Upstream forge returned an invalid command envelope",
        retryable=False,
        request_id=request_id,
    )
    return result
