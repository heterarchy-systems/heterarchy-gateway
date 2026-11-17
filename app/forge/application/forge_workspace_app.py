"""Typed command applications for Forge Location, Workspace, Activity, and DAG routes."""

from collections.abc import Callable
from functools import partial
from uuid import UUID

from pydantic import JsonValue

from app.forge.application.forge_command_utils import (
    execute_forge_command,
    session_actor_dto,
    workspace_scope_dto,
)
from app.forge.application.forge_workspace_dto import (
    ForgeActivityListCommandDto,
    ForgeActivityListPayload,
    ForgeActivityListResultDict,
    ForgeActivityListResultDto,
    ForgeDagCurrentFoundResultDto,
    ForgeDagCurrentMissingResultDto,
    ForgeDagCurrentResultDict,
    ForgeDagReadCurrentCommandDto,
    ForgeDagSettleCommandDto,
    ForgeDagSettleResultDict,
    ForgeDagSettleResultDto,
    ForgeLocationListCommandDto,
    ForgeLocationListResultDict,
    ForgeLocationListResultDto,
    ForgeWorkspaceListCommandDto,
    ForgeWorkspaceListPayload,
    ForgeWorkspaceListResultDict,
    ForgeWorkspaceListResultDto,
)
from app.forge.application.inner_dto.forge_envelope_dto import ForgeCommandOutcomeDto
from app.forge.schema.activity.forge_activity_schema import (
    ForgeActivityListRequest,
    ForgeActivityListResult,
)
from app.forge.schema.dag.forge_dag_schema import (
    ForgeDagCurrentFoundResult,
    ForgeDagCurrentResult,
    ForgeDagReadCurrentRequest,
    ForgeDagSettlePayload,
    ForgeDagSettleRequest,
    ForgeDagSettleResult,
)
from app.forge.schema.envelope.forge_envelope_schema import ForgeCommandRequest
from app.forge.schema.location.forge_location_schema import (
    ForgeLocationListRequest,
    ForgeLocationListResult,
)
from app.forge.schema.workspace.forge_workspace_schema import (
    ForgeWorkspaceListRequest,
    ForgeWorkspaceListResult,
)
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum


class ForgeWorkspaceApplication:
    """Map typed Forge Workspace commands to typed Source envelopes."""

    def __init__(self, forge_calling: ForgeCalling) -> None:
        """Initialize the feature command application.

        Args:
            forge_calling: Request-scoped caller for the Forge command endpoint.
        Return:
            None.
        """
        self._forge_calling = forge_calling

    async def list_locations(
        self,
        request: ForgeLocationListRequest,
    ) -> ForgeCommandOutcomeDto[ForgeLocationListResultDict]:
        """List registered Forge Locations.

        Args:
            request: Validated location.list command envelope.
        Return:
            Typed Source response and preserved HTTP status.
        """
        command = ForgeLocationListCommandDto()
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.LOCATION_LIST,
            payload=command.to_dict(),
            parse_result=_parse_location_list_result,
        )
        return result

    async def list_workspaces(
        self,
        request: ForgeWorkspaceListRequest,
    ) -> ForgeCommandOutcomeDto[ForgeWorkspaceListResultDict]:
        """List Workspaces discovered beneath one Location revision.

        Args:
            request: Validated workspace.list command envelope.
        Return:
            Typed Source response and preserved HTTP status.
        """
        command = ForgeWorkspaceListCommandDto.from_payload(payload=request.payload)
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.WORKSPACE_LIST,
            payload=command.to_dict(),
            parse_result=partial(_parse_workspace_list_result, request.payload),
        )
        return result

    async def list_activities(
        self,
        request: ForgeActivityListRequest,
    ) -> ForgeCommandOutcomeDto[ForgeActivityListResultDict]:
        """List durable Activity projections for one canonical Workspace locator.

        Args:
            request: Validated activity.list command envelope.
        Return:
            Typed Source response and preserved HTTP status.
        """
        command = ForgeActivityListCommandDto.from_payload(payload=request.payload)
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.ACTIVITY_LIST,
            payload=command.to_dict(),
            parse_result=partial(_parse_activity_list_result, request.payload),
        )
        return result

    async def read_current_dag(
        self,
        request: ForgeDagReadCurrentRequest,
    ) -> ForgeCommandOutcomeDto[ForgeDagCurrentResultDict]:
        """Read the current stored revision for one Goal.

        Args:
            request: Validated dag.read_current command envelope.
        Return:
            Typed found-or-missing Source response and preserved status.
        """
        command = ForgeDagReadCurrentCommandDto.from_payload(
            payload=request.payload,
            scope=workspace_scope_dto(scope=request.payload.scope),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.DAG_READ_CURRENT,
            payload=command.to_dict(),
            parse_result=partial(_parse_dag_current_result, request.payload.goal_id),
        )
        return result

    async def settle_dag(
        self,
        request: ForgeDagSettleRequest,
    ) -> ForgeCommandOutcomeDto[ForgeDagSettleResultDict]:
        """Settle one exact Goal and DAG revision under the Source contract.

        Args:
            request: Validated dag.settle command envelope.
        Return:
            Typed Source settlement receipt and preserved HTTP status.
        """
        command = ForgeDagSettleCommandDto.from_payload(
            payload=request.payload,
            scope=workspace_scope_dto(scope=request.payload.scope),
            actor=session_actor_dto(actor=request.payload.actor),
        )
        result = await self._execute(
            request=request,
            operation=ForgeCommandOpEnum.DAG_SETTLE,
            payload=command.to_dict(),
            parse_result=partial(_parse_dag_settle_result, request.payload),
        )
        return result

    async def _execute[
        PayloadSchema: StrictSchemaModel,
        PayloadDictT,
        ResultDictT,
    ](
        self,
        request: ForgeCommandRequest[PayloadSchema],
        operation: ForgeCommandOpEnum,
        payload: PayloadDictT,
        parse_result: Callable[[JsonValue], ResultDictT],
    ) -> ForgeCommandOutcomeDto[ResultDictT]:
        """Execute one command and retain its validated Source response.

        Args:
            request: Validated versioned command envelope.
            operation: Operation fixed by the route and Source parser.
            payload: Closed TypedDict operation payload.
            parse_result: Source result parser returning an immutable DTO TypedDict.
        Return:
            Immutable typed Source response with its original HTTP status.
        """
        if ForgeCommandOpEnum(request.op) is not operation:
            raise ValueError("Forge command operation does not match its route")
        envelope = request.to_inner_dto(payload=payload)
        result = await execute_forge_command(
            calling=self._forge_calling, envelope=envelope, parse_result=parse_result
        )
        return result


def _parse_location_list_result(payload: JsonValue) -> ForgeLocationListResultDict:
    """Validate and map location.list's nested Source result object.

    Args:
        payload: Source result JSON value.
    Return:
        Closed Location result TypedDict.
    """
    response = ForgeLocationListResult.model_validate(payload)
    result = ForgeLocationListResultDto.from_schema(result_schema=response).to_dict()
    return result


def _parse_workspace_list_result(
    request: ForgeWorkspaceListPayload,
    payload: JsonValue,
) -> ForgeWorkspaceListResultDict:
    """Validate and map workspace.list's nested Source result object.

    Args:
        request: Validated Workspace list request identity.
        payload: Source result JSON value.
    Return:
        Closed Workspace result TypedDict.
    """
    response = ForgeWorkspaceListResult.model_validate(payload)
    expected_locator_prefix = f"v1:{request.location_id}:{request.expected_revision}:"
    if not all(entry.locator.startswith(expected_locator_prefix) for entry in response.entries):
        raise ValueError("Forge Workspace locator escaped the requested Location revision")
    result = ForgeWorkspaceListResultDto.from_schema(result_schema=response).to_dict()
    return result


def _parse_activity_list_result(
    request: ForgeActivityListPayload,
    payload: JsonValue,
) -> ForgeActivityListResultDict:
    """Validate and map activity.list's nested Source result object.

    Args:
        request: Validated Activity list scope and bound.
        payload: Source result JSON value.
    Return:
        Closed Activity result TypedDict.
    """
    response = ForgeActivityListResult.model_validate(payload)
    if (
        response.scope.workspace_id != request.workspace_id
        or response.scope.workspace_revision != request.workspace_revision
        or response.scope.locator != request.locator
    ):
        raise ValueError("Forge Activity scope does not match the request")
    if not all(activity.workspace_id == request.workspace_id for activity in response.activities):
        raise ValueError("Forge Activity projection escaped the requested Workspace")
    result = ForgeActivityListResultDto.from_schema(result_schema=response).to_dict()
    return result


def _parse_dag_current_result(
    expected_goal_id: UUID,
    payload: JsonValue,
) -> ForgeDagCurrentResultDict:
    """Validate and map the tagged dag.read_current Source result.

    Args:
        expected_goal_id: Caller-supplied Goal identity.
        payload: Source result JSON value.
    Return:
        Closed found-or-missing DAG result TypedDict.
    """
    response = ForgeDagCurrentResult.model_validate(payload)
    if (
        isinstance(response.root, ForgeDagCurrentFoundResult)
        and response.root.goal_id != expected_goal_id
    ):
        raise ValueError("Forge returned a current DAG for a different Goal")
    if isinstance(response.root, ForgeDagCurrentFoundResult):
        inner_dto = ForgeDagCurrentFoundResultDto.from_schema(dag=response.root)
        result: ForgeDagCurrentResultDict = inner_dto.to_dict()
    else:
        inner_dto = ForgeDagCurrentMissingResultDto()
        result = inner_dto.to_dict()
    return result


def _parse_dag_settle_result(
    request: ForgeDagSettlePayload,
    payload: JsonValue,
) -> ForgeDagSettleResultDict:
    """Validate and map dag.settle's nested Source result object.

    Args:
        request: Validated settlement identity and revision fence.
        payload: Source result JSON value.
    Return:
        Closed DAG settlement result TypedDict.
    """
    response = ForgeDagSettleResult.model_validate(payload)
    if (
        response.settlement_id != request.settlement_id
        or response.goal_id != request.goal_id
        or response.dag_revision != request.expected_dag_revision
    ):
        raise ValueError("Forge settlement response does not match its request identity")
    result = ForgeDagSettleResultDto.from_schema(receipt=response).to_dict()
    return result
