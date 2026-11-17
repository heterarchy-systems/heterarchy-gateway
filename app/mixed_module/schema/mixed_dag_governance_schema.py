"""Strict request and response contracts for Mixed DAG governance reads."""

from typing import Annotated
from uuid import UUID

from pydantic import Field, model_validator

from app.forge.schema.dag.forge_dag_schema import (
    ForgeDagCurrentFoundResult,
    ForgeDagReadCurrentRequest,
    ForgeDagReadCurrentResponse,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_settlement_schema import (
    DagSettlementGovernanceResponse,
)
from app.orchestration.schema.types.autonomy_types import DagRevision
from app.shared.base_schema import StrictSchemaModel
from app.shared.types.wire_scalar_types import WireUUID


class MixedDagGovernanceIdentitySchema(StrictSchemaModel):
    """Comparable Workspace, Goal, and caller request identity."""

    workspace_id: Annotated[
        UUID,
        Field(alias="workspaceId", description="Workspace identity."),
    ]
    goal_id: Annotated[UUID, Field(alias="goalId", description="Goal identity.")]
    forge_request_id: Annotated[
        UUID,
        Field(alias="forgeRequestId", description="Caller Forge request identity."),
    ]


class DagSettlementGovernanceQuerySchema(StrictSchemaModel):
    """Required source key selecting one governance observation."""

    goal_id: Annotated[
        WireUUID,
        Field(alias="goalId", description="Goal identity selected at Orchestration."),
    ]
    dag_revision: Annotated[
        DagRevision,
        Field(alias="dagRevision", description="Settled revision selected at Orchestration."),
    ]


class MixedDagGovernanceRequest(StrictSchemaModel):
    """Caller-owned Forge read context and Orchestration governance key."""

    forge_request: Annotated[
        ForgeDagReadCurrentRequest,
        Field(description="Complete caller-supplied Forge current-DAG command."),
    ]
    governance_query: Annotated[
        DagSettlementGovernanceQuerySchema,
        Field(description="Required Orchestration governance lookup key."),
    ]

    @model_validator(mode="after")
    def validate_goal_identity(self) -> MixedDagGovernanceRequest:
        """Require the two caller-selected reads to name the same Goal.

        Args:
            None.
        Return:
            Validated combined request.
        """
        if self.forge_request.payload.goal_id != self.governance_query.goal_id:
            raise ValueError("Forge and governance requests must select the same Goal")
        result = self
        return result


class MixedDagGovernanceResponse(StrictSchemaModel):
    """Independent Forge current and Orchestration governance observations."""

    workspace_id: Annotated[
        UUID,
        Field(alias="workspaceId", description="Workspace identity selected by the path."),
    ]
    goal_id: Annotated[
        UUID,
        Field(alias="goalId", description="Goal identity selected by the caller."),
    ]
    forge_request_id: Annotated[
        UUID,
        Field(alias="forgeRequestId", description="Original Forge command request identity."),
    ]
    forge: Annotated[
        ForgeDagReadCurrentResponse,
        Field(description="Forge current-DAG read at its independently observed revision."),
    ]
    governance: Annotated[
        DagSettlementGovernanceResponse,
        Field(
            description=(
                "Orchestration governance read at the caller-selected settled revision. "
                "Its revision is an independent observation."
            ),
        ),
    ]

    @model_validator(mode="after")
    def validate_projection_identities(self) -> MixedDagGovernanceResponse:
        """Require each source projection to match its caller-selected identity.

        Args:
            None.
        Return:
            Validated pair of independent source observations.
        """
        expected = MixedDagGovernanceIdentitySchema(
            workspaceId=self.workspace_id,
            goalId=self.goal_id,
            forgeRequestId=self.forge_request_id,
        )
        observed = MixedDagGovernanceIdentitySchema(
            workspaceId=self.governance.workspace_id,
            goalId=self.governance.goal_id,
            forgeRequestId=self.forge.request_id,
        )
        current_result = self.forge.result.root
        if observed != expected:
            raise ValueError("Mixed DAG governance legs escaped their request identities")
        if (
            isinstance(current_result, ForgeDagCurrentFoundResult)
            and current_result.goal_id != self.goal_id
        ):
            raise ValueError("Forge current-DAG result escaped the requested Goal")
        result = self
        return result
