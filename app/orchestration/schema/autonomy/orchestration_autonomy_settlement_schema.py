"""Strict schemas for Workspace DAG settlement authority and governance."""

from typing import Annotated

from pydantic import Field

from app.orchestration.schema.types.autonomy_types import (
    DagRevision,
    NonNegativeDagRevision,
    UnixTimestampMs,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt64
from app.shared.base_schema import StrictSchemaModel
from app.shared.types.wire_scalar_types import WireUUID


class DagSettlementParticipantSchema(StrictSchemaModel):
    """Identify the participant whose leadership authority is checked."""

    activity_id: Annotated[
        WireUUID,
        Field(description="Orchestration activity identity.", alias="activityId"),
    ]
    agent_id: Annotated[
        WireUUID,
        Field(description="Agent instance identity.", alias="agentId"),
    ]
    session_id: Annotated[
        WireUUID,
        Field(description="Agent session identity.", alias="sessionId"),
    ]


class DagSettlementAuthorityRequest(StrictSchemaModel):
    """Check settlement authority at one Workspace leadership revision."""

    expected_leadership_revision: Annotated[
        NonNegativeDagRevision,
        Field(
            description="Expected Workspace leadership revision.",
            alias="expectedLeadershipRevision",
        ),
    ]
    participant: Annotated[
        DagSettlementParticipantSchema | None,
        Field(description="Participant actor, or null for the local operator."),
    ]


class DagSettlementAuthorityResponse(StrictSchemaModel):
    """Verified leadership fence witness returned by Orchestration."""

    workspace_id: Annotated[
        WireUUID,
        Field(description="Workspace identity selected by the URL path.", alias="workspaceId"),
    ]
    leader_participant_id: Annotated[
        WireUUID | None,
        Field(
            description="Current leader participant identity, or null.", alias="leaderParticipantId"
        ),
    ]
    leadership_revision: Annotated[
        NonNegativeDagRevision,
        Field(description="Verified Workspace leadership revision.", alias="leadershipRevision"),
    ]


class DagSettlementGovernanceResponse(StrictSchemaModel):
    """Durable governance linkage for one settled Goal and DAG revision."""

    workspace_id: Annotated[
        WireUUID,
        Field(description="Workspace identity selected by the URL path.", alias="workspaceId"),
    ]
    goal_id: Annotated[WireUUID, Field(description="Settled Goal identity.", alias="goalId")]
    dag_revision: Annotated[
        DagRevision,
        Field(description="Settled DAG revision.", alias="dagRevision"),
    ]
    migration_id: Annotated[
        WireUUID,
        Field(description="Durable migration identity.", alias="migrationId"),
    ]
    source_sequence: Annotated[
        UInt64,
        Field(description="Source outbox sequence.", alias="sourceSequence"),
    ]
    settlement_id: Annotated[
        WireUUID,
        Field(description="Durable settlement identity.", alias="settlementId"),
    ]
    coordinator_agent_id: Annotated[
        WireUUID,
        Field(description="Coordinator agent identity.", alias="coordinatorAgentId"),
    ]
    coordinator_participant_id: Annotated[
        WireUUID | None,
        Field(
            description="Coordinator participant identity, or null.",
            alias="coordinatorParticipantId",
        ),
    ]
    workspace_leadership_revision: Annotated[
        Int64 | None,
        Field(
            description="Workspace leadership revision at settlement, or null.",
            alias="workspaceLeadershipRevision",
        ),
    ]
    accepted_work_credit_count: Annotated[
        UInt64,
        Field(description="Accepted work-credit count.", alias="acceptedWorkCreditCount"),
    ]
    evaluated_assignment_count: Annotated[
        UInt64,
        Field(description="Evaluated reviewer assignment count.", alias="evaluatedAssignmentCount"),
    ]
    started_mission_plan_id: Annotated[
        WireUUID | None,
        Field(description="Started mission plan identity, or null.", alias="startedMissionPlanId"),
    ]
    started_mission_plan_revision: Annotated[
        UInt64 | None,
        Field(
            description="Started mission plan revision, or null.",
            alias="startedMissionPlanRevision",
        ),
    ]
    settled_at_ms: Annotated[
        UnixTimestampMs,
        Field(description="Settlement time in Unix milliseconds.", alias="settledAtMs"),
    ]
    recall_voter_fulfillment_eligible: Annotated[
        bool,
        Field(
            description="Whether recall-voter fulfillment is eligible.",
            alias="recallVoterFulfillmentEligible",
        ),
    ]
