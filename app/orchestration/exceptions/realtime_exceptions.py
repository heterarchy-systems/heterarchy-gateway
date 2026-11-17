"""Typed admission failures returned before an SSE response starts."""

from fastapi import status

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationBackendErrorDict,
    OrchestrationBackendErrorDto,
)
from app.orchestration.exceptions.orchestration_exceptions import (
    ORCHESTRATION_ERROR_RESPONSES,
)
from app.shared.ingredient_element.orchestration.realtime_enums import RealtimeMediaTypeEnum
from app.shared.types.http_types import (
    ContentResponseDefinition,
    ResponseModels,
    build_response_models,
)


class OrchestrationRealtimeAdmissionError(Exception):
    """Retain the source HTTP status, error body, and optional retry guidance."""

    def __init__(
        self,
        status_code: int,
        error: OrchestrationBackendErrorDto,
        retry_after: str | None,
    ) -> None:
        """Keep source admission details for the composition-root handler.

        Args:
            status_code: Original Orchestration admission status.
            error: Validated backend-owned error fields.
            retry_after: Source retry guidance, when present.
        Return:
            None.
        """
        self.status_code = status_code
        self.error = error
        self.retry_after = retry_after
        super().__init__(error.message)

    def to_dict(self) -> OrchestrationBackendErrorDict:
        """Serialize the source error body without adding Gateway fields.

        Args:
            None.
        Return:
            Typed backend-owned admission error.
        """
        result = self.error.to_dict()
        return result


REALTIME_RESPONSES: ResponseModels = {
    **ORCHESTRATION_ERROR_RESPONSES,
    **build_response_models(
        definitions=(
            ContentResponseDefinition(
                status_code=status.HTTP_200_OK,
                description="Scoped realtime event stream.",
                content={
                    RealtimeMediaTypeEnum.EVENT_STREAM.value: {"schema": {"type": "string"}},
                },
            ),
        )
    ),
}
