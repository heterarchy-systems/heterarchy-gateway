"""Application use case for listing Orchestration tasks."""

from app.orchestration.application.get_orchestration import parse_orchestration_dto
from app.orchestration.application.inner_dto.get_orchestration_inner_dto import (
    GetOrchestrationInnerDto,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import OrchestrationExcept
from app.shared.filter_module.orchestration_filter import OrchestrationFilter
from app.shared.types.upstream_payload import require_object_items


class ListOrchestrationsApplication:
    """Fetch and normalize a filtered list of Orchestration tasks."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the orchestration-list application.

        Args:
            orchestration_calling: Outbound orchestration API caller.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def execute(self, filters: OrchestrationFilter) -> list[GetOrchestrationInnerDto]:
        """Fetch orchestrations matching the configured criteria.

        Args:
            filters: Optional workflow name, status, and date criteria.
        Return:
            Normalized task DTOs returned by the upstream API.
        """
        payload = await self._orchestration_calling.fetch_tasks(filters.to_query_params())
        items = require_object_items(
            payload,
            service="orchestration",
            error_type=OrchestrationExcept,
        )
        result = [parse_orchestration_dto(item) for item in items]
        return result
