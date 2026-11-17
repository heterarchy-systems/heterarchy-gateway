"""Strict forge activity schema contracts."""

from typing import Annotated, Literal

from pydantic import Field

from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeCommandRequest,
    ForgeSuccessEnvelope,
)
from app.forge.schema.types.forge_types import (
    ActivityLiveness,
    ActivityState,
    ForgeUUID,
    Int64,
    UInt32,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum


class ForgeActivityListPayload(StrictSchemaModel):
    """Strict payload for a bounded Activity projection query."""

    locator: Annotated[str, Field(description="Canonical Source workspace locator.")]
    workspace_id: Annotated[ForgeUUID, Field(description="Expected Workspace identity.")]
    workspace_revision: Annotated[Int64, Field(description="Expected Workspace revision.")]
    limit: Annotated[UInt32, Field(description="Maximum number of Activities to return.")]


class ForgeActivityScope(StrictSchemaModel):
    """Validated Workspace identity and locator echoed by Activity projection."""

    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    workspace_revision: Annotated[Int64, Field(description="Workspace revision.")]
    locator: Annotated[str, Field(description="Canonical Source workspace locator.")]


class ForgeActivityProjection(StrictSchemaModel):
    """One durable Activity projection and its current lease observation."""

    activity_id: Annotated[ForgeUUID, Field(description="Activity identity.")]
    workspace_id: Annotated[ForgeUUID, Field(description="Owning Workspace identity.")]
    state: Annotated[ActivityState, Field(description="Durable Activity state.")]
    liveness: Annotated[ActivityLiveness, Field(description="Observed lease liveness.")]
    revision: Annotated[Int64, Field(description="Activity revision.")]
    created_at_ms: Annotated[Int64, Field(description="Creation time in Unix milliseconds.")]
    updated_at_ms: Annotated[Int64, Field(description="Update time in Unix milliseconds.")]
    lease_owner_id: Annotated[
        ForgeUUID | None,
        Field(description="Lease owner identity, explicitly null when unleased."),
    ]
    lease_until_ms: Annotated[
        Int64 | None,
        Field(description="Lease deadline, explicitly null when unleased."),
    ]
    lease_revision: Annotated[Int64, Field(description="Activity lease revision.")]


class ForgeActivityListResult(StrictSchemaModel):
    """Activity projection collection with its exact Workspace scope."""

    scope: Annotated[ForgeActivityScope, Field(description="Resolved projection scope.")]
    activities: Annotated[list[ForgeActivityProjection], Field(description="Activity projections.")]


class ForgeActivityListRequest(ForgeCommandRequest[ForgeActivityListPayload]):
    """Versioned activity.list command request."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.ACTIVITY_LIST],
        Field(description="This route executes activity.list."),
    ]


class ForgeActivityListResponse(ForgeSuccessEnvelope[ForgeActivityListResult]):
    """Successful activity.list response envelope."""
