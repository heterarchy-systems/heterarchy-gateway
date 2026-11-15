"""Internal DTO for fetched orchestration tasks."""

from dataclasses import dataclass

from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStatus,
)
from app.shared.types.base_types import JsonObject


@dataclass(frozen=True, slots=True, kw_only=True)
class GetOrchestrationInnerDto:
    """Normalized internal orchestration task representation."""

    task_id: str
    status: OrchestrationStatus
    result: JsonObject | None
