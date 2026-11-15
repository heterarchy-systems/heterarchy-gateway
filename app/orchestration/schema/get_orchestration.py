"""Public response schema for orchestration task lookups."""

from typing import Annotated

from pydantic import Field

from app.shared.base_schema import StrictSchemaModel, exclude_none_field
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStatus,
)
from app.shared.types.base_types import JsonObject


class GetOrchestrationResponse(StrictSchemaModel):
    """Public orchestration task representation."""

    task_id: Annotated[str, Field(description="Identifier of the workflow task.")]
    status: Annotated[OrchestrationStatus, Field(description="Current state of the workflow task.")]
    result: Annotated[
        JsonObject | None,
        exclude_none_field(),
        Field(description="Optional structured result payload when available."),
    ]
