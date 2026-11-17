"""Immutable DTO for the Mixed Swarm overview projection."""

from dataclasses import dataclass
from uuid import UUID

from typing_extensions import TypedDict

from app.forge.application.forge_swarm_dto import ForgeSwarmSettlementGetResponseDict
from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandSuccessEnvelopeDto,
    ForgeSuccessEnvelopeDict,
)
from app.orchestration.application.inner_dto.swarm_run_inner_dto import (
    SwarmRunInspectionResponseDict,
)


class MixedSwarmOverviewDict(TypedDict, total=True, closed=True):
    """Complete JSON response for the Mixed Swarm overview."""

    workspaceId: UUID
    swarmRunId: UUID
    forge: ForgeSuccessEnvelopeDict[ForgeSwarmSettlementGetResponseDict]
    orchestration: SwarmRunInspectionResponseDict


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
