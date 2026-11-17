"""Strict forge swarm identity schema contracts."""

from typing import Annotated, Literal

from pydantic import Field

from app.forge.schema.types.forge_types import ForgeUUID, SwarmWorkspaceMode
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import SwarmTargetKindEnum


class ForgeSwarmStandaloneTarget(StrictSchemaModel):
    """Standalone Swarm target discriminator."""

    kind: Annotated[
        Literal[SwarmTargetKindEnum.STANDALONE_SWARM],
        Field(description="Standalone Swarm settlement target discriminator."),
    ]


class ForgeSwarmDagNodeHybridTarget(StrictSchemaModel):
    """DAG node hybrid target with its source revision fence."""

    kind: Annotated[
        Literal[SwarmTargetKindEnum.DAG_NODE_HYBRID],
        Field(description="DAG node hybrid settlement target discriminator."),
    ]
    goal_id: Annotated[ForgeUUID, Field(description="Goal receiving the settled Swarm node.")]
    dag_revision: Annotated[
        int,
        Field(
            description="Expected DAG revision for hybrid materialization.",
            ge=0,
            le=9_223_372_036_854_775_807,
        ),
    ]
    node_id: Annotated[ForgeUUID, Field(description="DAG node receiving the settled Swarm output.")]


ForgeSwarmTarget = Annotated[
    ForgeSwarmStandaloneTarget | ForgeSwarmDagNodeHybridTarget,
    Field(description="Tagged standalone or DAG node hybrid settlement target."),
]


class ForgeSwarmMemberIdentity(StrictSchemaModel):
    """Echoed Swarm run and member identity."""

    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]


class ForgeSwarmRunIdentity(StrictSchemaModel):
    """Echoed Swarm run identity."""

    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]


class ForgeSwarmMemberModeIdentity(StrictSchemaModel):
    """Echoed Swarm run, member, and workspace mode."""

    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]
    mode: Annotated[SwarmWorkspaceMode, Field(description="Workspace isolation mode.")]


class ForgeSwarmWorkspaceIdentity(StrictSchemaModel):
    """Echoed Workspace, Swarm run, and member identity."""

    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]


class ForgeSwarmWorkspaceRunIdentity(StrictSchemaModel):
    """Echoed Workspace and Swarm run identity."""

    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]


class ForgeSwarmSettlementReceiptIdentity(StrictSchemaModel):
    """Settlement identity and commit/target fields echoed by Forge."""

    settlement_id: Annotated[str, Field(description="Settlement identity string.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    converged_commit_oid: Annotated[str, Field(description="Converged commit identity.")]
    target: Annotated[ForgeSwarmTarget, Field(description="Settlement target.")]


class ForgeSwarmWorkspaceModeTargetIdentity(StrictSchemaModel):
    """Echoed workspace mode and tagged target identity."""

    mode: Annotated[SwarmWorkspaceMode, Field(description="Workspace isolation mode.")]
    target: Annotated[ForgeSwarmTarget, Field(description="Swarm workspace target.")]
