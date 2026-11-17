"""Typed command applications for Forge Swarm workspace operations."""

from collections.abc import Callable
from functools import partial
from uuid import UUID

from pydantic import ConfigDict, TypeAdapter

from app.forge.application.forge_command_utils import (
    execute_forge_command,
    session_actor_dto,
    workspace_scope_dto,
)
from app.forge.application.forge_swarm_dto import (
    ForgeSwarmCommandPayloadDict,
    ForgeSwarmConvergeCommandDto,
    ForgeSwarmConvergenceResponseDict,
    ForgeSwarmMaterializeHybridCommandDto,
    ForgeSwarmMemberCaptureCommandDto,
    ForgeSwarmMemberOutputInnerDto,
    ForgeSwarmMemberOutputResponseDict,
    ForgeSwarmPurgeCommandDto,
    ForgeSwarmPurgeInnerDto,
    ForgeSwarmPurgeResponseDict,
    ForgeSwarmSettleCommandDto,
    ForgeSwarmSettleInnerDto,
    ForgeSwarmSettlementGetCommandDto,
    ForgeSwarmSettlementGetInnerDto,
    ForgeSwarmSettlementGetResponseDict,
    ForgeSwarmSettlementReceiptInnerDto,
    ForgeSwarmSettlementReceiptResponseDict,
    ForgeSwarmSettleResponseDict,
    ForgeSwarmWorkspaceGetCommandDto,
    ForgeSwarmWorkspaceGetInnerDto,
    ForgeSwarmWorkspaceGetResponseDict,
    ForgeSwarmWorkspaceProvisionCommandDto,
    ForgeSwarmWorkspaceReceiptInnerDto,
    ForgeSwarmWorkspaceReceiptResponseDict,
    converge_inner_dto,
)
from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandEnvelopeDto,
    ForgeCommandOutcomeDto,
)
from app.forge.schema.envelope.forge_envelope_schema import ForgeCommandRequest
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import (
    ForgeSwarmMemberCaptureCommandRequest,
    ForgeSwarmMemberCaptureRequest,
    ForgeSwarmMemberCaptureResult,
)
from app.forge.schema.swarm.convergence.forge_swarm_convergence_schema import (
    ForgeSwarmConvergeCommandRequest,
    ForgeSwarmConvergeRequest,
    ForgeSwarmConvergeResult,
)
from app.forge.schema.swarm.identity.forge_swarm_identity_schema import (
    ForgeSwarmDagNodeHybridTarget,
    ForgeSwarmMemberIdentity,
    ForgeSwarmMemberModeIdentity,
    ForgeSwarmRunIdentity,
    ForgeSwarmSettlementReceiptIdentity,
    ForgeSwarmStandaloneTarget,
    ForgeSwarmTarget,
    ForgeSwarmWorkspaceIdentity,
    ForgeSwarmWorkspaceModeTargetIdentity,
    ForgeSwarmWorkspaceRunIdentity,
)
from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmMaterializeHybridCommandRequest,
    ForgeSwarmMaterializeHybridRequest,
    ForgeSwarmMaterializeHybridResult,
    ForgeSwarmSettleCommandRequest,
    ForgeSwarmSettlementGetCommandRequest,
    ForgeSwarmSettlementGetRequest,
    ForgeSwarmSettlementGetResult,
    ForgeSwarmSettlementReceiptResult,
    ForgeSwarmSettleRequest,
    ForgeSwarmSettleResult,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeCommandRequest,
    ForgeSwarmPurgeRequest,
    ForgeSwarmPurgeResult,
    ForgeSwarmWorkspaceGetCommandRequest,
    ForgeSwarmWorkspaceGetRequest,
    ForgeSwarmWorkspaceGetResult,
    ForgeSwarmWorkspaceProvisionCommandRequest,
    ForgeSwarmWorkspaceProvisionRequest,
    ForgeSwarmWorkspaceReceiptResult,
)
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import (
    ForgeCommandOpEnum,
    SwarmTargetKindEnum,
)
from app.shared.types.base_types import JsonObject, JsonValue

_JSON_VALUE_ADAPTER: TypeAdapter[JsonValue] = TypeAdapter(
    JsonValue,
    config=ConfigDict(strict=True, allow_inf_nan=False),
)


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
        envelope = _command_envelope(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_WORKSPACE_PROVISION,
            payload=command.to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_WORKSPACE_PROVISION,
            envelope=envelope,
            parse_result=partial(_parse_workspace_provision, payload),
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
        envelope = _command_envelope(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_WORKSPACE_GET,
            payload=command.to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_WORKSPACE_GET,
            envelope=envelope,
            parse_result=partial(_parse_workspace_get, payload),
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
        envelope = _command_envelope(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_MEMBER_CAPTURE,
            payload=command.to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_MEMBER_CAPTURE,
            envelope=envelope,
            parse_result=partial(_parse_member_capture, payload),
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
        envelope = _command_envelope(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_CONVERGE,
            payload=command.to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_CONVERGE,
            envelope=envelope,
            parse_result=partial(_parse_converge, payload),
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
        envelope = _command_envelope(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_SETTLE,
            payload=command.to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_SETTLE,
            envelope=envelope,
            parse_result=partial(_parse_settle, payload),
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
        envelope = _command_envelope(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_MATERIALIZE_HYBRID,
            payload=command.to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_MATERIALIZE_HYBRID,
            envelope=envelope,
            parse_result=partial(_parse_materialize_hybrid, payload),
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
        envelope = _command_envelope(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_SETTLEMENT_GET,
            payload=command.to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_SETTLEMENT_GET,
            envelope=envelope,
            parse_result=partial(_parse_settlement_get, payload),
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
        envelope = _command_envelope(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_PURGE,
            payload=command.to_dict(),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.SWARM_PURGE,
            envelope=envelope,
            parse_result=partial(_parse_purge, payload),
        )
        return result

    async def _execute[RequestPayload: StrictSchemaModel, ResultDict](
        self,
        request: ForgeCommandRequest[RequestPayload],
        operation: ForgeCommandOpEnum,
        envelope: ForgeCommandEnvelopeDto,
        parse_result: Callable[[JsonValue], ResultDict],
    ) -> ForgeCommandOutcomeDto[ResultDict]:
        """Execute one strict Swarm command and preserve its typed result.

        Args:
            request: Complete command request with typed request payload.
            operation: Operation fixed by the selected public route.
        envelope: Typed request envelope containing the operation DTO payload.
            parse_result: Source-aware parser returning its closed result TypedDict.
        Return:
            Validated success or failure envelope preserving source status.
        """
        if ForgeCommandOpEnum(request.op) is not operation:
            raise ValueError("Forge command operation does not match its route")
        result = await execute_forge_command(
            calling=self._calling, envelope=envelope, parse_result=parse_result
        )
        return result


def _command_envelope[PayloadSchema: StrictSchemaModel](
    request: ForgeCommandRequest[PayloadSchema],
    operation: ForgeCommandOpEnum,
    payload: ForgeSwarmCommandPayloadDict,
) -> ForgeCommandEnvelopeDto:
    """Build a versioned Forge envelope from a closed payload TypedDict.

    Args:
        request: Complete versioned request received from the caller.
        operation: Operation fixed by the selected route.
        payload: Closed total TypedDict produced by the operation DTO.
    Return:
        Immutable Forge request envelope with the caller's identity intact.
    """
    if ForgeCommandOpEnum(request.op) is not operation:
        raise ValueError("Forge command operation does not match its route")
    payload_json = _JSON_VALUE_ADAPTER.validate_python(payload, strict=True)
    result = ForgeCommandEnvelopeDto(
        forge_api=request.forge_api,
        request_id=request.request_id,
        op=operation,
        payload=payload_json,
    )
    return result


def _parse_workspace_provision(
    request: ForgeSwarmWorkspaceProvisionRequest,
    payload: JsonValue,
) -> ForgeSwarmWorkspaceReceiptResponseDict:
    """Normalize only Forge's omitted completion field, then validate the result.

    Args:
        payload: Decoded Forge provision result.
    Return:
        Strict Gateway response rebuilt from the immutable result DTO.
    """
    normalized_payload = _normalize_source_fields(payload=payload, field_names=("completed",))
    response = ForgeSwarmWorkspaceReceiptResult.model_validate(normalized_payload)
    _require_echo(
        expected=ForgeSwarmMemberIdentity(
            swarm_run_id=request.swarm_run_id,
            member_id=request.member_id,
        ),
        observed=ForgeSwarmMemberIdentity(
            swarm_run_id=response.swarm_run_id,
            member_id=response.member_id,
        ),
        identity_name="swarm workspace receipt member identity",
    )
    _require_echo(
        expected=ForgeSwarmWorkspaceModeTargetIdentity(mode=request.mode, target=request.target),
        observed=ForgeSwarmWorkspaceModeTargetIdentity(mode=response.mode, target=response.target),
        identity_name="swarm workspace receipt mode and target",
    )
    completed = response.completed
    if completed is not None:
        _require_echo(
            expected=ForgeSwarmMemberModeIdentity(
                swarm_run_id=response.swarm_run_id,
                member_id=response.member_id,
                mode=response.mode,
            ),
            observed=ForgeSwarmMemberModeIdentity(
                swarm_run_id=completed.swarm_run_id,
                member_id=completed.member_id,
                mode=completed.mode,
            ),
            identity_name="completed Swarm member identity",
        )
    result_dto = ForgeSwarmWorkspaceReceiptInnerDto.from_schema(response=response)
    result = result_dto.to_dict()
    return result


def _parse_workspace_get(
    request: ForgeSwarmWorkspaceGetRequest,
    payload: JsonValue,
) -> ForgeSwarmWorkspaceGetResponseDict:
    """Normalize Forge's omitted receipt and completed fields, then validate.

    Args:
        payload: Decoded Forge workspace lookup result.
    Return:
        Strict Gateway response rebuilt from the immutable result DTO.
    """
    normalized_payload = _normalize_source_fields(payload=payload, field_names=("receipt",))
    if isinstance(normalized_payload, dict) and isinstance(normalized_payload["receipt"], dict):
        normalized_payload["receipt"] = _normalize_source_fields(
            payload=normalized_payload["receipt"],
            field_names=("completed",),
        )
    response = ForgeSwarmWorkspaceGetResult.model_validate(normalized_payload)
    expected_identity = ForgeSwarmWorkspaceIdentity(
        workspace_id=request.scope.workspace_id,
        swarm_run_id=request.swarm_run_id,
        member_id=request.member_id,
    )
    observed_identity = ForgeSwarmWorkspaceIdentity(
        workspace_id=response.workspace_id,
        swarm_run_id=response.swarm_run_id,
        member_id=response.member_id,
    )
    _require_echo(
        expected=expected_identity,
        observed=observed_identity,
        identity_name="swarm workspace lookup identity",
    )
    if response.found != (response.receipt is not None):
        raise ValueError("Forge workspace lookup found flag does not match its receipt")
    receipt = response.receipt
    if receipt is not None:
        expected_member = ForgeSwarmMemberIdentity(
            swarm_run_id=response.swarm_run_id,
            member_id=response.member_id,
        )
        observed_member = ForgeSwarmMemberIdentity(
            swarm_run_id=receipt.swarm_run_id,
            member_id=receipt.member_id,
        )
        _require_echo(
            expected=expected_member,
            observed=observed_member,
            identity_name="nested Swarm workspace receipt identity",
        )
        completed = receipt.completed
        if completed is not None:
            _require_echo(
                expected=ForgeSwarmMemberModeIdentity(
                    swarm_run_id=receipt.swarm_run_id,
                    member_id=receipt.member_id,
                    mode=receipt.mode,
                ),
                observed=ForgeSwarmMemberModeIdentity(
                    swarm_run_id=completed.swarm_run_id,
                    member_id=completed.member_id,
                    mode=completed.mode,
                ),
                identity_name="completed Swarm member identity",
            )
    result_dto = ForgeSwarmWorkspaceGetInnerDto.from_schema(response=response)
    result = result_dto.to_dict()
    return result


def _parse_member_capture(
    request: ForgeSwarmMemberCaptureRequest,
    payload: JsonValue,
) -> ForgeSwarmMemberOutputResponseDict:
    """Validate Forge's member output receipt and rebuild its result DTO.

    Args:
        payload: Decoded Forge member capture result.
    Return:
        Strict Gateway response rebuilt from the immutable result DTO.
    """
    response = ForgeSwarmMemberCaptureResult.model_validate(payload)
    _require_echo(
        expected=ForgeSwarmMemberIdentity(
            swarm_run_id=request.swarm_run_id,
            member_id=request.member_id,
        ),
        observed=ForgeSwarmMemberIdentity(
            swarm_run_id=response.swarm_run_id,
            member_id=response.member_id,
        ),
        identity_name="captured Swarm member identity",
    )
    result_dto = ForgeSwarmMemberOutputInnerDto.from_schema(response=response)
    result = result_dto.to_dict()
    return result


def _parse_converge(
    request: ForgeSwarmConvergeRequest,
    payload: JsonValue,
) -> ForgeSwarmConvergenceResponseDict:
    """Validate tagged convergence output and rebuild its immutable result DTO.

    Args:
        payload: Decoded Forge convergence result.
    Return:
        Strict Gateway response rebuilt from the result DTO.
    """
    response = ForgeSwarmConvergeResult.model_validate(payload)
    _require_echo(
        expected=ForgeSwarmRunIdentity(swarm_run_id=request.swarm_run_id),
        observed=ForgeSwarmRunIdentity(swarm_run_id=response.root.swarm_run_id),
        identity_name="convergence Swarm run identity",
    )
    result_dto = converge_inner_dto(response=response)
    result = result_dto.to_dict()
    return result


def _parse_settle(
    request: ForgeSwarmSettleRequest,
    payload: JsonValue,
) -> ForgeSwarmSettleResponseDict:
    """Normalize Forge's omitted outbox sequence and validate the result.

    Args:
        payload: Decoded Forge settlement result.
    Return:
        Strict Gateway response rebuilt from the result DTO.
    """
    normalized_payload = _normalize_source_fields(payload=payload, field_names=("outbox_sequence",))
    response = ForgeSwarmSettleResult.model_validate(normalized_payload)
    _require_echo(
        expected=_expected_settlement_receipt_identity(
            settlement_id=request.settlement_id,
            swarm_run_id=request.swarm_run_id,
            converged_commit_oid=request.converged_commit_oid,
            target=ForgeSwarmStandaloneTarget(kind=SwarmTargetKindEnum.STANDALONE_SWARM),
        ),
        observed=_observed_settlement_receipt_identity(receipt=response.receipt),
        identity_name="standalone settlement receipt identity and target",
    )
    result_dto = ForgeSwarmSettleInnerDto.from_schema(response=response)
    result = result_dto.to_dict()
    return result


def _parse_materialize_hybrid(
    request: ForgeSwarmMaterializeHybridRequest,
    payload: JsonValue,
) -> ForgeSwarmSettlementReceiptResponseDict:
    """Validate hybrid materialization and rebuild its immutable result DTO.

    Args:
        payload: Decoded Forge hybrid settlement receipt.
    Return:
        Strict Gateway response rebuilt from the result DTO.
    """
    response = ForgeSwarmMaterializeHybridResult.model_validate(payload)
    expected_target = ForgeSwarmDagNodeHybridTarget(
        kind=SwarmTargetKindEnum.DAG_NODE_HYBRID,
        goal_id=request.goal_id,
        dag_revision=request.expected_dag_revision,
        node_id=request.node_id,
    )
    _require_echo(
        expected=_expected_settlement_receipt_identity(
            settlement_id=request.settlement_id,
            swarm_run_id=request.swarm_run_id,
            converged_commit_oid=request.converged_commit_oid,
            target=expected_target,
        ),
        observed=_observed_settlement_receipt_identity(receipt=response),
        identity_name="hybrid settlement receipt identity and target",
    )
    result_dto = ForgeSwarmSettlementReceiptInnerDto.from_schema(response=response)
    result = result_dto.to_dict()
    return result


def _parse_settlement_get(
    request: ForgeSwarmSettlementGetRequest,
    payload: JsonValue,
) -> ForgeSwarmSettlementGetResponseDict:
    """Normalize omitted settlement fields and rebuild the result DTO.

    Args:
        payload: Decoded Forge settlement lookup result.
    Return:
        Strict Gateway response rebuilt from the result DTO.
    """
    normalized_payload = _normalize_source_fields(
        payload=payload, field_names=("receipt", "outbox_entry")
    )
    response = ForgeSwarmSettlementGetResult.model_validate(normalized_payload)
    _require_echo(
        expected=ForgeSwarmWorkspaceRunIdentity(
            workspace_id=request.scope.workspace_id,
            swarm_run_id=request.swarm_run_id,
        ),
        observed=ForgeSwarmWorkspaceRunIdentity(
            workspace_id=response.workspace_id,
            swarm_run_id=response.swarm_run_id,
        ),
        identity_name="settlement lookup workspace and run identity",
    )
    receipt = response.receipt
    if receipt is not None:
        _require_echo(
            expected=ForgeSwarmRunIdentity(swarm_run_id=request.swarm_run_id),
            observed=ForgeSwarmRunIdentity(swarm_run_id=receipt.swarm_run_id),
            identity_name="nested settlement receipt run identity",
        )
    outbox_entry = response.outbox_entry
    if outbox_entry is not None:
        _require_echo(
            expected=ForgeSwarmWorkspaceRunIdentity(
                workspace_id=request.scope.workspace_id,
                swarm_run_id=request.swarm_run_id,
            ),
            observed=ForgeSwarmWorkspaceRunIdentity(
                workspace_id=outbox_entry.workspace_id,
                swarm_run_id=outbox_entry.fact.swarm_run_id,
            ),
            identity_name="settlement outbox workspace and run identity",
        )
        _require_echo(
            expected=ForgeSwarmWorkspaceRunIdentity(
                workspace_id=request.scope.workspace_id,
                swarm_run_id=request.swarm_run_id,
            ),
            observed=ForgeSwarmWorkspaceRunIdentity(
                workspace_id=outbox_entry.fact.workspace_id,
                swarm_run_id=outbox_entry.fact.swarm_run_id,
            ),
            identity_name="settled effect fact workspace and run identity",
        )
        if receipt is not None and str(outbox_entry.fact.settlement_id) != receipt.settlement_id:
            raise ValueError("settlement receipt and outbox fact identities do not match")
    result_dto = ForgeSwarmSettlementGetInnerDto.from_schema(response=response)
    result = result_dto.to_dict()
    return result


def _parse_purge(
    request: ForgeSwarmPurgeRequest,
    payload: JsonValue,
) -> ForgeSwarmPurgeResponseDict:
    """Validate Forge's purge result and rebuild its immutable result DTO.

    Args:
        payload: Decoded Forge purge result.
    Return:
        Strict Gateway response rebuilt from the result DTO.
    """
    response = ForgeSwarmPurgeResult.model_validate(payload)
    _require_echo(
        expected=ForgeSwarmWorkspaceRunIdentity(
            workspace_id=request.scope.workspace_id,
            swarm_run_id=request.swarm_run_id,
        ),
        observed=ForgeSwarmWorkspaceRunIdentity(
            workspace_id=response.workspace_id,
            swarm_run_id=response.swarm_run_id,
        ),
        identity_name="purge workspace and run identity",
    )
    if not response.purged:
        raise ValueError("Forge purge command did not confirm the requested purge")
    result_dto = ForgeSwarmPurgeInnerDto.from_schema(response=response)
    result = result_dto.to_dict()
    return result


def _require_echo[IdentitySchema: StrictSchemaModel](
    expected: IdentitySchema,
    observed: IdentitySchema,
    identity_name: str,
) -> None:
    """Reject Source result identity fields that differ from the admitted request.

    Args:
        expected: Concrete Source identity derived from the operation request.
        observed: Same concrete identity shape decoded from the operation result.
        identity_name: Sanitized identity label for the raised parse failure.
    Return:
        None.
    """
    if expected != observed:
        raise ValueError(f"Forge {identity_name} does not match the request")


def _expected_settlement_receipt_identity(
    settlement_id: UUID,
    swarm_run_id: UUID,
    converged_commit_oid: str,
    target: ForgeSwarmTarget,
) -> ForgeSwarmSettlementReceiptIdentity:
    """Build the receipt fields the Rust client requires to echo.

    Args:
        settlement_id: Caller-selected durable settlement identity.
        swarm_run_id: Caller-selected Swarm run identity.
        converged_commit_oid: Exact converged commit selected by the caller.
        target: Target fixed by settle or hybrid materialization semantics.
    Return:
        Strict identity projection for Source receipt equality.
    """
    result = ForgeSwarmSettlementReceiptIdentity(
        settlement_id=str(settlement_id),
        swarm_run_id=swarm_run_id,
        converged_commit_oid=converged_commit_oid,
        target=target,
    )
    return result


def _observed_settlement_receipt_identity(
    receipt: ForgeSwarmSettlementReceiptResult,
) -> ForgeSwarmSettlementReceiptIdentity:
    """Project exactly the receipt identity and target fields echoed by Forge.

    Args:
        receipt: Validated Source Swarm settlement receipt.
    Return:
        Strict Source identity projection used for request equality.
    """
    result = ForgeSwarmSettlementReceiptIdentity(
        settlement_id=receipt.settlement_id,
        swarm_run_id=receipt.swarm_run_id,
        converged_commit_oid=receipt.converged_commit_oid,
        target=receipt.target,
    )
    return result


def _normalize_source_fields(payload: JsonValue, field_names: tuple[str, ...]) -> JsonValue:
    """Normalize only source-declared omitted Option fields before public validation.

    Args:
        payload: Decoded response value from Forge.
        field_names: Exact source wire fields that use skip_serializing_if.
    Return:
        Copy retaining every source key with absent listed fields set to null.
    """
    if not isinstance(payload, dict):
        result = payload
        return result
    normalized: JsonObject = {key: value for key, value in payload.items()}
    for field_name in field_names:
        if field_name not in normalized:
            normalized[field_name] = None
    result = normalized
    return result
