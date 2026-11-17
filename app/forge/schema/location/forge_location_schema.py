"""Strict forge location schema contracts."""

from typing import Annotated, Literal

from pydantic import Field

from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeCommandRequest,
    ForgeSuccessEnvelope,
)
from app.forge.schema.types.forge_types import ForgeUUID, Int64, LocationState
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum


class ForgeLocationListPayload(StrictSchemaModel):
    """The location.list command has an empty, closed payload."""


class ForgeLocationEntry(StrictSchemaModel):
    """One registered Forge Location."""

    location_id: Annotated[ForgeUUID, Field(description="Registered Location identity.")]
    display_name: Annotated[str, Field(description="Display name of the Location.")]
    revision: Annotated[Int64, Field(description="Current Location revision.")]
    state: Annotated[LocationState, Field(description="Location lifecycle state.")]


class ForgeLocationListResult(StrictSchemaModel):
    """Registered Location collection returned by location.list."""

    entries: Annotated[list[ForgeLocationEntry], Field(description="Registered Locations.")]


class ForgeLocationListRequest(ForgeCommandRequest[ForgeLocationListPayload]):
    """Versioned location.list command request."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.LOCATION_LIST],
        Field(description="This route executes location.list."),
    ]


class ForgeLocationListResponse(ForgeSuccessEnvelope[ForgeLocationListResult]):
    """Successful location.list response envelope."""
