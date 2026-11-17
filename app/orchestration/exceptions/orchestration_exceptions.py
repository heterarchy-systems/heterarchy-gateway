"""Backend-owned Orchestration rejection response contract."""

from typing import Annotated

from fastapi import status
from pydantic import Field

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationBackendErrorDto,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.exception import OrchestrationErrorResponse
from app.shared.types.http_types import (
    ResponseModelDefinition,
    ResponseModels,
    build_response_models,
)


class OrchestrationBackendErrorResponse(StrictSchemaModel):
    code: Annotated[str, Field(description="Backend-owned error code.", min_length=1)]
    message: Annotated[str, Field(description="Backend-owned error explanation.")]
    retryable: Annotated[bool, Field(description="Backend-owned retry safety claim.")]

    def to_inner_dto(self) -> OrchestrationBackendErrorDto:
        """Build an immutable backend rejection DTO.

        Args:
            None.
        Return:
            The backend error fields with their original values.
        """
        result = OrchestrationBackendErrorDto(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
        )
        return result


ORCHESTRATION_ERROR_RESPONSES: ResponseModels = build_response_models(
    definitions=(
        ResponseModelDefinition(
            status_code=status.HTTP_400_BAD_REQUEST,
            model=OrchestrationBackendErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_401_UNAUTHORIZED,
            model=OrchestrationBackendErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_403_FORBIDDEN,
            model=OrchestrationBackendErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_404_NOT_FOUND,
            model=OrchestrationBackendErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_409_CONFLICT,
            model=OrchestrationBackendErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            model=OrchestrationErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            model=OrchestrationBackendErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            model=OrchestrationBackendErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_502_BAD_GATEWAY,
            model=OrchestrationErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            model=OrchestrationBackendErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            model=OrchestrationErrorResponse,
        ),
    )
)
