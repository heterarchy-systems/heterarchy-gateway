"""Public response schema for combined forge-orchestration views."""

from typing import Annotated

from pydantic import Field

from app.forge.schema.get_forge import GetForgeResponse
from app.orchestration.schema.get_orchestration import GetOrchestrationResponse
from app.shared.base_schema import StrictSchemaModel


class GetMixedModuleResponse(StrictSchemaModel):
    """Combined forge and orchestration public response payload."""

    forge: Annotated[GetForgeResponse, Field(description="Forge associated with the workflow.")]
    orchestration: Annotated[
        GetOrchestrationResponse,
        Field(description="Current workflow task details."),
    ]
