"""Source-preserving applications for DAG settlement contracts."""

from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.inner_dto.autonomy_settlement_inner_dto import (
    DagSettlementAuthorityCommandDto,
    DagSettlementAuthorityResponseDict,
    DagSettlementAuthorityResponseDto,
    DagSettlementGovernanceResponseDict,
    DagSettlementGovernanceResponseDto,
    DagSettlementParticipantDto,
)
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.orchestration_command_utils import (
    execute_orchestration_operation,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_settlement_schema import (
    DagSettlementAuthorityRequest,
    DagSettlementAuthorityResponse,
    DagSettlementGovernanceResponse,
)
from app.orchestration.schema.types.autonomy_types import NonNegativeDagRevision
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.filter_module.autonomy_filter import DagSettlementGovernanceFilter


def _source_authority_command(
    request: DagSettlementAuthorityRequest,
) -> DagSettlementAuthorityCommandDto:
    participant_schema = request.participant
    participant = (
        DagSettlementParticipantDto(
            activity_id=participant_schema.activity_id,
            agent_id=participant_schema.agent_id,
            session_id=participant_schema.session_id,
        )
        if participant_schema is not None
        else None
    )
    result = DagSettlementAuthorityCommandDto(
        expected_leadership_revision=request.expected_leadership_revision,
        participant=participant,
    )
    return result


def _parse_authority_response(
    payload: JsonValue,
    workspace_id: UUID,
    expected_leadership_revision: NonNegativeDagRevision,
) -> DagSettlementAuthorityResponseDict:
    schema = DagSettlementAuthorityResponse.model_validate(payload)
    if schema.workspace_id != workspace_id:
        raise ValueError("Settlement authority response escaped the requested Workspace")
    if schema.leadership_revision != expected_leadership_revision:
        raise ValueError("Settlement authority response did not echo the requested revision")
    if schema.leader_participant_id is not None and schema.leader_participant_id.int == 0:
        raise ValueError("Settlement authority response returned a nil leader identity")
    result = DagSettlementAuthorityResponseDto(
        workspace_id=schema.workspace_id,
        leader_participant_id=schema.leader_participant_id,
        leadership_revision=schema.leadership_revision,
    ).to_dict()
    return result


def _parse_governance_response(
    payload: JsonValue,
    workspace_id: UUID,
    filters: DagSettlementGovernanceFilter,
) -> DagSettlementGovernanceResponseDict:
    schema = DagSettlementGovernanceResponse.model_validate(payload)
    if (
        schema.workspace_id != workspace_id
        or schema.goal_id != filters.goal_id
        or schema.dag_revision != filters.dag_revision
        or schema.migration_id.int == 0
        or schema.source_sequence == 0
        or schema.settlement_id.int == 0
        or schema.coordinator_agent_id.int == 0
        or (
            schema.coordinator_participant_id is not None
            and schema.coordinator_participant_id.int == 0
        )
        or (schema.started_mission_plan_id is not None and schema.started_mission_plan_id.int == 0)
    ):
        raise ValueError("Governance response violates its source identity and revision fences")
    result = DagSettlementGovernanceResponseDto(
        workspace_id=schema.workspace_id,
        goal_id=schema.goal_id,
        dag_revision=schema.dag_revision,
        migration_id=schema.migration_id,
        source_sequence=schema.source_sequence,
        settlement_id=schema.settlement_id,
        coordinator_agent_id=schema.coordinator_agent_id,
        coordinator_participant_id=schema.coordinator_participant_id,
        workspace_leadership_revision=schema.workspace_leadership_revision,
        accepted_work_credit_count=schema.accepted_work_credit_count,
        evaluated_assignment_count=schema.evaluated_assignment_count,
        started_mission_plan_id=schema.started_mission_plan_id,
        started_mission_plan_revision=schema.started_mission_plan_revision,
        settled_at_ms=schema.settled_at_ms,
        recall_voter_fulfillment_eligible=schema.recall_voter_fulfillment_eligible,
    ).to_dict()
    return result


class AutonomySettlementApplication:
    """Execute settlement authority and governance reads."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the request-scoped Orchestration caller.

        Args:
            orchestration_calling: Caller carrying this request's upstream authority.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def check_dag_settlement_authority(
        self,
        workspace_id: UUID,
        request: DagSettlementAuthorityRequest,
    ) -> OrchestrationOutcomeDto[DagSettlementAuthorityResponseDict]:
        """Verify one Workspace settlement leadership revision fence.

        Args:
            workspace_id: Workspace identity selected by the public route.
            request: Strictly validated settlement authority request.
        Return:
            Source status and typed leadership fence witness.
        """
        command = _source_authority_command(request=request)
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/internal/v1/workspaces/{workspace_id}/dag-settlement-authority",
            parse_result=partial(
                _parse_authority_response,
                workspace_id=workspace_id,
                expected_leadership_revision=request.expected_leadership_revision,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
        )
        return result

    async def fetch_dag_settlement_governance(
        self,
        workspace_id: UUID,
        filters: DagSettlementGovernanceFilter,
    ) -> OrchestrationOutcomeDto[DagSettlementGovernanceResponseDict]:
        """Read one durable settlement governance link by its exact key.

        Args:
            workspace_id: Workspace identity selected by the public route.
            filters: Required Goal and DAG revision query key.
        Return:
            Source status and typed settlement governance projection.
        """
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path=f"/internal/v1/workspaces/{workspace_id}/dag-settlement-governance",
            parse_result=partial(
                _parse_governance_response, workspace_id=workspace_id, filters=filters
            ),
            params=filters.to_query_params(),
            result_statuses=(status.HTTP_200_OK,),
            workspace_id=workspace_id,
        )
        return result
