"""Pydantic filter schema for combined forge-task resources."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Annotated

from pydantic import Field

from app.shared.filter_module.base_filter import BaseDateFilter
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStatus,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class _MixedFilterTarget:
    forge_name: str
    task_status: OrchestrationStatus


_STRING_PREDICATES: dict[str, Callable[[str, _MixedFilterTarget], bool]] = {
    "forge_name": lambda criterion, target: criterion.casefold() in target.forge_name.casefold(),
    "task_status": lambda criterion, target: criterion == target.task_status.value,
}


class MixedModuleFilter(BaseDateFilter):
    """Represent optional criteria for the combined forge-task resource."""

    forge_name: Annotated[
        str | None,
        Field(description="Optional forge name to match.", max_length=100),
    ] = None
    task_status: Annotated[
        OrchestrationStatus | None,
        Field(description="Optional orchestration status to match."),
    ] = None

    def matches(self, forge_name: str, task_status: OrchestrationStatus, created_at: date) -> bool:
        """Return whether a combined resource matches all configured criteria.

        Args:
            forge_name: Name on the combined forge resource.
            task_status: Status on the combined orchestration resource.
            created_at: Forge creation date on the combined resource.
        Return:
            Whether the combined resource matches every configured criterion.
        """
        target = _MixedFilterTarget(forge_name=forge_name, task_status=task_status)
        active_criteria: dict[str, str] = {
            key: str(value)
            for key, value in self.model_dump(exclude_none=True).items()
            if key in _STRING_PREDICATES
        }
        fields_match = all(
            _STRING_PREDICATES[key](value, target) for key, value in active_criteria.items()
        )
        date_match = self.matches_created_date(created_at)
        result = fields_match and date_match
        return result
