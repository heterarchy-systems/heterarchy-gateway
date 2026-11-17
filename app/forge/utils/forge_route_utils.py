"""HTTP response mapping for typed Forge command envelopes."""

from uuid import UUID

from fastapi import Response as FastAPIResponse
from fastapi import status
from pydantic import BaseModel, ValidationError

from app.forge.application.inner_dto.forge_envelope_dto import ForgeCommandOutcomeDto
from app.forge.exceptions.forge_exceptions import ForgeFailureEnvelope
from app.shared.exception import ForgeExcept


def forge_http_response[ResultDictT, ResponseSchema: BaseModel](
    outcome: ForgeCommandOutcomeDto[ResultDictT],
    request_id: UUID,
    response: FastAPIResponse,
    success_model: type[ResponseSchema],
) -> ResponseSchema | ForgeFailureEnvelope:
    """Validate the response DTO and preserve its Source HTTP status.

    Args:
        outcome: Typed operation response DTO with the Source status.
        request_id: Caller request identity for a sanitized local 502.
        response: FastAPI response whose status is set after validation.
        success_model: Concrete success envelope for this operation.
    Return:
        Validated success or failure envelope for FastAPI serialization.
    """
    response_payload = outcome.to_dict()["response"]
    try:
        if outcome.status_code == status.HTTP_200_OK:
            response_model = success_model.model_validate(response_payload)
        else:
            response_model = ForgeFailureEnvelope.model_validate(response_payload)
    except ValidationError as error:
        raise ForgeExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="forge_invalid_payload",
            message="Gateway could not validate the Forge response DTO",
            retryable=False,
            request_id=request_id,
        ) from error
    response.status_code = outcome.status_code
    result = response_model
    return result
