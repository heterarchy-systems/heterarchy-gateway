"""Internal DTO for started orchestration tasks."""

from dataclasses import dataclass

from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStartStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class StartOrchestrationInnerDto:
    """Normalized internal result for starting an orchestration workflow."""

    task_id: str
    status: OrchestrationStartStatus
