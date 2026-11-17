"""Validate typed Orchestration responses at the final HTTP boundary."""

from uuid import UUID

from fastapi import Response, status
from pydantic import BaseModel, ValidationError

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.exceptions.orchestration_exceptions import (
    OrchestrationBackendErrorResponse,
)
from app.shared.exception import OrchestrationExcept
from app.shared.ingredient_element.gateway.upstream_reply_enums import UpstreamReplyKind


def orchestration_http_response[ResultDictT, ResponseSchema: BaseModel](
    outcome: OrchestrationOutcomeDto[ResultDictT],
    response: Response,
    response_model: type[ResponseSchema],
    *,
    workspace_id: UUID | None = None,
) -> ResponseSchema | OrchestrationBackendErrorResponse:
    """Validate the concrete contract before assigning its source HTTP status.

    Args:
        outcome: Typed status and body produced by the operation factory.
        response: FastAPI response carrying the source status.
        response_model: Concrete public result model, including root-array models.
        workspace_id: Caller workspace for a local boundary-validation failure.
    Return:
        A public Pydantic result or backend-owned rejection response.
    """
    body = outcome.to_dict()["response"]
    try:
        if outcome.body_kind is UpstreamReplyKind.ERROR:
            result: ResponseSchema | OrchestrationBackendErrorResponse = (
                OrchestrationBackendErrorResponse.model_validate(body)
            )
        else:
            result = response_model.model_validate(body)
    except (ValidationError, ValueError) as error:
        raise OrchestrationExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="orchestration_invalid_payload",
            message="Upstream orchestration returned an invalid operation response",
            retryable=False,
            workspace_id=workspace_id,
        ) from error
    response.status_code = outcome.status_code
    return result
