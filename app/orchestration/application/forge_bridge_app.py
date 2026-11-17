"""Source-preserving applications for the East-West Forge bridge."""

from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue, TypeAdapter

from app.orchestration.application.autonomy_wire_utils import require_wire_object
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
from app.orchestration.application.swarm_state_parsers import (
    parse_swarm_convergence_gate,
    parse_swarm_run,
)
from app.orchestration.schema.forge_bridge.orchestration_forge_bridge_schema import (
    ForgeConvergeSwarmRequest,
    ForgeConvergeSwarmResponse,
    ForgeSettleSwarmRequest,
    ForgeSettleSwarmResponse,
    SyncAutonomyOutboxRequest,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt64
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.ingredient_element.orchestration.forge_bridge_enums import (
    ForgeBridgeFieldEnum,
)
from app.shared.types.base_types import JsonObject
from app.shared.types.wire_scalar_types import parse_wire_uuid

_UINT64_ADAPTER: TypeAdapter[UInt64] = TypeAdapter(UInt64)
_INT64_ADAPTER: TypeAdapter[Int64] = TypeAdapter(Int64)
_BOOL_ADAPTER: TypeAdapter[bool] = TypeAdapter(bool)


def _required_boolean(payload: JsonObject, field: ForgeBridgeFieldEnum) -> bool:
    """Extract one exact JSON boolean from a bridge response.

    Args:
        payload: Closed source response object already checked for its wire keys.
        field: Required field key owned by the bridge wire enum.
    Return:
        Exact source boolean.
    """
    result = _BOOL_ADAPTER.validate_python(payload[field.value], strict=True)
    return result


def _required_string_list(payload: JsonObject, field: ForgeBridgeFieldEnum) -> tuple[str, ...]:
    """Extract a source string array without coercing any member.

    Args:
        payload: Closed source response object already checked for its wire keys.
        field: Required field key owned by the bridge wire enum.
    Return:
        Immutable tuple preserving the source order.
    """
    value = payload[field.value]
    if not isinstance(value, list):
        raise ValueError(f"Bridge field {field.value} must be an array")
    values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"Bridge field {field.value} must contain strings")
        values.append(item)
    result = tuple(values)
    return result


def _parse_outbox_sync_response(payload: JsonValue) -> SyncAutonomyOutboxResponseDict:
    """Parse the exact bounded autonomy outbox summary.

    Args:
        payload: Decoded Orchestration response JSON value.
    Return:
        Closed typed outbox sync response.
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
        applied_count=_UINT64_ADAPTER.validate_python(
            source[ForgeBridgeFieldEnum.APPLIED_COUNT.value], strict=True
        ),
        dag_settled_count=_UINT64_ADAPTER.validate_python(
            source[ForgeBridgeFieldEnum.DAG_SETTLED_COUNT.value], strict=True
        ),
        swarm_settled_count=_UINT64_ADAPTER.validate_python(
            source[ForgeBridgeFieldEnum.SWARM_SETTLED_COUNT.value], strict=True
        ),
        last_sequence=_UINT64_ADAPTER.validate_python(
            source[ForgeBridgeFieldEnum.LAST_SEQUENCE.value], strict=True
        ),
    ).to_dict()
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
    gate_value = source.get(ForgeBridgeFieldEnum.GATE.value)
    gate = parse_swarm_convergence_gate(value=gate_value) if gate_value is not None else None
    if gate is not None and gate.swarm_run_id != expected_swarm_run_id:
        raise ValueError("Forge convergence gate escaped the requested Swarm")
    response = ForgeConvergeSwarmResponseDto(
        run=run,
        changed_files=_required_string_list(
            payload=source, field=ForgeBridgeFieldEnum.CHANGED_FILES
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
    sequence_value = source.get(ForgeBridgeFieldEnum.OUTBOX_SEQUENCE.value)
    outbox_sequence = (
        _UINT64_ADAPTER.validate_python(sequence_value, strict=True)
        if sequence_value is not None
        else None
    )
    outbox_value = source.get(ForgeBridgeFieldEnum.OUTBOX_SYNC.value)
    outbox_sync = None
    if outbox_value is not None:
        outbox_sync_dict = _parse_outbox_sync_response(payload=outbox_value)
        if outbox_sync_dict[ForgeBridgeFieldEnum.LAST_SEQUENCE.value] < expected_after_sequence:
            raise ValueError("Settlement outbox cursor regressed behind its requested sequence")
        outbox_sync = SyncAutonomyOutboxResponseDto(
            applied_count=outbox_sync_dict[ForgeBridgeFieldEnum.APPLIED_COUNT.value],
            dag_settled_count=outbox_sync_dict[ForgeBridgeFieldEnum.DAG_SETTLED_COUNT.value],
            swarm_settled_count=outbox_sync_dict[ForgeBridgeFieldEnum.SWARM_SETTLED_COUNT.value],
            last_sequence=outbox_sync_dict[ForgeBridgeFieldEnum.LAST_SEQUENCE.value],
        )
    response = ForgeSettleSwarmResponseDto(
        run=run,
        gate=gate,
        settlement_id=settlement_id,
        settled_file_count=_UINT64_ADAPTER.validate_python(
            source[ForgeBridgeFieldEnum.SETTLED_FILE_COUNT.value], strict=True
        ),
        settled_at_ms=_INT64_ADAPTER.validate_python(
            source[ForgeBridgeFieldEnum.SETTLED_AT_MS.value], strict=True
        ),
        outbox_sequence=outbox_sequence,
        outbox_sync=outbox_sync,
        purged_ephemeral=_required_boolean(
            payload=source, field=ForgeBridgeFieldEnum.PURGED_EPHEMERAL
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
