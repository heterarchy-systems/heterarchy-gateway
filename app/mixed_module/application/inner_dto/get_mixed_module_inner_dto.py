"""Internal DTO for combined forge-orchestration views."""

from dataclasses import dataclass

from app.forge.application.inner_dto.get_forge_inner_dto import GetForgeInnerDto
from app.orchestration.application.inner_dto.get_orchestration_inner_dto import (
    GetOrchestrationInnerDto,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class GetMixedModuleInnerDto:
    """Combined normalized internal DTO for forge and task state."""

    forge: GetForgeInnerDto
    orchestration: GetOrchestrationInnerDto
