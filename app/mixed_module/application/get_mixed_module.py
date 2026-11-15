"""Application composition use case combining Forge and Orchestration reads."""

import asyncio

from app.forge.application.get_forge import GetForgeApplication
from app.mixed_module.application.inner_dto.get_mixed_module_inner_dto import (
    GetMixedModuleInnerDto,
)
from app.orchestration.application.get_orchestration import GetOrchestrationApplication


class GetMixedModuleApplication:
    """Fetch Forge and Orchestration resources concurrently and combine them."""

    def __init__(
        self,
        forge_application: GetForgeApplication,
        orchestration_application: GetOrchestrationApplication,
    ) -> None:
        """Initialize the combined module application.

        Args:
            forge_application: Application that fetches forge data.
            orchestration_application: Application that fetches task data.
        Return:
            None.
        """
        self._forge_application = forge_application
        self._orchestration_application = orchestration_application

    async def execute(self, forge_id: str, task_id: str) -> GetMixedModuleInnerDto:
        """Fetch forge and orchestration data concurrently.

        Args:
            forge_id: Identifier of the forge.
            task_id: Identifier of the orchestration task.
        Return:
            Combined forge and orchestration DTO.
        """
        forge, orchestration = await asyncio.gather(
            self._forge_application.execute(forge_id),
            self._orchestration_application.execute(task_id),
        )
        result = GetMixedModuleInnerDto(forge=forge, orchestration=orchestration)
        return result
