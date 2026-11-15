"""Public response schema for deleting a forge."""

from typing import Annotated

from pydantic import Field

from app.shared.base_schema import StrictSchemaModel


class DeleteForgeResponse(StrictSchemaModel):
    """Response payload returned after deleting a forge."""

    id: Annotated[str, Field(description="Identifier of the deleted forge.")]
    deleted: Annotated[bool, Field(description="Whether the forge was deleted.")]
