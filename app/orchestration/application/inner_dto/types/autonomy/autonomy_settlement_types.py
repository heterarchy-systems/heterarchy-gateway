"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing_extensions import TypedDict

from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    NonNegativeDagRevision,
    UnixTimestampMs,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt64


class DagSettlementParticipantDict(TypedDict, total=True, closed=True):
    """Participant coordinates used for settlement authority checks."""

    activityId: str
    agentId: str
    sessionId: str


class DagSettlementAuthorityRequestDict(TypedDict, total=True, closed=True):
    """Complete settlement authority request dictionary."""

    expectedLeadershipRevision: NonNegativeDagRevision
    participant: DagSettlementParticipantDict | None


class DagSettlementAuthorityResponseDict(TypedDict, total=True, closed=True):
    """Verified Workspace settlement leadership response dictionary."""

    workspaceId: str
    leaderParticipantId: str | None
    leadershipRevision: NonNegativeDagRevision


class DagSettlementGovernanceResponseDict(TypedDict, total=True, closed=True):
    """Complete durable settlement governance response dictionary."""

    workspaceId: str
    goalId: str
    dagRevision: DagRevision
    migrationId: str
    sourceSequence: UInt64
    settlementId: str
    coordinatorAgentId: str
    coordinatorParticipantId: str | None
    workspaceLeadershipRevision: Int64 | None
    acceptedWorkCreditCount: UInt64
    evaluatedAssignmentCount: UInt64
    startedMissionPlanId: str | None
    startedMissionPlanRevision: UInt64 | None
    settledAtMs: UnixTimestampMs
    recallVoterFulfillmentEligible: bool
