"""Exact-key Orchestration Autonomy query filters."""

from typing import Annotated

from pydantic import Field

from app.shared.filter_module.base_filter import BaseFilter
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    ExecutionSnapshotQueryFieldEnum,
)
from app.shared.types.wire_scalar_types import WireUUID

_I64_MAX = (1 << 63) - 1
_U32_MAX = (1 << 32) - 1


class ExecutionSnapshotFilter(BaseFilter):
    """Select one execution snapshot by its complete attempt key."""

    goal_id: Annotated[
        WireUUID,
        Field(
            description="Goal identity for the exact execution attempt.",
            alias=ExecutionSnapshotQueryFieldEnum.GOAL_ID.value,
        ),
    ]
    dag_revision: Annotated[
        int,
        Field(
            description="Positive DAG revision for the exact attempt.",
            ge=1,
            le=_I64_MAX,
            alias=ExecutionSnapshotQueryFieldEnum.DAG_REVISION.value,
        ),
    ]
    node_id: Annotated[
        WireUUID,
        Field(
            description="Node identity for the exact execution attempt.",
            alias=ExecutionSnapshotQueryFieldEnum.NODE_ID.value,
        ),
    ]
    assignment_id: Annotated[
        WireUUID,
        Field(
            description="Assignment identity for the exact attempt.",
            alias=ExecutionSnapshotQueryFieldEnum.ASSIGNMENT_ID.value,
        ),
    ]
    attempt: Annotated[
        int,
        Field(
            alias=ExecutionSnapshotQueryFieldEnum.ATTEMPT.value,
            description="Zero-based execution attempt number.",
            ge=0,
            le=_U32_MAX,
        ),
    ]


class DagSettlementGovernanceFilter(BaseFilter):
    """Select one durable settlement governance link by its exact key."""

    goal_id: Annotated[
        WireUUID,
        Field(description="Settled Goal identity.", alias="goalId"),
    ]
    dag_revision: Annotated[
        int,
        Field(
            description="Positive settled DAG revision.",
            ge=1,
            le=_I64_MAX,
            alias="dagRevision",
        ),
    ]
