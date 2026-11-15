"""Public request and response schemas for starting workflows."""

from typing import Annotated

from pydantic import Field

from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStartStatus,
)
from app.shared.types.base_types import JsonObject


class StartOrchestrationRequest(StrictSchemaModel):
    """Request payload for starting an orchestration workflow."""

    workflow_name: Annotated[
        str,
        Field(description="Name of the workflow to start.", min_length=1, max_length=100),
    ]
    inputs: Annotated[JsonObject, Field(description="Input values supplied to the workflow.")]


class StartOrchestrationResponse(StrictSchemaModel):
    """Response payload returned after starting an orchestration workflow."""

    task_id: Annotated[str, Field(description="Identifier of the started task.")]
    status: Annotated[
        OrchestrationStartStatus,
        Field(description="Current state immediately after the workflow starts."),
    ]
