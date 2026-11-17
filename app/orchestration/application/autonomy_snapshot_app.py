"""Source-preserving applications for execution snapshot operations."""

from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue, TypeAdapter

from app.orchestration.application.autonomy_wire_utils import require_wire_object
from app.orchestration.application.inner_dto.autonomy_snapshot_inner_dto import (
    ExecutionSnapshotOutcomeDto,
    ExecutionSnapshotOutcomeResponseDict,
    ExecutionSnapshotQueryDto,
    ExecutionSnapshotQueryResponseDict,
    LaunchLedgerRecordDto,
    LaunchLedgerStateDto,
    PrepareExecutionSnapshotCommandDto,
    ProcessOwnershipDto,
)
from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPermissionsDto,
    ExecutionTimeoutsDto,
)
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.orchestration_command_utils import (
    execute_orchestration_operation,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_snapshot_schema import (
    ExecutionSnapshotOutcomeResponse,
    LaunchLedgerRecordSchema,
    PrepareExecutionSnapshotRequest,
)
from app.orchestration.schema.types.autonomy_types import DagRevision, WorkAttempt
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.filter_module.autonomy_filter import ExecutionSnapshotFilter
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    ExecutionSnapshotQueryFieldEnum,
)
from app.shared.types.wire_scalar_types import parse_wire_uuid

_DAG_REVISION_ADAPTER: TypeAdapter[DagRevision] = TypeAdapter(DagRevision)
_WORK_ATTEMPT_ADAPTER: TypeAdapter[WorkAttempt] = TypeAdapter(WorkAttempt)
_SNAPSHOT_QUERY_REQUIRED_FIELDS = tuple(
    field.value
    for field in ExecutionSnapshotQueryFieldEnum
    if field is not ExecutionSnapshotQueryFieldEnum.RECORD
)


def _record_dto_from_schema(schema: LaunchLedgerRecordSchema) -> LaunchLedgerRecordDto:
    ownership_schema = schema.state.ownership
    ownership = (
        ProcessOwnershipDto(
            pid=ownership_schema.pid,
            pgid=ownership_schema.pgid,
            start_time=ownership_schema.start_time,
            boot_id=ownership_schema.boot_id,
        )
        if ownership_schema is not None
        else None
    )
    state = LaunchLedgerStateDto(
        status=schema.state.status,
        ownership=ownership,
        exit_code=schema.state.exit_code,
        unknown_reason=schema.state.unknown_reason,
        observed_at_ms=schema.state.observed_at_ms,
    )
    result = LaunchLedgerRecordDto(
        snapshot_id=schema.snapshot_id,
        workspace_id=schema.workspace_id,
        goal_id=schema.goal_id,
        dag_revision=schema.dag_revision,
        node_id=schema.node_id,
        assignment_id=schema.assignment_id,
        attempt=schema.attempt,
        state=state,
        revision=schema.revision,
        updated_at_ms=schema.updated_at_ms,
    )
    return result


def _parse_snapshot_outcome(
    payload: JsonValue,
    expected_workspace_id: UUID,
    expected_snapshot_id: UUID,
    goal_id: UUID,
    dag_revision: DagRevision,
    node_id: UUID,
    assignment_id: UUID,
    attempt: WorkAttempt,
) -> ExecutionSnapshotOutcomeResponseDict:
    schema = ExecutionSnapshotOutcomeResponse.model_validate(payload)
    record_schema = schema.record
    if record_schema is not None and record_schema.snapshot_id != expected_snapshot_id:
        raise ValueError("Snapshot outcome record escaped the requested snapshot identity")
    expected_filter = ExecutionSnapshotFilter(
        goalId=goal_id,
        dagRevision=dag_revision,
        nodeId=node_id,
        assignmentId=assignment_id,
        attempt=attempt,
    )
    record = _record_dto_for_attempt(
        record_schema=record_schema, workspace_id=expected_workspace_id, filters=expected_filter
    )
    result = ExecutionSnapshotOutcomeDto(
        committed=schema.committed,
        rejection_code=schema.rejection_code,
        detail=schema.detail,
        record=record,
    ).to_dict()
    return result


def _validate_snapshot_response_status(
    status_code: int,
    response: ExecutionSnapshotOutcomeResponseDict,
) -> None:
    record = response["record"]
    if status_code == status.HTTP_200_OK:
        if not response["committed"] or response["rejectionCode"] is not None or record is None:
            raise ValueError("Snapshot HTTP 200 response is not a committed record")
    elif status_code == status.HTTP_409_CONFLICT:
        if response["committed"] or not response["rejectionCode"] or record is not None:
            raise ValueError("Snapshot HTTP 409 response is not a typed rejection")
    else:
        raise ValueError("Unexpected execution snapshot result status")


def _record_dto_for_attempt(
    record_schema: LaunchLedgerRecordSchema | None,
    workspace_id: UUID,
    filters: ExecutionSnapshotFilter,
) -> LaunchLedgerRecordDto | None:
    """Convert an optional ledger record after checking its requested attempt."""
    if record_schema is None:
        return None
    observed_filter = ExecutionSnapshotFilter(
        goalId=record_schema.goal_id,
        dagRevision=record_schema.dag_revision,
        nodeId=record_schema.node_id,
        assignmentId=record_schema.assignment_id,
        attempt=record_schema.attempt,
    )
    if record_schema.workspace_id != workspace_id or observed_filter != filters:
        raise ValueError("Snapshot record escaped requested Workspace attempt")
    result = _record_dto_from_schema(schema=record_schema)
    return result


def _parse_snapshot_query(
    payload: JsonValue,
    workspace_id: UUID,
    filters: ExecutionSnapshotFilter,
) -> ExecutionSnapshotQueryResponseDict:
    source = require_wire_object(
        payload=payload,
        required_keys=_SNAPSHOT_QUERY_REQUIRED_FIELDS,
        optional_keys=(ExecutionSnapshotQueryFieldEnum.RECORD.value,),
    )
    observed_workspace_id = parse_wire_uuid(
        value=source[ExecutionSnapshotQueryFieldEnum.WORKSPACE_ID]
    )
    observed_goal_id = parse_wire_uuid(value=source[ExecutionSnapshotQueryFieldEnum.GOAL_ID])
    observed_dag_revision = _DAG_REVISION_ADAPTER.validate_python(
        source[ExecutionSnapshotQueryFieldEnum.DAG_REVISION],
        strict=True,
    )
    observed_node_id = parse_wire_uuid(value=source[ExecutionSnapshotQueryFieldEnum.NODE_ID])
    observed_assignment_id = parse_wire_uuid(
        value=source[ExecutionSnapshotQueryFieldEnum.ASSIGNMENT_ID]
    )
    observed_attempt = _WORK_ATTEMPT_ADAPTER.validate_python(
        source[ExecutionSnapshotQueryFieldEnum.ATTEMPT],
        strict=True,
    )
    observed_filter = ExecutionSnapshotFilter(
        goalId=observed_goal_id,
        dagRevision=observed_dag_revision,
        nodeId=observed_node_id,
        assignmentId=observed_assignment_id,
        attempt=observed_attempt,
    )
    if observed_workspace_id != workspace_id or observed_filter != filters:
        raise ValueError("Snapshot query response did not match the requested attempt key")
    record_payload = source.get(ExecutionSnapshotQueryFieldEnum.RECORD)
    record_schema = (
        LaunchLedgerRecordSchema.model_validate(record_payload)
        if record_payload is not None
        else None
    )
    record = _record_dto_for_attempt(
        record_schema=record_schema, workspace_id=workspace_id, filters=filters
    )
    result = ExecutionSnapshotQueryDto(
        workspace_id=observed_workspace_id,
        goal_id=observed_goal_id,
        dag_revision=observed_dag_revision,
        node_id=observed_node_id,
        assignment_id=observed_assignment_id,
        attempt=observed_attempt,
        record=record,
    ).to_dict()
    return result


def _source_snapshot_command(
    request: PrepareExecutionSnapshotRequest,
) -> PrepareExecutionSnapshotCommandDto:
    mcp_grant_schema = request.mcp_grant
    mcp_grant = mcp_grant_schema.to_inner_dto() if mcp_grant_schema is not None else None
    result = PrepareExecutionSnapshotCommandDto(
        request_id=request.request_id,
        snapshot_id=request.snapshot_id,
        goal_id=request.goal_id,
        dag_revision=request.dag_revision,
        node_id=request.node_id,
        assignment_id=request.assignment_id,
        attempt=request.attempt,
        activity_id=request.activity_id,
        profile_id=request.profile_id,
        profile_revision=request.profile_revision,
        resolved_engine=request.resolved_engine,
        resolved_model=request.resolved_model,
        resolved_reasoning=request.resolved_reasoning,
        role_prompt_digest_hex=request.role_prompt_digest_hex,
        worktree_path=request.worktree_path,
        lease_id=request.lease_id,
        lease_revision=request.lease_revision,
        lease_expires_at_ms=request.lease_expires_at_ms,
        mcp_grant=mcp_grant,
        permissions=ExecutionPermissionsDto(
            allow_workspace_write=request.permissions.allow_workspace_write,
            allow_local_shell=request.permissions.allow_local_shell,
            allow_network=request.permissions.allow_network,
        ),
        timeouts=ExecutionTimeoutsDto(
            startup_timeout_ms=request.timeouts.startup_timeout_ms,
            execution_timeout_ms=request.timeouts.execution_timeout_ms,
            termination_grace_ms=request.timeouts.termination_grace_ms,
        ),
    )
    return result


class AutonomySnapshotApplication:
    """Execute prepare and exact-key readback for execution snapshots."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying this request's upstream authority.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def prepare_execution_snapshot(
        self,
        workspace_id: UUID,
        request: PrepareExecutionSnapshotRequest,
    ) -> OrchestrationOutcomeDto[ExecutionSnapshotOutcomeResponseDict]:
        """Validate and commit one execution snapshot.

        Args:
            workspace_id: Workspace identity selected by the public route.
            request: Strictly validated execution snapshot command.
        Return:
            Source status and typed committed or rejected outcome.
        """
        command = _source_snapshot_command(request=request)
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/internal/v1/workspaces/{workspace_id}/execution-snapshots",
            parse_result=partial(
                _parse_snapshot_outcome,
                expected_workspace_id=workspace_id,
                expected_snapshot_id=request.snapshot_id,
                goal_id=request.goal_id,
                dag_revision=request.dag_revision,
                node_id=request.node_id,
                assignment_id=request.assignment_id,
                attempt=request.attempt,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_409_CONFLICT),
            validate_result_status=_validate_snapshot_response_status,
            workspace_id=workspace_id,
        )
        return result

    async def fetch_execution_snapshot(
        self,
        workspace_id: UUID,
        filters: ExecutionSnapshotFilter,
    ) -> OrchestrationOutcomeDto[ExecutionSnapshotQueryResponseDict]:
        """Read one execution snapshot by its complete attempt key.

        Args:
            workspace_id: Workspace identity selected by the public route.
            filters: Required source query key for one execution attempt.
        Return:
            Source status and exact-key response with absent records normalized.
        """
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path=f"/internal/v1/workspaces/{workspace_id}/execution-snapshots",
            parse_result=partial(_parse_snapshot_query, workspace_id=workspace_id, filters=filters),
            params=filters.to_query_params(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
        )
        return result
