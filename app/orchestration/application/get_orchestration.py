"""Application use cases for reading Orchestration tasks."""

from app.orchestration.application.inner_dto.get_orchestration_inner_dto import (
    GetOrchestrationInnerDto,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import OrchestrationExcept
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStatus,
)
from app.shared.types.base_types import JsonObject
from app.shared.types.upstream_payload import (
    require_enum,
    require_optional_object,
    require_str,
)


def parse_orchestration_dto(payload: JsonObject) -> GetOrchestrationInnerDto:
    """Normalize an upstream Orchestration task payload into GetOrchestrationInnerDto.

    Args:
        payload: Upstream Orchestration JSON object.
    Return:
        Validated GetOrchestrationInnerDto instance.
    """
    return GetOrchestrationInnerDto(
        task_id=require_str(
            payload,
            "task_id",
            service="orchestration",
            error_type=OrchestrationExcept,
        ),
        status=require_enum(
            payload,
            "status",
            OrchestrationStatus,
            service="orchestration",
            error_type=OrchestrationExcept,
        ),
        result=require_optional_object(
            payload,
            "result",
            service="orchestration",
            error_type=OrchestrationExcept,
        ),
    )


class GetOrchestrationApplication:
    """Fetch and normalize a single Orchestration task."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the task lookup application.

        Args:
            orchestration_calling: Outbound orchestration API caller.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def execute(self, task_id: str) -> GetOrchestrationInnerDto:
        """Fetch and normalize an orchestration task.

        Args:
            task_id: Identifier of the task to fetch.
        Return:
            Normalized task DTO.
        """
        payload = await self._orchestration_calling.fetch_task(task_id)
        result = parse_orchestration_dto(payload)
        return result
