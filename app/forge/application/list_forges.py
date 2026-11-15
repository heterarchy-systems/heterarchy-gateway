"""Application use case for listing Forge resources."""

from app.forge.application.get_forge import parse_forge_dto
from app.forge.application.inner_dto.get_forge_inner_dto import GetForgeInnerDto
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.exception import ForgeExcept
from app.shared.filter_module.forge_filter import ForgeFilter
from app.shared.types.upstream_payload import require_object_items


class ListForgesApplication:
    """Fetch and normalize a filtered list of Forge resources."""

    def __init__(self, forge_calling: ForgeCalling) -> None:
        """Initialize the forge-list application.

        Args:
            forge_calling: Outbound Forge API caller.
        Return:
            None.
        """
        self._forge_calling = forge_calling

    async def execute(self, filters: ForgeFilter) -> list[GetForgeInnerDto]:
        """Fetch forges matching the configured filters.

        Args:
            filters: Optional forge name and creation-date criteria.
        Return:
            Normalized forge DTOs returned by the upstream API.
        """
        payload = await self._forge_calling.fetch_forges(filters.to_query_params())
        items = require_object_items(payload, service="forge", error_type=ForgeExcept)
        result = [parse_forge_dto(item) for item in items]
        return result
