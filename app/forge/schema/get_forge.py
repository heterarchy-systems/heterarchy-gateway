"""Public response schema for fetching forge resources."""

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.shared.base_schema import StrictSchemaModel


class GetForgeResponse(StrictSchemaModel):
    """Public forge resource representation."""

    id: Annotated[str, Field(description="Identifier of the forge.")]
    name: Annotated[str, Field(description="Name of the forge.")]
    description: Annotated[str | None, Field(description="Optional forge description.")]
    created_at: Annotated[datetime, Field(description="Time when the forge was created.")]
