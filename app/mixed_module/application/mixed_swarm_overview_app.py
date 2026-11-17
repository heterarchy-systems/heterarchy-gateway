"""Request-owned Orchestration and Forge Swarm overview composition."""

import asyncio
from uuid import UUID

from fastapi import status
from pydantic import TypeAdapter, ValidationError

from app.forge.application.forge_swarm_app import ForgeSwarmApplication
from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandSuccessEnvelopeDto,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmSettlementGetResponseDict,
)
from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeLocator,
    ForgeWorkspaceScope,
)
from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmSettlementGetCommandRequest,
    ForgeSwarmSettlementGetRequest,
    ForgeSwarmSettlementGetResponse,
)
from app.mixed_module.application.inner_dto.mixed_dependency_failure_inner_dto import (
    MixedDependencyFailureSetDto,
)
from app.mixed_module.application.inner_dto.mixed_swarm_overview_inner_dto import (
    MixedSwarmOverviewInnerDto,
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
from app.mixed_module.exceptions.mixed_exceptions import MixedDependencyFailureError
from app.orchestration.application.inner_dto.types.swarm.swarm_run_types import (
    SwarmRunInspectionResponseDict,
)
from app.orchestration.application.swarm_run_app import SwarmRunApplication
from app.orchestration.schema.swarm.orchestration_swarm_run_schema import SwarmRunInspectionResponse
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import ForgeExcept, OrchestrationExcept
from app.shared.filter_module.mixed_module_filter import MixedSwarmOverviewFilter
from app.shared.ingredient_element.forge.forge_enums import (
    ForgeCommandOpEnum,
    SettlementJournalStateEnum,
)
from app.shared.ingredient_element.orchestration.swarm_enums import SwarmRunStateEnum

_INSPECTION_ADAPTER: TypeAdapter[SwarmRunInspectionResponseDict] = TypeAdapter(
    SwarmRunInspectionResponseDict
)


async def _fetch_forge_settlement(
    calling: ForgeCalling,
    request: ForgeSwarmSettlementGetCommandRequest,
) -> ForgeCommandSuccessEnvelopeDto[ForgeSwarmSettlementGetResponseDict]:
    """Fetch the exact caller-scoped Forge settlement observation.

    Args:
        calling: Request-scoped Forge caller carrying its separate credential.
        request: Forge request assembled solely from path and caller query values.
    Return:
        Validated Forge success envelope preserving the caller request identity.
    """
    try:
        outcome = await ForgeSwarmApplication(calling=calling).fetch_settlement(request=request)
        result = require_forge_success(outcome=outcome)
        ForgeSwarmSettlementGetResponse.model_validate(result.to_dict())
    except ForgeExcept as error:
        raise forge_gateway_failure(error=error) from error
    except (ValidationError, ValueError) as error:
        invalid_response = ForgeExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="forge_invalid_payload",
            message="Gateway could not validate the Forge settlement projection",
            retryable=False,
            request_id=request.request_id,
        )
        raise forge_gateway_failure(error=invalid_response) from error
    return result


async def _fetch_orchestration_inspection(
    calling: OrchestrationCalling,
    workspace_id: UUID,
    swarm_run_id: UUID,
) -> SwarmRunInspectionResponseDict:
    """Fetch and type-check the matching Orchestration run inspection.

    Args:
        calling: Request-scoped Orchestration caller with its own credential.
        workspace_id: Workspace identity selected by the route path.
        swarm_run_id: Swarm identity selected by the route path.
    Return:
        Validated complete source inspection dictionary.
    """
    try:
        outcome = await SwarmRunApplication(calling=calling).inspect_swarm_run(
            workspace_id=workspace_id,
            swarm_run_id=swarm_run_id,
        )
        result = require_orchestration_success(outcome=outcome, result_adapter=_INSPECTION_ADAPTER)
        SwarmRunInspectionResponse.model_validate(result)
    except OrchestrationExcept as error:
        raise orchestration_gateway_failure(error=error) from error
    except (ValidationError, ValueError) as error:
        invalid_response = OrchestrationExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="orchestration_invalid_payload",
            message="Gateway could not validate the Swarm inspection projection",
            retryable=False,
            workspace_id=workspace_id,
        )
        raise orchestration_gateway_failure(error=invalid_response) from error
    return result


def _forge_settlement_request(
    workspace_id: UUID,
    swarm_run_id: UUID,
    filters: MixedSwarmOverviewFilter,
) -> ForgeSwarmSettlementGetCommandRequest:
    """Build the strict Forge lookup request from explicit caller context.

    Args:
        workspace_id: Workspace identity selected by the route path.
        swarm_run_id: Swarm identity selected by the route path.
        filters: Required caller-supplied Forge request and locator values.
    Return:
        Complete source request with no synthesized locator or revision data.
    """
    scope = ForgeWorkspaceScope(
        workspace_id=workspace_id,
        workspace_revision=filters.workspace_revision,
        locator=ForgeLocator(
            location_id=filters.location_id,
            expected_revision=filters.expected_revision,
            relative_root=filters.relative_root,
        ),
    )
    payload = ForgeSwarmSettlementGetRequest(
        scope=scope,
        swarm_run_id=swarm_run_id,
    )
    result = ForgeSwarmSettlementGetCommandRequest(
        forge_api=1,
        request_id=filters.forge_request_id,
        op=ForgeCommandOpEnum.SWARM_SETTLEMENT_GET,
        payload=payload,
    )
    return result


class MixedSwarmOverviewApplication:
    """Compose two validated Swarm read projections under one request owner."""

    def __init__(
        self,
        forge_calling: ForgeCalling,
        orchestration_calling: OrchestrationCalling,
    ) -> None:
        """Bind request-scoped backend callers for the composition.

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
        swarm_run_id: UUID,
        filters: MixedSwarmOverviewFilter,
    ) -> MixedSwarmOverviewInnerDto | MixedDependencyFailureSetDto:
        """Read and compose the caller-scoped Forge and Swarm observations.

        Args:
            workspace_id: Workspace identity selected by the route path.
            swarm_run_id: Swarm identity selected by the route path.
            filters: Required Forge scope plus optional observation filters.
        Return:
            Typed overview result or exact dependency failure collection.
        """
        forge_request = _forge_settlement_request(
            workspace_id=workspace_id, swarm_run_id=swarm_run_id, filters=filters
        )
        failures: tuple[MixedDependencyFailureError, ...] = ()
        forge_task: (
            asyncio.Task[ForgeCommandSuccessEnvelopeDto[ForgeSwarmSettlementGetResponseDict]] | None
        ) = None
        orchestration_task: asyncio.Task[SwarmRunInspectionResponseDict] | None = None
        try:
            async with asyncio.TaskGroup() as task_group:
                forge_task = task_group.create_task(
                    _fetch_forge_settlement(calling=self._forge_calling, request=forge_request)
                )
                orchestration_task = task_group.create_task(
                    _fetch_orchestration_inspection(
                        calling=self._orchestration_calling,
                        workspace_id=workspace_id,
                        swarm_run_id=swarm_run_id,
                    )
                )
        except* MixedDependencyFailureError as errors:
            failures = dependency_errors(errors=errors)
        if failures:
            result = dependency_failure_set(errors=failures)
            return result

        forge_result = completed_task_result(task=forge_task)
        orchestration_result = completed_task_result(task=orchestration_task)
        receipt = forge_result.result["receipt"]
        settlement_state = (
            SettlementJournalStateEnum(receipt["state"]) if receipt is not None else None
        )
        run_state = SwarmRunStateEnum(orchestration_result["run"]["state"])
        matches_filter = filters.matches_observation(
            run_state=run_state, settlement_state=settlement_state
        )
        result = MixedSwarmOverviewInnerDto(
            workspace_id=workspace_id,
            swarm_run_id=swarm_run_id,
            forge=forge_result,
            orchestration=orchestration_result,
            matches_filter=matches_filter,
        )
        return result
