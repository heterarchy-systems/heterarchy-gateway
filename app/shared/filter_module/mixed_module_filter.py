"""Strict caller context and observation filters for Mixed Swarm overview."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from pydantic import Field

from app.shared.filter_module.base_filter import BaseFilter
from app.shared.ingredient_element.forge.forge_enums import SettlementJournalStateEnum
from app.shared.ingredient_element.gateway.mixed_enums import MixedOverviewQueryKeyEnum
from app.shared.ingredient_element.orchestration.swarm_enums import SwarmRunStateEnum
from app.shared.types.wire_scalar_types import WireUUID

_I64_MIN = -(1 << 63)
_I64_MAX = (1 << 63) - 1


@dataclass(frozen=True, slots=True, kw_only=True)
class _SwarmOverviewObservation:
    run_state: SwarmRunStateEnum
    has_applied_settlement: bool


def _matches_run_state(criterion: str, observation: _SwarmOverviewObservation) -> bool:
    result = criterion == observation.run_state.value
    return result


def _matches_settled_only(criterion: str, observation: _SwarmOverviewObservation) -> bool:
    result = criterion == "false" or observation.has_applied_settlement
    return result


_OVERVIEW_PREDICATES: dict[str, Callable[[str, _SwarmOverviewObservation], bool]] = {
    MixedOverviewQueryKeyEnum.RUN_STATE.value: _matches_run_state,
    MixedOverviewQueryKeyEnum.SETTLED_ONLY.value: _matches_settled_only,
}


class MixedSwarmOverviewFilter(BaseFilter):
    """Bind caller-supplied Forge scope and optional Swarm observations."""

    forge_request_id: Annotated[
        WireUUID,
        Field(
            description="Caller-supplied Forge settlement lookup request identity.",
            alias=MixedOverviewQueryKeyEnum.FORGE_REQUEST_ID.value,
        ),
    ]
    workspace_revision: Annotated[
        int,
        Field(
            description="Caller-observed Forge Workspace revision.",
            ge=_I64_MIN,
            le=_I64_MAX,
            alias=MixedOverviewQueryKeyEnum.WORKSPACE_REVISION.value,
        ),
    ]
    location_id: Annotated[
        WireUUID,
        Field(
            description="Caller-supplied Forge Location identity.",
            alias=MixedOverviewQueryKeyEnum.LOCATION_ID.value,
        ),
    ]
    expected_revision: Annotated[
        int,
        Field(
            description="Caller-observed Forge Location revision.",
            ge=_I64_MIN,
            le=_I64_MAX,
            alias=MixedOverviewQueryKeyEnum.EXPECTED_REVISION.value,
        ),
    ]
    relative_root: Annotated[
        str,
        Field(description="Caller-supplied relative Forge Workspace root."),
    ]
    run_state: Annotated[
        SwarmRunStateEnum | None,
        Field(
            description="Optional canonical Orchestration run-state observation.",
            alias=MixedOverviewQueryKeyEnum.RUN_STATE.value,
        ),
    ] = None
    settled_only: Annotated[
        bool | None,
        Field(
            description="When true, require an applied Forge settlement receipt.",
            alias=MixedOverviewQueryKeyEnum.SETTLED_ONLY.value,
        ),
    ] = None

    def matches_observation(
        self,
        run_state: SwarmRunStateEnum,
        settlement_state: SettlementJournalStateEnum | None,
    ) -> bool:
        """Match only explicitly requested state observations.

        Args:
            run_state: Canonical state returned by Orchestration.
            settlement_state: Forge receipt state, when a receipt exists.
        Return:
            Whether all configured observation filters match.
        """
        observation = _SwarmOverviewObservation(
            run_state=run_state,
            has_applied_settlement=settlement_state == SettlementJournalStateEnum.APPLIED,
        )
        active_criteria = {
            key: value
            for key, value in self.to_query_params().items()
            if key in _OVERVIEW_PREDICATES
        }
        result = all(
            _OVERVIEW_PREDICATES[key](value, observation) for key, value in active_criteria.items()
        )
        return result
