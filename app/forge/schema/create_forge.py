"""Public request and response schemas for creating a forge."""

from typing import Annotated

from pydantic import Field

from app.shared.base_schema import StrictSchemaModel


class CreateForgeRequest(StrictSchemaModel):
    """Request payload for creating a forge."""

    name: Annotated[
        str,
        Field(description="Name assigned to the forge.", min_length=1, max_length=100),
    ]
    description: Annotated[str | None, Field(description="Optional forge description.")]


class CreateForgeResponse(StrictSchemaModel):
    """Response payload returned after creating a forge."""

    id: Annotated[str, Field(description="Identifier assigned to the created forge.")]
    name: Annotated[str, Field(description="Name of the created forge.")]
