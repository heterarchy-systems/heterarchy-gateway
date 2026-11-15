"""Application use cases for mutating Forge resources."""

from app.forge.application.inner_dto.get_forge_inner_dto import (
    CreateForgeInnerDto,
    DeleteForgeInnerDto,
    UpdateForgeInnerDto,
)
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.exception import ForgeExcept
from app.shared.types.base_types import JsonObject
from app.shared.types.upstream_payload import require_bool, require_str


class CreateForgeApplication:
    """Create a Forge resource via the upstream API."""

    def __init__(self, forge_calling: ForgeCalling) -> None:
        """Initialize the forge creation application.

        Args:
            forge_calling: Outbound Forge API caller.
        Return:
            None.
        """
        self._forge_calling = forge_calling

    async def execute(self, name: str, description: str | None) -> CreateForgeInnerDto:
        """Create a forge resource upstream.

        Args:
            name: Forge name to create.
            description: Optional forge description.
        Return:
            Normalized creation DTO.
        """
        payload = await self._forge_calling.create_forge(
            {"name": name, "description": description},
        )
        result = CreateForgeInnerDto(
            id=require_str(payload, "id", service="forge", error_type=ForgeExcept),
            name=require_str(payload, "name", service="forge", error_type=ForgeExcept),
        )
        return result


class UpdateForgeApplication:
    """Update an existing Forge resource via the upstream API."""

    def __init__(self, forge_calling: ForgeCalling) -> None:
        """Initialize the forge update application.

        Args:
            forge_calling: Outbound Forge API caller.
        Return:
            None.
        """
        self._forge_calling = forge_calling

    async def execute(self, forge_id: str, patch: JsonObject) -> UpdateForgeInnerDto:
        """Apply partial updates to an upstream forge resource.

        Args:
            forge_id: Identifier of the forge to update.
            patch: JSON object with explicit updated fields.
        Return:
            Normalized update DTO.
        """
        payload = await self._forge_calling.update_forge(forge_id, patch)
        result = UpdateForgeInnerDto(
            id=require_str(payload, "id", service="forge", error_type=ForgeExcept),
            updated=require_bool(payload, "updated", service="forge", error_type=ForgeExcept),
        )
        return result


class DeleteForgeApplication:
    """Delete an existing Forge resource via the upstream API."""

    def __init__(self, forge_calling: ForgeCalling) -> None:
        """Initialize the forge deletion application.

        Args:
            forge_calling: Outbound Forge API caller.
        Return:
            None.
        """
        self._forge_calling = forge_calling

    async def execute(self, forge_id: str) -> DeleteForgeInnerDto:
        """Delete an upstream forge resource.

        Args:
            forge_id: Identifier of the forge to delete.
        Return:
            Normalized deletion DTO.
        """
        payload = await self._forge_calling.delete_forge(forge_id)
        result = DeleteForgeInnerDto(
            id=require_str(payload, "id", service="forge", error_type=ForgeExcept),
            deleted=require_bool(payload, "deleted", service="forge", error_type=ForgeExcept),
        )
        return result
