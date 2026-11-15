"""Application use cases for reading Forge resources."""

from app.forge.application.inner_dto.get_forge_inner_dto import GetForgeInnerDto
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.exception import ForgeExcept
from app.shared.types.base_types import JsonObject
from app.shared.types.upstream_payload import (
    require_iso_datetime,
    require_optional_str,
    require_str,
)


def parse_forge_dto(payload: JsonObject) -> GetForgeInnerDto:
    """Normalize an upstream Forge JSON payload into a GetForgeInnerDto.

    Args:
        payload: Upstream Forge JSON object.
    Return:
        Validated GetForgeInnerDto instance.
    """
    return GetForgeInnerDto(
        id=require_str(payload, "id", service="forge", error_type=ForgeExcept),
        name=require_str(payload, "name", service="forge", error_type=ForgeExcept),
        description=require_optional_str(
            payload,
            "description",
            service="forge",
            error_type=ForgeExcept,
        ),
        created_at=require_iso_datetime(
            payload,
            "created_at",
            service="forge",
            error_type=ForgeExcept,
        ),
    )


class GetForgeApplication:
    """Fetch and normalize a single Forge resource."""

    def __init__(self, forge_calling: ForgeCalling) -> None:
        """Initialize the forge lookup application.

        Args:
            forge_calling: Outbound Forge API caller.
        Return:
            None.
        """
        self._forge_calling = forge_calling

    async def execute(self, forge_id: str) -> GetForgeInnerDto:
        """Fetch and normalize a forge.

        Args:
            forge_id: Identifier of the forge to fetch.
        Return:
            Normalized forge DTO.
        """
        payload = await self._forge_calling.fetch_forge(forge_id)
        result = parse_forge_dto(payload)
        return result
