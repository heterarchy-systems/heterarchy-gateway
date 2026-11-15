"""Public request and response schemas for updating a forge."""

from typing import Annotated

from pydantic import Field

from app.shared.base_schema import StrictSchemaModel


class UpdateForgeRequest(StrictSchemaModel):
    """Partial update payload for an existing forge."""

    name: Annotated[
        str | None,
        Field(description="Replacement forge name.", min_length=1, max_length=100),
    ] = None
    description: Annotated[str | None, Field(description="Replacement forge description.")] = None


class UpdateForgeResponse(StrictSchemaModel):
    """Response payload returned after updating a forge."""

    id: Annotated[str, Field(description="Identifier of the updated forge.")]
    updated: Annotated[bool, Field(description="Whether the forge was updated.")]
