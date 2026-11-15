"""Application use case for starting Orchestration workflows."""

from app.orchestration.application.inner_dto.start_orchestration_inner_dto import (
    StartOrchestrationInnerDto,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import OrchestrationExcept
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStartStatus,
)
from app.shared.types.base_types import JsonObject
from app.shared.types.upstream_payload import require_enum, require_str


class StartOrchestrationApplication:
    """Start an Orchestration workflow via the upstream API."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the workflow start application.

        Args:
            orchestration_calling: Outbound orchestration API caller.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def execute(
        self,
        workflow_name: str,
        inputs: JsonObject,
    ) -> StartOrchestrationInnerDto:
        """Start a workflow and normalize its response.

        Args:
            workflow_name: Name of the workflow to start.
            inputs: JSON input object for the workflow.
        Return:
            Normalized workflow-start DTO.
        """
        payload = await self._orchestration_calling.start_workflow(workflow_name, inputs)
        result = StartOrchestrationInnerDto(
            task_id=require_str(
                payload,
                "task_id",
                service="orchestration",
                error_type=OrchestrationExcept,
            ),
            status=require_enum(
                payload,
                "status",
                OrchestrationStartStatus,
                service="orchestration",
                error_type=OrchestrationExcept,
            ),
        )
        return result
