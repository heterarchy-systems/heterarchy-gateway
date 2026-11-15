"""Internal DTO for cancelled orchestration tasks."""

from dataclasses import dataclass

from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationCancelStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CancelOrchestrationInnerDto:
    """Normalized internal result for cancelling an orchestration task."""

    task_id: str
    status: OrchestrationCancelStatus
