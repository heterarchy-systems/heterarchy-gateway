"""Public request and response schemas for cancelling workflows."""

from typing import Annotated

from pydantic import Field

from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationCancelStatus,
)


class CancelOrchestrationRequest(StrictSchemaModel):
    """Request payload identifying an orchestration task to cancel."""

    task_id: Annotated[str, Field(description="Identifier of the task to cancel.", min_length=1)]


class CancelOrchestrationResponse(StrictSchemaModel):
    """Response payload returned after cancelling an orchestration task."""

    task_id: Annotated[str, Field(description="Identifier of the cancelled task.")]
    status: Annotated[
        OrchestrationCancelStatus,
        Field(description="Final state of the task after cancellation."),
    ]
