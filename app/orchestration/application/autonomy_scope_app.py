"""Source-preserving application methods for Workspace scope operations."""

from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.autonomy_wire_utils import require_wire_object
from app.orchestration.application.inner_dto.autonomy_scope_inner_dto import (
    RegisteredWorkspaceScopeDto,
    WorkspaceQueryScopeDto,
    WorkspaceScopeQueryDto,
    WorkspaceScopeRegisterCommandDto,
)
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.types.autonomy.autonomy_scope_types import (
    RegisteredWorkspaceScopeDict,
    WorkspaceScopeQueryResponseDict,
)
from app.orchestration.application.orchestration_command_utils import (
    execute_orchestration_operation,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_scope_schema import (
    RegisteredWorkspaceScopeResponse,
    WorkspaceQueryScopeSchema,
    WorkspaceScopeRegisterRequest,
)
from app.orchestration.schema.types.autonomy_types import UnsignedRevision
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.types.wire_scalar_types import parse_wire_uuid

_MAX_ACTIVE_SCOPE_COUNT = 64
_MAX_LOCATOR_BYTES = 4_096


def _scope_dto_from_schema(schema: WorkspaceQueryScopeSchema) -> WorkspaceQueryScopeDto:
    result = WorkspaceQueryScopeDto(
        workspace_id=schema.workspace_id,
        location_id=schema.location_id,
        location_revision=schema.location_revision,
        workspace_revision=schema.workspace_revision,
        locator=schema.locator,
    )
    return result


def _registered_scope_dto_from_schema(
    schema: RegisteredWorkspaceScopeResponse,
) -> RegisteredWorkspaceScopeDto:
    result = RegisteredWorkspaceScopeDto(
        workspace_id=schema.workspace_id,
        location_id=schema.location_id,
        location_revision=schema.location_revision,
        workspace_revision=schema.workspace_revision,
        locator=schema.locator,
        active=schema.active,
        revision=schema.revision,
        generation=schema.generation,
        updated_at_ms=schema.updated_at_ms,
        replayed=schema.replayed,
    )
    return result


def _parse_scope_list(payload: JsonValue) -> list[RegisteredWorkspaceScopeDict]:
    if not isinstance(payload, list):
        raise ValueError("Workspace scopes response must be a root JSON array")
    if len(payload) > _MAX_ACTIVE_SCOPE_COUNT:
        raise ValueError("Workspace scopes response exceeds the source count bound")
    result: list[RegisteredWorkspaceScopeDict] = []
    seen_workspace_ids: set[UUID] = set()
    for item in payload:
        schema = RegisteredWorkspaceScopeResponse.model_validate(item)
        scope = _registered_scope_dto_from_schema(schema=schema)
        if not _active_scope_record_matches(scope=scope, expected_workspace_id=schema.workspace_id):
            raise ValueError("Workspace scope response violates its active-record contract")
        if scope.workspace_id in seen_workspace_ids:
            raise ValueError("Workspace scopes response contains a duplicate Workspace")
        seen_workspace_ids.add(scope.workspace_id)
        result.append(scope.to_dict())
    return result


def _parse_scope_register_response(
    payload: JsonValue,
    expected_scope: WorkspaceQueryScopeDto,
    expected_revision: UnsignedRevision,
) -> RegisteredWorkspaceScopeDict:
    schema = RegisteredWorkspaceScopeResponse.model_validate(payload)
    if (
        schema.workspace_id != expected_scope.workspace_id
        or schema.location_id != expected_scope.location_id
        or schema.location_revision != expected_scope.location_revision
        or schema.workspace_revision != expected_scope.workspace_revision
        or schema.locator != expected_scope.locator
    ):
        raise ValueError("Registered scope response does not match the requested scope")
    scope = _registered_scope_dto_from_schema(schema=schema)
    if (
        not _active_scope_record_matches(
            scope=scope, expected_workspace_id=expected_scope.workspace_id
        )
        or scope.revision <= expected_revision
    ):
        raise ValueError("Registered scope response violates its mutation readback contract")
    result = scope.to_dict()
    return result


def _active_scope_record_matches(
    scope: RegisteredWorkspaceScopeDto,
    expected_workspace_id: UUID,
) -> bool:
    locator_bytes = len(scope.locator.encode("utf-8"))
    result = (
        scope.workspace_id == expected_workspace_id
        and scope.workspace_id.int != 0
        and scope.location_id.int != 0
        and scope.location_revision > 0
        and scope.workspace_revision > 0
        and locator_bytes > 0
        and locator_bytes <= _MAX_LOCATOR_BYTES
        and scope.active
        and scope.revision > 0
        and scope.generation > 0
        and scope.updated_at_ms >= 0
    )
    return result


def _parse_scope_query_response(
    payload: JsonValue,
    expected_workspace_id: UUID,
) -> WorkspaceScopeQueryResponseDict:
    source = require_wire_object(
        payload=payload, required_keys=("workspaceId",), optional_keys=("scope",)
    )
    workspace_id = parse_wire_uuid(value=source["workspaceId"])
    if workspace_id != expected_workspace_id:
        raise ValueError("Workspace scope response does not match the requested path")
    scope_value = source.get("scope")
    scope_schema = (
        RegisteredWorkspaceScopeResponse.model_validate(scope_value)
        if scope_value is not None
        else None
    )
    scope = (
        _registered_scope_dto_from_schema(schema=scope_schema) if scope_schema is not None else None
    )
    if scope is not None and not _active_scope_record_matches(
        scope=scope, expected_workspace_id=expected_workspace_id
    ):
        raise ValueError("Registered scope response violates its active-record contract")
    result = WorkspaceScopeQueryDto(workspace_id=workspace_id, scope=scope).to_dict()
    return result


class AutonomyScopeApplication:
    """Execute the three plan-owned Workspace scope operations."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying this request's upstream authority.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def list_scopes(self) -> OrchestrationOutcomeDto[list[RegisteredWorkspaceScopeDict]]:
        """Read active Workspace scopes as a source root array.

        Args:
            None.
        Return:
            Source status and validated active scope result array.
        """
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path="/internal/v1/workspaces/scopes",
            parse_result=_parse_scope_list,
            result_statuses=(status.HTTP_200_OK,),
        )
        return result

    async def register_scope(
        self,
        request: WorkspaceScopeRegisterRequest,
    ) -> OrchestrationOutcomeDto[RegisteredWorkspaceScopeDict]:
        """Register or advance one Workspace scope.

        Args:
            request: Strictly validated scope registration request.
        Return:
            Source status and scope response matching the submitted scope.
        """
        scope = _scope_dto_from_schema(schema=request.scope)
        command = WorkspaceScopeRegisterCommandDto(
            request_id=request.request_id,
            expected_revision=request.expected_revision,
            scope=scope,
        )
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path="/internal/v1/workspaces/scopes",
            parse_result=partial(
                _parse_scope_register_response,
                expected_scope=scope,
                expected_revision=request.expected_revision,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=scope.workspace_id,
        )
        return result

    async def fetch_workspace_scope(
        self,
        workspace_id: UUID,
    ) -> OrchestrationOutcomeDto[WorkspaceScopeQueryResponseDict]:
        """Read the active scope for one Workspace path identity.

        Args:
            workspace_id: Workspace identity selected by the public route.
        Return:
            Source status and scope response with missing scope normalized to null.
        """
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path=f"/internal/v1/workspaces/{workspace_id}/scopes",
            parse_result=partial(_parse_scope_query_response, expected_workspace_id=workspace_id),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
        )
        return result
