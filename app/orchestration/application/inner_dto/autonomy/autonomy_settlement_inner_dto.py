"""Immutable DTOs for DAG settlement authority and governance."""

from dataclasses import dataclass
from uuid import UUID

from app.orchestration.application.inner_dto.types.autonomy.autonomy_settlement_types import (
    DagSettlementAuthorityRequestDict,
    DagSettlementAuthorityResponseDict,
    DagSettlementGovernanceResponseDict,
    DagSettlementParticipantDict,
)
from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    NonNegativeDagRevision,
    UnixTimestampMs,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt64


@dataclass(frozen=True, slots=True, kw_only=True)
class DagSettlementParticipantDto:
    """Immutable participant actor for a settlement authority check."""

    activity_id: UUID
    agent_id: UUID
    session_id: UUID

    def to_dict(self) -> DagSettlementParticipantDict:
        """Serialize participant coordinates using source wire aliases.

        Args:
            None.
        Return:
            Complete settlement participant dictionary.
        """
        result = DagSettlementParticipantDict(
            activityId=str(self.activity_id),
            agentId=str(self.agent_id),
            sessionId=str(self.session_id),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class DagSettlementAuthorityCommandDto:
    """Immutable request to verify the Workspace leadership fence."""

    expected_leadership_revision: NonNegativeDagRevision
    participant: DagSettlementParticipantDto | None

    def to_dict(self) -> DagSettlementAuthorityRequestDict:
        """Serialize the settlement authority check request.

        Args:
            None.
        Return:
            Complete settlement authority request dictionary.
        """
        participant = self.participant.to_dict() if self.participant is not None else None
        result = DagSettlementAuthorityRequestDict(
            expectedLeadershipRevision=self.expected_leadership_revision,
            participant=participant,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class DagSettlementAuthorityResponseDto:
    """Immutable verified Workspace leadership fence witness."""

    workspace_id: UUID
    leader_participant_id: UUID | None
    leadership_revision: NonNegativeDagRevision

    def to_dict(self) -> DagSettlementAuthorityResponseDict:
        """Serialize the settlement authority witness response.

        Args:
            None.
        Return:
            Complete settlement authority response dictionary.
        """
        leader_participant_id = (
            str(self.leader_participant_id) if self.leader_participant_id is not None else None
        )
        result = DagSettlementAuthorityResponseDict(
            workspaceId=str(self.workspace_id),
            leaderParticipantId=leader_participant_id,
            leadershipRevision=self.leadership_revision,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class DagSettlementGovernanceResponseDto:
    """Immutable durable DAG settlement governance projection."""

    workspace_id: UUID
    goal_id: UUID
    dag_revision: DagRevision
    migration_id: UUID
    source_sequence: UInt64
    settlement_id: UUID
    coordinator_agent_id: UUID
    coordinator_participant_id: UUID | None
    workspace_leadership_revision: Int64 | None
    accepted_work_credit_count: UInt64
    evaluated_assignment_count: UInt64
    started_mission_plan_id: UUID | None
    started_mission_plan_revision: UInt64 | None
    settled_at_ms: UnixTimestampMs
    recall_voter_fulfillment_eligible: bool

    def to_dict(self) -> DagSettlementGovernanceResponseDict:
        """Serialize the governance projection with source nullable fields.

        Args:
            None.
        Return:
            Complete DAG settlement governance dictionary.
        """
        coordinator_participant_id = (
            str(self.coordinator_participant_id)
            if self.coordinator_participant_id is not None
            else None
        )
        started_mission_plan_id = (
            str(self.started_mission_plan_id) if self.started_mission_plan_id is not None else None
        )
        result = DagSettlementGovernanceResponseDict(
            workspaceId=str(self.workspace_id),
            goalId=str(self.goal_id),
            dagRevision=self.dag_revision,
            migrationId=str(self.migration_id),
            sourceSequence=self.source_sequence,
            settlementId=str(self.settlement_id),
            coordinatorAgentId=str(self.coordinator_agent_id),
            coordinatorParticipantId=coordinator_participant_id,
            workspaceLeadershipRevision=self.workspace_leadership_revision,
            acceptedWorkCreditCount=self.accepted_work_credit_count,
            evaluatedAssignmentCount=self.evaluated_assignment_count,
            startedMissionPlanId=started_mission_plan_id,
            startedMissionPlanRevision=self.started_mission_plan_revision,
            settledAtMs=self.settled_at_ms,
            recallVoterFulfillmentEligible=self.recall_voter_fulfillment_eligible,
        )
        return result
