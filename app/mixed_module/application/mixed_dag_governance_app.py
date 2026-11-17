"""Request-owned Forge DAG and Orchestration governance composition."""

import asyncio
from uuid import UUID

from fastapi import status
from pydantic import TypeAdapter, ValidationError

from app.forge.application.forge_workspace_app import ForgeWorkspaceApplication
from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandSuccessEnvelopeDto,
)
from app.forge.application.inner_dto.types.forge_workspace_types import (
    ForgeDagCurrentResultDict,
)
from app.forge.schema.dag.forge_dag_schema import (
    ForgeDagReadCurrentRequest,
    ForgeDagReadCurrentResponse,
)
from app.mixed_module.application.inner_dto.mixed_dag_governance_inner_dto import (
    MixedDagGovernanceInnerDto,
)
from app.mixed_module.application.inner_dto.mixed_dependency_failure_inner_dto import (
    MixedDependencyFailureSetDto,
)
from app.mixed_module.application.mixed_application_utils import (
    completed_task_result,
    dependency_errors,
    dependency_failure_set,
    forge_gateway_failure,
    orchestration_gateway_failure,
    require_forge_success,
    require_orchestration_success,
)
from app.mixed_module.exceptions.mixed_exceptions import (
    MixedDependencyFailureError,
    MixedRequestContextError,
)
from app.mixed_module.schema.mixed_dag_governance_schema import (
    MixedDagGovernanceRequest,
)
from app.orchestration.application.autonomy_settlement_app import (
    AutonomySettlementApplication,
)
from app.orchestration.application.inner_dto.types.autonomy.autonomy_settlement_types import (
    DagSettlementGovernanceResponseDict,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_settlement_schema import (
    DagSettlementGovernanceResponse,
)
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import ForgeExcept, OrchestrationExcept
from app.shared.filter_module.autonomy_filter import DagSettlementGovernanceFilter

_GOVERNANCE_ADAPTER: TypeAdapter[DagSettlementGovernanceResponseDict] = TypeAdapter(
    DagSettlementGovernanceResponseDict
)


async def _fetch_forge_current_dag(
    calling: ForgeCalling,
    request: ForgeDagReadCurrentRequest,
) -> ForgeCommandSuccessEnvelopeDto[ForgeDagCurrentResultDict]:
    """Read Forge current DAG using the complete caller-supplied request.

    Args:
        calling: Request-scoped Forge caller with its own credential.
        request: Complete source request supplied by the mixed-view caller.
    Return:
        Typed Forge success envelope preserving the original request identity.
    """
    try:
        outcome = await ForgeWorkspaceApplication(forge_calling=calling).read_current_dag(
            request=request
        )
        result = require_forge_success(outcome=outcome)
        ForgeDagReadCurrentResponse.model_validate(result.to_dict())
    except ForgeExcept as error:
        raise forge_gateway_failure(error=error) from error
    except (ValidationError, ValueError) as error:
        invalid_response = ForgeExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="forge_invalid_payload",
            message="Gateway could not validate the current DAG projection",
            retryable=False,
            request_id=request.request_id,
        )
        raise forge_gateway_failure(error=invalid_response) from error
    return result


async def _fetch_governance(
    calling: OrchestrationCalling,
    workspace_id: UUID,
    filters: DagSettlementGovernanceFilter,
) -> DagSettlementGovernanceResponseDict:
    """Read the caller-selected Orchestration governance projection.

    Args:
        calling: Request-scoped Orchestration caller with its own credential.
        workspace_id: Workspace identity selected by the route path.
        filters: Required Goal and settled DAG revision query.
    Return:
        Validated governance projection at the selected revision.
    """
    try:
        outcome = await AutonomySettlementApplication(
            orchestration_calling=calling
        ).fetch_dag_settlement_governance(
            workspace_id=workspace_id,
            filters=filters,
        )
        result = require_orchestration_success(outcome=outcome, result_adapter=_GOVERNANCE_ADAPTER)
        DagSettlementGovernanceResponse.model_validate(result)
    except OrchestrationExcept as error:
        raise orchestration_gateway_failure(error=error) from error
    except (ValidationError, ValueError) as error:
        invalid_response = OrchestrationExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="orchestration_invalid_payload",
            message="Gateway could not validate the DAG governance projection",
            retryable=False,
            workspace_id=workspace_id,
        )
        raise orchestration_gateway_failure(error=invalid_response) from error
    return result


class MixedDagGovernanceApplication:
    """Compose current DAG and governance reads under one request owner."""

    def __init__(
        self,
        forge_calling: ForgeCalling,
        orchestration_calling: OrchestrationCalling,
    ) -> None:
        """Bind the two request-scoped backend callers.

        Args:
            forge_calling: Caller carrying only the Forge request credential.
            orchestration_calling: Caller carrying only the Orchestration credential.
        Return:
            None.
        """
        self._forge_calling = forge_calling
        self._orchestration_calling = orchestration_calling

    async def execute(
        self,
        workspace_id: UUID,
        request: MixedDagGovernanceRequest,
    ) -> MixedDagGovernanceInnerDto | MixedDependencyFailureSetDto:
        """Run both validated read legs and retain their independent revisions.

        Args:
            workspace_id: Workspace identity selected by the route path.
            request: Caller-supplied Forge command and governance lookup key.
        Return:
            Typed pair of source observations or preserved dependency failures.
        """
        forge_request = request.forge_request
        if forge_request.payload.scope.workspace_id != workspace_id:
            raise MixedRequestContextError(
                message="Forge scope Workspace must match the route Workspace",
                location=("body", "forge_request", "payload", "scope", "workspace_id"),
                rejected_value=str(forge_request.payload.scope.workspace_id),
            )
        governance_filter = DagSettlementGovernanceFilter(
            goalId=request.governance_query.goal_id,
            dagRevision=request.governance_query.dag_revision,
        )
        failures: tuple[MixedDependencyFailureError, ...] = ()
        forge_task: (
            asyncio.Task[ForgeCommandSuccessEnvelopeDto[ForgeDagCurrentResultDict]] | None
        ) = None
        governance_task: asyncio.Task[DagSettlementGovernanceResponseDict] | None = None
        try:
            async with asyncio.TaskGroup() as task_group:
                forge_task = task_group.create_task(
                    _fetch_forge_current_dag(calling=self._forge_calling, request=forge_request)
                )
                governance_task = task_group.create_task(
                    _fetch_governance(
                        calling=self._orchestration_calling,
                        workspace_id=workspace_id,
                        filters=governance_filter,
                    )
                )
        except* MixedDependencyFailureError as errors:
            failures = dependency_errors(errors=errors)
        if failures:
            result = dependency_failure_set(errors=failures)
            return result

        forge_result = completed_task_result(task=forge_task)
        governance_result = completed_task_result(task=governance_task)
        result = MixedDagGovernanceInnerDto(
            workspace_id=workspace_id,
            goal_id=forge_request.payload.goal_id,
            forge_request_id=forge_request.request_id,
            forge=forge_result,
            governance=governance_result,
        )
        return result
