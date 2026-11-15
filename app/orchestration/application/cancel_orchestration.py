"""Application use case for cancelling Orchestration tasks."""

from app.orchestration.application.inner_dto.cancel_orchestration_inner_dto import (
    CancelOrchestrationInnerDto,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import OrchestrationExcept
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationCancelStatus,
)
from app.shared.types.upstream_payload import require_enum, require_str


class CancelOrchestrationApplication:
    """Cancel an Orchestration task via the upstream API."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the task cancellation application.

        Args:
            orchestration_calling: Outbound orchestration API caller.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def execute(self, task_id: str) -> CancelOrchestrationInnerDto:
        """Cancel and normalize an orchestration task.

        Args:
            task_id: Identifier of the task to cancel.
        Return:
            Normalized cancellation DTO.
        """
        payload = await self._orchestration_calling.cancel_task(task_id)
        result = CancelOrchestrationInnerDto(
            task_id=require_str(
                payload,
                "task_id",
                service="orchestration",
                error_type=OrchestrationExcept,
            ),
            status=require_enum(
                payload,
                "status",
                OrchestrationCancelStatus,
                service="orchestration",
                error_type=OrchestrationExcept,
            ),
        )
        return result
