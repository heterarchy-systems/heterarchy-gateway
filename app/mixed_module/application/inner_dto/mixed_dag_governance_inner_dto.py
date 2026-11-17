"""Immutable DTO for independent DAG and governance observations."""

from dataclasses import dataclass
from uuid import UUID

from typing_extensions import TypedDict

from app.forge.application.forge_workspace_dto import ForgeDagCurrentResultDict
from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandSuccessEnvelopeDto,
    ForgeSuccessEnvelopeDict,
)
from app.orchestration.application.inner_dto.autonomy_settlement_inner_dto import (
    DagSettlementGovernanceResponseDict,
)


class MixedDagGovernanceDict(TypedDict, total=True, closed=True):
    """Complete typed response for the Mixed DAG governance view."""

    workspaceId: UUID
    goalId: UUID
    forgeRequestId: UUID
    forge: ForgeSuccessEnvelopeDict[ForgeDagCurrentResultDict]
    governance: DagSettlementGovernanceResponseDict


@dataclass(frozen=True, slots=True, kw_only=True)
class MixedDagGovernanceInnerDto:
    """Source projections and caller identities for one governance view."""

    workspace_id: UUID
    goal_id: UUID
    forge_request_id: UUID
    forge: ForgeCommandSuccessEnvelopeDto[ForgeDagCurrentResultDict]
    governance: DagSettlementGovernanceResponseDict

    def to_dict(self) -> MixedDagGovernanceDict:
        """Serialize each original read without merging revision authority.

        Args:
            None.
        Return:
            Complete typed DAG governance response.
        """
        result = MixedDagGovernanceDict(
            workspaceId=self.workspace_id,
            goalId=self.goal_id,
            forgeRequestId=self.forge_request_id,
            forge=self.forge.to_dict(),
            governance=self.governance,
        )
        return result
