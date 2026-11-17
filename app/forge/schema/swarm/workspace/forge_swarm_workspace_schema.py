"""Strict forge swarm workspace schema contracts."""

from typing import Annotated, Literal

from pydantic import Field

from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeCommandRequest,
    ForgeSessionActor,
    ForgeSuccessEnvelope,
    ForgeWorkspaceScope,
)
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import ForgeSwarmMemberOutputResult
from app.forge.schema.swarm.identity.forge_swarm_identity_schema import (
    ForgeSwarmTarget,
)
from app.forge.schema.types.forge_types import ForgeUUID, SwarmWorkspaceMode
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum


class ForgeSwarmWorkspaceReceiptResult(StrictSchemaModel):
    """Provisioned member workspace receipt."""

    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run owning the workspace.")]
    member_id: Annotated[ForgeUUID, Field(description="Member owning the workspace.")]
    mode: Annotated[SwarmWorkspaceMode, Field(description="Workspace isolation mode.")]
    target: Annotated[ForgeSwarmTarget, Field(description="Provisioning target.")]
    worktree_path: Annotated[str, Field(description="Confined member worktree path.")]
    provisioned_at_ms: Annotated[
        int,
        Field(
            description="Provision time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]
    initial_tree_blake3: Annotated[str, Field(description="Initial workspace tree digest.")]
    initial_file_count: Annotated[
        int,
        Field(
            description="Number of files in the initial tree.", ge=0, le=18_446_744_073_709_551_615
        ),
    ]
    input_commit_oid: Annotated[str, Field(description="Input commit used for provisioning.")]
    completed: Annotated[
        ForgeSwarmMemberOutputResult | None,
        Field(description="Completed member output, omitted by Forge while incomplete."),
    ]


class ForgeSwarmWorkspaceProvisionRequest(StrictSchemaModel):
    """Provision one Swarm member workspace through Forge."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    actor: Annotated[ForgeSessionActor, Field(description="Authenticated Forge session actor.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]
    mode: Annotated[SwarmWorkspaceMode, Field(description="Workspace isolation mode.")]
    target: Annotated[ForgeSwarmTarget, Field(description="Workspace provisioning target.")]
    candidate_commit_oid: Annotated[
        str | None,
        Field(description="Optional candidate commit used to seed the workspace."),
    ]
    observed_at_ms: Annotated[
        int,
        Field(
            description="Observation time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]


class ForgeSwarmWorkspaceProvisionResponse(ForgeSuccessEnvelope[ForgeSwarmWorkspaceReceiptResult]):
    """Successful envelope for provisioning one Swarm member workspace."""


class ForgeSwarmWorkspaceGetRequest(StrictSchemaModel):
    """Read one Swarm member workspace receipt."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]


class ForgeSwarmWorkspaceGetResult(StrictSchemaModel):
    """Workspace lookup result, including its source presence flag."""

    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]
    found: Annotated[bool, Field(description="Whether a provisioned workspace receipt exists.")]
    receipt: Annotated[
        ForgeSwarmWorkspaceReceiptResult | None,
        Field(description="Workspace receipt, omitted by Forge when absent."),
    ]


class ForgeSwarmPurgeRequest(StrictSchemaModel):
    """Purge a Swarm workspace projection."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    actor: Annotated[ForgeSessionActor, Field(description="Authenticated Forge session actor.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]


class ForgeSwarmPurgeResult(StrictSchemaModel):
    """Result of a Swarm workspace purge."""

    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    purged: Annotated[bool, Field(description="Whether the Swarm workspace was purged.")]


class ForgeSwarmWorkspaceGetResponse(ForgeSuccessEnvelope[ForgeSwarmWorkspaceGetResult]):
    """Successful envelope for reading one Swarm member workspace."""


class ForgeSwarmPurgeResponse(ForgeSuccessEnvelope[ForgeSwarmPurgeResult]):
    """Successful envelope for a Swarm workspace purge."""


class ForgeSwarmWorkspaceProvisionCommandRequest(
    ForgeCommandRequest[ForgeSwarmWorkspaceProvisionRequest]
):
    """Versioned provision request with the operation fixed by its route."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.SWARM_WORKSPACE_PROVISION],
        Field(description="Forge operation selected by this route."),
    ]


class ForgeSwarmWorkspaceGetCommandRequest(ForgeCommandRequest[ForgeSwarmWorkspaceGetRequest]):
    """Versioned workspace lookup request with its route operation fixed."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.SWARM_WORKSPACE_GET],
        Field(description="Forge operation selected by this route."),
    ]


class ForgeSwarmPurgeCommandRequest(ForgeCommandRequest[ForgeSwarmPurgeRequest]):
    """Versioned purge request with its route operation fixed."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.SWARM_PURGE],
        Field(description="Forge operation selected by this route."),
    ]
