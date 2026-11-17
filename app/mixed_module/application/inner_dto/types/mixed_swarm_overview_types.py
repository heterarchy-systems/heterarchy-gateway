"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from uuid import UUID

from typing_extensions import TypedDict

from app.forge.application.inner_dto.types.forge_envelope_types import (
    ForgeSuccessEnvelopeDict,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmSettlementGetResponseDict,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_run_types import (
    SwarmRunInspectionResponseDict,
)


class MixedSwarmOverviewDict(TypedDict, total=True, closed=True):
    """Complete JSON response for the Mixed Swarm overview."""

    workspaceId: UUID
    swarmRunId: UUID
    forge: ForgeSuccessEnvelopeDict[ForgeSwarmSettlementGetResponseDict]
    orchestration: SwarmRunInspectionResponseDict
