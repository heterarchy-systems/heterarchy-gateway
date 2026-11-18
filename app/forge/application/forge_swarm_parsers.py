"""Source normalization and response parsers for Forge Swarm commands."""

from uuid import UUID

from pydantic import JsonValue

from app.forge.application.inner_dto.forge_swarm_result_dto import (
    ForgeSwarmMemberOutputInnerDto,
    ForgeSwarmWorkspaceGetInnerDto,
    ForgeSwarmWorkspaceReceiptInnerDto,
    converge_inner_dto,
)
from app.forge.application.inner_dto.forge_swarm_settlement_dto import (
    ForgeSwarmPurgeInnerDto,
    ForgeSwarmSettleInnerDto,
    ForgeSwarmSettlementGetInnerDto,
    ForgeSwarmSettlementReceiptInnerDto,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmConvergenceResponseDict,
    ForgeSwarmMemberOutputResponseDict,
    ForgeSwarmPurgeResponseDict,
    ForgeSwarmSettlementGetResponseDict,
    ForgeSwarmSettlementReceiptResponseDict,
    ForgeSwarmSettleResponseDict,
    ForgeSwarmWorkspaceGetResponseDict,
    ForgeSwarmWorkspaceReceiptResponseDict,
)
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import (
    ForgeSwarmMemberCaptureRequest,
    ForgeSwarmMemberCaptureResult,
)
from app.forge.schema.swarm.convergence.forge_swarm_convergence_schema import (
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
    ForgeSwarmMaterializeHybridRequest,
    ForgeSwarmMaterializeHybridResult,
    ForgeSwarmSettlementGetRequest,
    ForgeSwarmSettlementGetResult,
    ForgeSwarmSettlementReceiptResult,
    ForgeSwarmSettleRequest,
    ForgeSwarmSettleResult,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeRequest,
    ForgeSwarmPurgeResult,
    ForgeSwarmWorkspaceGetRequest,
    ForgeSwarmWorkspaceGetResult,
    ForgeSwarmWorkspaceProvisionRequest,
    ForgeSwarmWorkspaceReceiptResult,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import SwarmTargetKindEnum
from app.shared.types.base_types import JsonObject


def parse_workspace_provision(
    request: ForgeSwarmWorkspaceProvisionRequest,
    payload: JsonValue,
) -> ForgeSwarmWorkspaceReceiptResponseDict:
    """Normalize only Forge's omitted completion field, then validate the result.

    Args:
        request: Original Swarm workspace provision request for echo verification.
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


def parse_workspace_get(
    request: ForgeSwarmWorkspaceGetRequest,
    payload: JsonValue,
) -> ForgeSwarmWorkspaceGetResponseDict:
    """Normalize Forge's omitted receipt and completed fields, then validate.

    Args:
        request: Original Swarm workspace lookup request for echo verification.
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


def parse_member_capture(
    request: ForgeSwarmMemberCaptureRequest,
    payload: JsonValue,
) -> ForgeSwarmMemberOutputResponseDict:
    """Validate Forge's member output receipt and rebuild its result DTO.

    Args:
        request: Original Swarm member capture request for echo verification.
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


def parse_converge(
    request: ForgeSwarmConvergeRequest,
    payload: JsonValue,
) -> ForgeSwarmConvergenceResponseDict:
    """Validate tagged convergence output and rebuild its immutable result DTO.

    Args:
        request: Original Swarm convergence request for echo verification.
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


def parse_settle(
    request: ForgeSwarmSettleRequest,
    payload: JsonValue,
) -> ForgeSwarmSettleResponseDict:
    """Normalize Forge's omitted outbox sequence and validate the result.

    Args:
        request: Original Swarm settlement request for echo verification.
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


def parse_materialize_hybrid(
    request: ForgeSwarmMaterializeHybridRequest,
    payload: JsonValue,
) -> ForgeSwarmSettlementReceiptResponseDict:
    """Validate hybrid materialization and rebuild its immutable result DTO.

    Args:
        request: Original hybrid materialization request for echo verification.
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


def parse_settlement_get(
    request: ForgeSwarmSettlementGetRequest,
    payload: JsonValue,
) -> ForgeSwarmSettlementGetResponseDict:
    """Normalize omitted settlement fields and rebuild the result DTO.

    Args:
        request: Original settlement lookup request for echo verification.
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


def parse_purge(
    request: ForgeSwarmPurgeRequest,
    payload: JsonValue,
) -> ForgeSwarmPurgeResponseDict:
    """Validate Forge's purge result and rebuild its immutable result DTO.

    Args:
        request: Original purge request for echo verification.
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
