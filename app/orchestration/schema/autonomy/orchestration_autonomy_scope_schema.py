"""Strict schemas for Orchestration workspace scopes."""

from typing import Annotated

from pydantic import Field

from app.orchestration.schema.types.autonomy_types import (
    PositiveInt64,
    UnixTimestampMs,
    UnsignedRevision,
)
from app.shared.base_schema import StrictRootSchemaModel, StrictSchemaModel
from app.shared.types.wire_scalar_types import WireUUID


class WorkspaceQueryScopeSchema(StrictSchemaModel):
    """Reference one Workspace within a specific Forge revision."""

    workspace_id: Annotated[
        WireUUID,
        Field(description="Workspace identity.", alias="workspaceId"),
    ]
    location_id: Annotated[
        WireUUID,
        Field(description="Parent Forge Location identity.", alias="locationId"),
    ]
    location_revision: Annotated[
        PositiveInt64,
        Field(description="Positive Forge Location revision.", ge=1, alias="locationRevision"),
    ]
    workspace_revision: Annotated[
        PositiveInt64,
        Field(description="Positive Forge Workspace revision.", ge=1, alias="workspaceRevision"),
    ]
    locator: Annotated[
        str,
        Field(description="Forge locator identifying this Workspace revision."),
    ]


class WorkspaceScopeRegisterRequest(StrictSchemaModel):
    """Register or advance one operator-owned Workspace scope."""

    request_id: Annotated[
        WireUUID,
        Field(description="Stable request identity for the scope mutation.", alias="requestId"),
    ]
    expected_revision: Annotated[
        UnsignedRevision,
        Field(description="Expected current scope revision.", alias="expectedRevision"),
    ]
    scope: Annotated[
        WorkspaceQueryScopeSchema,
        Field(description="Workspace, Location, and locator scope to register."),
    ]


class RegisteredWorkspaceScopeResponse(StrictSchemaModel):
    """Registered Workspace scope state returned by Orchestration."""

    workspace_id: Annotated[
        WireUUID,
        Field(description="Workspace identity.", alias="workspaceId"),
    ]
    location_id: Annotated[
        WireUUID,
        Field(description="Parent Forge Location identity.", alias="locationId"),
    ]
    location_revision: Annotated[
        PositiveInt64,
        Field(
            description="Forge Location revision captured by this scope.", alias="locationRevision"
        ),
    ]
    workspace_revision: Annotated[
        PositiveInt64,
        Field(
            description="Forge Workspace revision captured by this scope.",
            alias="workspaceRevision",
        ),
    ]
    locator: Annotated[
        str,
        Field(description="Forge locator for the registered Workspace revision."),
    ]
    active: Annotated[bool, Field(description="Whether this scope is currently active.")]
    revision: Annotated[
        UnsignedRevision,
        Field(description="Scope mutation revision."),
    ]
    generation: Annotated[
        UnsignedRevision,
        Field(description="Monotonic scope registration generation."),
    ]
    updated_at_ms: Annotated[
        UnixTimestampMs,
        Field(description="Last scope update time in Unix milliseconds.", alias="updatedAtMs"),
    ]
    replayed: Annotated[bool, Field(description="Whether this mutation reused a prior result.")]


class WorkspaceScopeQueryResponse(StrictSchemaModel):
    """Read the active scope for one Workspace, when present."""

    workspace_id: Annotated[
        WireUUID,
        Field(description="Workspace identity selected by the URL path.", alias="workspaceId"),
    ]
    scope: Annotated[
        RegisteredWorkspaceScopeResponse | None,
        Field(description="Active registered scope, or null when absent."),
    ]


class WorkspaceScopeListResponse(
    StrictRootSchemaModel[list[RegisteredWorkspaceScopeResponse]],
):
    """Preserve the source root array of active Workspace scopes."""
