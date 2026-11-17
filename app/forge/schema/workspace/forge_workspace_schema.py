"""Strict forge workspace schema contracts."""

from typing import Annotated, Literal

from pydantic import Field

from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeCommandRequest,
    ForgeSuccessEnvelope,
)
from app.forge.schema.types.forge_types import ForgeUUID, Int64
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum


class ForgeWorkspaceListPayload(StrictSchemaModel):
    """Strict payload for listing Workspaces within one Location revision."""

    location_id: Annotated[ForgeUUID, Field(description="Registered Location identity.")]
    expected_revision: Annotated[Int64, Field(description="Expected Location revision.")]


class ForgeWorkspaceEntry(StrictSchemaModel):
    """One Workspace discovered at the requested Location revision."""

    locator: Annotated[str, Field(description="Canonical Source workspace locator.")]
    display_name: Annotated[str, Field(description="Display name of the Workspace.")]
    workspace_id: Annotated[ForgeUUID, Field(description="Durable Workspace identity.")]
    workspace_revision: Annotated[Int64, Field(description="Current Workspace revision.")]


class ForgeWorkspaceListResult(StrictSchemaModel):
    """Workspace collection returned by workspace.list."""

    entries: Annotated[list[ForgeWorkspaceEntry], Field(description="Discovered Workspaces.")]


class ForgeWorkspaceListRequest(ForgeCommandRequest[ForgeWorkspaceListPayload]):
    """Versioned workspace.list command request."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.WORKSPACE_LIST],
        Field(description="This route executes workspace.list."),
    ]


class ForgeWorkspaceListResponse(ForgeSuccessEnvelope[ForgeWorkspaceListResult]):
    """Successful workspace.list response envelope."""
