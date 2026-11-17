"""Strict forge swarm capture schema contracts."""

from typing import Annotated, Literal

from pydantic import Field

from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeCommandRequest,
    ForgeSessionActor,
    ForgeSuccessEnvelope,
    ForgeWorkspaceScope,
)
from app.forge.schema.types.forge_types import ForgeUUID, SwarmWorkspaceMode
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum


class ForgeSwarmMemberOutputResult(StrictSchemaModel):
    """Captured member workspace output receipt."""

    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run owning the member output.")]
    member_id: Annotated[ForgeUUID, Field(description="Member that produced the output.")]
    mode: Annotated[SwarmWorkspaceMode, Field(description="Workspace isolation mode.")]
    input_commit_oid: Annotated[str, Field(description="Input commit used by the member.")]
    output_commit_oid: Annotated[str, Field(description="Captured output commit.")]
    initial_tree_blake3: Annotated[str, Field(description="Initial workspace tree digest.")]
    final_tree_blake3: Annotated[str, Field(description="Final workspace tree digest.")]
    final_file_count: Annotated[
        int,
        Field(
            description="Number of files in the final tree.", ge=0, le=18_446_744_073_709_551_615
        ),
    ]
    changed_paths: Annotated[list[str], Field(description="Changed workspace-relative paths.")]
    diff_digest: Annotated[str, Field(description="Hexadecimal digest of the captured diff.")]
    captured_at_ms: Annotated[
        int,
        Field(
            description="Capture time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]


class ForgeSwarmMemberCaptureRequest(StrictSchemaModel):
    """Capture one member's completed workspace output."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    actor: Annotated[ForgeSessionActor, Field(description="Authenticated Forge session actor.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]
    captured_at_ms: Annotated[
        int,
        Field(
            description="Capture time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]


class ForgeSwarmMemberCaptureResult(ForgeSwarmMemberOutputResult):
    """Response for a member output capture."""


class ForgeSwarmMemberCaptureResponse(ForgeSuccessEnvelope[ForgeSwarmMemberCaptureResult]):
    """Successful envelope for capturing one member output."""


class ForgeSwarmMemberCaptureCommandRequest(ForgeCommandRequest[ForgeSwarmMemberCaptureRequest]):
    """Versioned member capture request with its route operation fixed."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.SWARM_MEMBER_CAPTURE],
        Field(description="Forge operation selected by this route."),
    ]
