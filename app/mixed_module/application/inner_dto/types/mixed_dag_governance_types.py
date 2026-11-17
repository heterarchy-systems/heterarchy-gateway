"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from uuid import UUID

from typing_extensions import TypedDict

from app.forge.application.inner_dto.types.forge_envelope_types import (
    ForgeSuccessEnvelopeDict,
)
from app.forge.application.inner_dto.types.forge_workspace_types import (
    ForgeDagCurrentResultDict,
)
from app.orchestration.application.inner_dto.types.autonomy.autonomy_settlement_types import (
    DagSettlementGovernanceResponseDict,
)


class MixedDagGovernanceDict(TypedDict, total=True, closed=True):
    """Complete typed response for the Mixed DAG governance view."""

    workspaceId: UUID
    goalId: UUID
    forgeRequestId: UUID
    forge: ForgeSuccessEnvelopeDict[ForgeDagCurrentResultDict]
    governance: DagSettlementGovernanceResponseDict
