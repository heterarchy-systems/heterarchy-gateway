"""Source-preserving applications for the East-West Forge bridge."""

from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.inner_dto.forge_bridge_inner_dto import (
    ForgeConvergeSwarmResponseDto,
    ForgeSettleSwarmResponseDto,
    SyncAutonomyOutboxResponseDto,
)
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.types.forge_bridge_types import (
    ForgeConvergeSwarmResponseDict,
    ForgeSettleSwarmResponseDict,
    SyncAutonomyOutboxResponseDict,
)
from app.orchestration.application.orchestration_command_utils import (
    ORCHESTRATION_SWARM_EXCHANGE_POLICY,
    execute_orchestration_operation,
)
from app.orchestration.application.orchestration_wire_parsers import (
    UINT64_MAX,
    parse_wire_bool,
    parse_wire_int,
    parse_wire_str_tuple,
    require_wire_object,
    wire_optional,
)
from app.orchestration.application.swarm.swarm_state_parsers import parse_swarm_run
from app.orchestration.application.swarm.swarm_verification_parsers import (
    parse_swarm_convergence_gate,
)
from app.orchestration.schema.forge_bridge.orchestration_forge_bridge_schema import (
    ForgeConvergeSwarmRequest,
    ForgeConvergeSwarmResponse,
    ForgeSettleSwarmRequest,
    ForgeSettleSwarmResponse,
    SyncAutonomyOutboxRequest,
)
from app.orchestration.schema.types.orchestration_types import UInt64
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.ingredient_element.orchestration.forge_bridge_enums import (
    ForgeBridgeFieldEnum,
)
from app.shared.types.wire_scalar_types import parse_wire_uuid


def _parse_uint64_field(value: JsonValue, field: ForgeBridgeFieldEnum) -> UInt64:
    """Parse one required unsigned 64-bit integer from a bridge response.

    Args:
        value: Raw JSON field value.
        field: Bridge wire field identifier used in error context.
    Return:
        Exact validated UInt64 integer.
    """
    result = parse_wire_int(value=value, minimum=0, maximum=UINT64_MAX, label=field.value)
    return result


def _parse_outbox_sync_dto(payload: JsonValue) -> SyncAutonomyOutboxResponseDto:
    """Parse the exact bounded autonomy outbox summary DTO.

    Args:
        payload: Decoded Orchestration response JSON value.
    Return:
        Closed inner DTO representing the outbox sync summary.
    """
    source = require_wire_object(
        payload=payload,
        required_keys=(
            ForgeBridgeFieldEnum.APPLIED_COUNT.value,
            ForgeBridgeFieldEnum.DAG_SETTLED_COUNT.value,
            ForgeBridgeFieldEnum.SWARM_SETTLED_COUNT.value,
            ForgeBridgeFieldEnum.LAST_SEQUENCE.value,
        ),
        optional_keys=(),
    )
    result = SyncAutonomyOutboxResponseDto(
        applied_count=_parse_uint64_field(
            value=source[ForgeBridgeFieldEnum.APPLIED_COUNT.value],
            field=ForgeBridgeFieldEnum.APPLIED_COUNT,
        ),
        dag_settled_count=_parse_uint64_field(
            value=source[ForgeBridgeFieldEnum.DAG_SETTLED_COUNT.value],
            field=ForgeBridgeFieldEnum.DAG_SETTLED_COUNT,
        ),
        swarm_settled_count=_parse_uint64_field(
            value=source[ForgeBridgeFieldEnum.SWARM_SETTLED_COUNT.value],
            field=ForgeBridgeFieldEnum.SWARM_SETTLED_COUNT,
        ),
        last_sequence=_parse_uint64_field(
            value=source[ForgeBridgeFieldEnum.LAST_SEQUENCE.value],
            field=ForgeBridgeFieldEnum.LAST_SEQUENCE,
        ),
    )
    return result


def _parse_outbox_sync_response(payload: JsonValue) -> SyncAutonomyOutboxResponseDict:
    """Parse the exact bounded autonomy outbox summary.

    Args:
        payload: Decoded Orchestration response JSON value.
    Return:
        Closed typed outbox sync response.
    """
    result = _parse_outbox_sync_dto(payload=payload).to_dict()
    return result


def _parse_converge_response(
    payload: JsonValue,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
) -> ForgeConvergeSwarmResponseDict:
    """Parse a convergence result and fence its source path identities.

    Args:
        payload: Decoded Orchestration response JSON value.
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm selected by the Gateway path.
    Return:
        Closed typed convergence response with absent gate normalized to null.
    """
    source = require_wire_object(
        payload=payload,
        required_keys=(ForgeBridgeFieldEnum.RUN.value, ForgeBridgeFieldEnum.CHANGED_FILES.value),
        optional_keys=(ForgeBridgeFieldEnum.GATE.value,),
    )
    run = parse_swarm_run(value=source[ForgeBridgeFieldEnum.RUN.value])
    if run.workspace_id != expected_workspace_id or run.swarm_run_id != expected_swarm_run_id:
        raise ValueError("Forge convergence response escaped the requested Workspace or Swarm")
    gate = wire_optional(
        value=source.get(ForgeBridgeFieldEnum.GATE.value),
        parser=parse_swarm_convergence_gate,
    )
    if gate is not None and gate.swarm_run_id != expected_swarm_run_id:
        raise ValueError("Forge convergence gate escaped the requested Swarm")
    response = ForgeConvergeSwarmResponseDto(
        run=run,
        changed_files=parse_wire_str_tuple(
            value=source[ForgeBridgeFieldEnum.CHANGED_FILES.value],
            label=ForgeBridgeFieldEnum.CHANGED_FILES.value,
        ),
        gate=gate,
    )
    result = response.to_dict()
    ForgeConvergeSwarmResponse.model_validate(result)
    return result


def _parse_settle_response(
    payload: JsonValue,
    expected_workspace_id: UUID,
    expected_swarm_run_id: UUID,
    expected_settlement_id: UUID,
    expected_after_sequence: UInt64,
) -> ForgeSettleSwarmResponseDict:
    """Parse a settlement receipt and fence Source identities and sequence bounds.

    Args:
        payload: Decoded Orchestration response JSON value.
        expected_workspace_id: Workspace selected by the Gateway path.
        expected_swarm_run_id: Swarm selected by the Gateway path.
        expected_settlement_id: Caller-supplied settlement request UUID.
    Return:
        Closed typed settlement response with absent options normalized to null.
    """
    source = require_wire_object(
        payload=payload,
        required_keys=(
            ForgeBridgeFieldEnum.RUN.value,
            ForgeBridgeFieldEnum.GATE.value,
            ForgeBridgeFieldEnum.SETTLEMENT_ID.value,
            ForgeBridgeFieldEnum.SETTLED_FILE_COUNT.value,
            ForgeBridgeFieldEnum.SETTLED_AT_MS.value,
            ForgeBridgeFieldEnum.PURGED_EPHEMERAL.value,
        ),
        optional_keys=(
            ForgeBridgeFieldEnum.OUTBOX_SEQUENCE.value,
            ForgeBridgeFieldEnum.OUTBOX_SYNC.value,
        ),
    )
    run = parse_swarm_run(value=source[ForgeBridgeFieldEnum.RUN.value])
    if run.workspace_id != expected_workspace_id or run.swarm_run_id != expected_swarm_run_id:
        raise ValueError("Forge settlement response escaped the requested Workspace or Swarm")
    settlement_id = parse_wire_uuid(value=source[ForgeBridgeFieldEnum.SETTLEMENT_ID.value])
    if settlement_id != expected_settlement_id:
        raise ValueError("Forge settlement response changed the request identity")
    gate = parse_swarm_convergence_gate(value=source[ForgeBridgeFieldEnum.GATE.value])
    if gate.swarm_run_id != expected_swarm_run_id:
        raise ValueError("Forge settlement gate escaped the requested Swarm")
    outbox_sequence = wire_optional(
        value=source.get(ForgeBridgeFieldEnum.OUTBOX_SEQUENCE.value),
        parser=partial(
            parse_wire_int,
            minimum=0,
            maximum=UINT64_MAX,
            label=ForgeBridgeFieldEnum.OUTBOX_SEQUENCE.value,
        ),
    )
    outbox_sync = wire_optional(
        value=source.get(ForgeBridgeFieldEnum.OUTBOX_SYNC.value),
        parser=_parse_outbox_sync_dto,
    )
    if outbox_sync is not None and outbox_sync.last_sequence < expected_after_sequence:
        raise ValueError("Settlement outbox cursor regressed behind its requested sequence")
    response = ForgeSettleSwarmResponseDto(
        run=run,
        gate=gate,
        settlement_id=settlement_id,
        settled_file_count=_parse_uint64_field(
            value=source[ForgeBridgeFieldEnum.SETTLED_FILE_COUNT.value],
            field=ForgeBridgeFieldEnum.SETTLED_FILE_COUNT,
        ),
        settled_at_ms=parse_wire_int(
            value=source[ForgeBridgeFieldEnum.SETTLED_AT_MS.value],
            label=ForgeBridgeFieldEnum.SETTLED_AT_MS.value,
        ),
        outbox_sequence=outbox_sequence,
        outbox_sync=outbox_sync,
        purged_ephemeral=parse_wire_bool(
            value=source[ForgeBridgeFieldEnum.PURGED_EPHEMERAL.value],
            label=ForgeBridgeFieldEnum.PURGED_EPHEMERAL.value,
        ),
    )
    result = response.to_dict()
    ForgeSettleSwarmResponse.model_validate(result)
    return result


class ForgeBridgeApplication:
    """Forward Source-validated east-west bridge operations."""

    def __init__(self, calling: OrchestrationCalling) -> None:
        """Bind the request-scoped Orchestration caller.

        Args:
            calling: Caller carrying this request's Orchestration credential.
        Return:
            None.
        """
        self._calling = calling

    async def forge_converge_swarm(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: ForgeConvergeSwarmRequest,
    ) -> OrchestrationOutcomeDto[ForgeConvergeSwarmResponseDict]:
        """Converge one Swarm run through Orchestration's Forge bridge.

        Args:
            workspace_id: Workspace identity selected by the Gateway path.
            swarm_run_id: Swarm identity selected by the Gateway path.
            request: Strict caller convergence command.
        Return:
            Source HTTP status and typed convergence response or error.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/forge-converge",
            parse_result=partial(
                _parse_converge_response,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def forge_settle_swarm(
        self,
        workspace_id: UUID,
        swarm_run_id: UUID,
        request: ForgeSettleSwarmRequest,
    ) -> OrchestrationOutcomeDto[ForgeSettleSwarmResponseDict]:
        """Settle one Swarm run and preserve its Source outcome.

        Args:
            workspace_id: Workspace identity selected by the Gateway path.
            swarm_run_id: Swarm identity selected by the Gateway path.
            request: Strict caller settlement command.
        Return:
            Source HTTP status and typed settlement response or error.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=f"/v1/workspaces/{workspace_id}/swarms/{swarm_run_id}/forge-settle",
            parse_result=partial(
                _parse_settle_response,
                expected_workspace_id=workspace_id,
                expected_swarm_run_id=swarm_run_id,
                expected_settlement_id=request.request_id,
                expected_after_sequence=request.outbox_after_sequence or 0,
            ),
            body=command.to_dict(),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result

    async def sync_autonomy_outbox(
        self,
        workspace_id: UUID,
        request: SyncAutonomyOutboxRequest,
    ) -> OrchestrationOutcomeDto[SyncAutonomyOutboxResponseDict]:
        """Reconcile one bounded Forge autonomy outbox page.

        Args:
            workspace_id: Workspace identity selected by the Gateway path.
            request: Strict caller synchronization cursor and page size.
        Return:
            Source HTTP status and typed outbox summary or error.
        """
        command = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._calling,
            method="POST",
            path=f"/internal/v1/workspaces/{workspace_id}/autonomy-outbox/sync",
            parse_result=partial(_parse_outbox_sync_response),
            body=command.to_dict(),
            validate_result_status=partial(
                _validate_outbox_cursor,
                after_sequence=request.after_sequence,
            ),
            workspace_id=workspace_id,
            exchange_policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
        )
        return result


def _validate_outbox_cursor(
    status_code: int,
    result: SyncAutonomyOutboxResponseDict,
    *,
    after_sequence: UInt64,
) -> None:
    """Reject a Source cursor that regresses behind the caller's request."""
    if (
        status_code == status.HTTP_200_OK
        and result[ForgeBridgeFieldEnum.LAST_SEQUENCE.value] < after_sequence
    ):
        raise ValueError("Outbox synchronization sequence regressed")
