"""Immutable DTO for independent DAG and governance observations."""

from dataclasses import dataclass
from uuid import UUID

from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandSuccessEnvelopeDto,
)
from app.forge.application.inner_dto.types.forge_workspace_types import (
    ForgeDagCurrentResultDict,
)
from app.mixed_module.application.inner_dto.types.mixed_dag_governance_types import (
    MixedDagGovernanceDict,
)
from app.orchestration.application.inner_dto.types.autonomy.autonomy_settlement_types import (
    DagSettlementGovernanceResponseDict,
)


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
