"""Immutable DTO for the Mixed Swarm overview projection."""

from dataclasses import dataclass
from uuid import UUID

from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandSuccessEnvelopeDto,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmSettlementGetResponseDict,
)
from app.mixed_module.application.inner_dto.types.mixed_swarm_overview_types import (
    MixedSwarmOverviewDict,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_run_types import (
    SwarmRunInspectionResponseDict,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class MixedSwarmOverviewInnerDto:
    """Validated Forge and Orchestration projections for a requested Swarm."""

    workspace_id: UUID
    swarm_run_id: UUID
    forge: ForgeCommandSuccessEnvelopeDto[ForgeSwarmSettlementGetResponseDict]
    orchestration: SwarmRunInspectionResponseDict
    matches_filter: bool

    def to_dict(self) -> MixedSwarmOverviewDict:
        """Serialize both source projections with caller path identities.

        Args:
            None.
        Return:
            Complete typed Mixed Swarm overview response.
        """
        result = MixedSwarmOverviewDict(
            workspaceId=self.workspace_id,
            swarmRunId=self.swarm_run_id,
            forge=self.forge.to_dict(),
            orchestration=self.orchestration,
        )
        return result
