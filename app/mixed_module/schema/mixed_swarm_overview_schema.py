"""Strict public contract for the Mixed Native Swarm overview."""

from typing import Annotated
from uuid import UUID

from pydantic import Field, model_validator

from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmSettlementGetResponse,
)
from app.orchestration.schema.swarm.orchestration_swarm_run_schema import (
    SwarmRunInspectionResponse,
    SwarmRunScopeIdentity,
)
from app.shared.base_schema import StrictSchemaModel


class MixedSwarmOverviewResponse(StrictSchemaModel):
    """Two independently validated source projections for one Swarm run."""

    workspace_id: Annotated[
        UUID,
        Field(alias="workspaceId", description="Workspace identity in both projections."),
    ]
    swarm_run_id: Annotated[
        UUID,
        Field(alias="swarmRunId", description="Swarm run identity in both projections."),
    ]
    forge: Annotated[
        ForgeSwarmSettlementGetResponse,
        Field(description="Forge settlement receipt and outbox observation."),
    ]
    orchestration: Annotated[
        SwarmRunInspectionResponse,
        Field(description="Orchestration run, roster, channels, and board observation."),
    ]

    @model_validator(mode="after")
    def validate_projection_identities(self) -> MixedSwarmOverviewResponse:
        """Require both source legs to describe the same path identities.

        Args:
            None.
        Return:
            Validated combined source observation.
        """
        expected = SwarmRunScopeIdentity(
            workspace_id=self.workspace_id,
            swarm_run_id=self.swarm_run_id,
        )
        forge_identity = SwarmRunScopeIdentity(
            workspace_id=self.forge.result.workspace_id,
            swarm_run_id=self.forge.result.swarm_run_id,
        )
        orchestration_identity = SwarmRunScopeIdentity(
            workspace_id=self.orchestration.run.workspace_id,
            swarm_run_id=self.orchestration.run.swarm_run_id,
        )
        if forge_identity != expected or orchestration_identity != expected:
            raise ValueError("Mixed Swarm overview legs escaped their path identities")
        result = self
        return result
