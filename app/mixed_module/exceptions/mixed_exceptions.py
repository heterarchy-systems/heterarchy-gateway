"""Typed exceptions and response schemas for Mixed compositions."""

from typing import Annotated, Literal

from fastapi import status
from pydantic import Field

from app.forge.exceptions.forge_exceptions import ForgeFailureEnvelope
from app.mixed_module.application.inner_dto.mixed_dependency_failure_inner_dto import (
    MixedDependencyFailureDto,
)
from app.orchestration.exceptions.orchestration_exceptions import (
    OrchestrationBackendErrorResponse,
)
from app.shared.base_schema import BackendReadError, StrictSchemaModel
from app.shared.exception.forge_exception import ForgeErrorResponse
from app.shared.exception.orchestration_exception import OrchestrationErrorResponse
from app.shared.ingredient_element.gateway.mixed_enums import (
    MixedBackendEnum,
    MixedDependencyFailureTagEnum,
)
from app.shared.types.base_types import JsonObject
from app.shared.types.http_types import (
    ContentResponseDefinition,
    ResponseModel,
    ResponseModelDefinition,
    ResponseModels,
    build_response_models,
)


class MixedForgeSourceFailureSchema(StrictSchemaModel):
    """Forge source rejection, including its durable readback envelope."""

    backend: Annotated[Literal[MixedBackendEnum.FORGE], Field(description="Owning backend.")]
    kind: Annotated[
        Literal[MixedDependencyFailureTagEnum.FORGE_SOURCE],
        Field(description="Forge source failure variant."),
    ]
    status_code: Annotated[int, Field(description="Original Forge HTTP status.")]
    response: Annotated[
        ForgeFailureEnvelope,
        Field(description="Original validated Forge failure envelope."),
    ]


class MixedOrchestrationSourceFailureSchema(StrictSchemaModel):
    """Orchestration source rejection with its original status and body."""

    backend: Annotated[
        Literal[MixedBackendEnum.ORCHESTRATION], Field(description="Owning backend.")
    ]
    kind: Annotated[
        Literal[MixedDependencyFailureTagEnum.ORCHESTRATION_SOURCE],
        Field(description="Orchestration source failure variant."),
    ]
    status_code: Annotated[int, Field(description="Original Orchestration HTTP status.")]
    response: Annotated[
        OrchestrationBackendErrorResponse,
        Field(description="Original validated Orchestration failure body."),
    ]


class MixedForgeGatewayFailureSchema(StrictSchemaModel):
    """Sanitized Forge Gateway error correlated to the caller's request."""

    backend: Annotated[Literal[MixedBackendEnum.FORGE], Field(description="Owning backend.")]
    kind: Annotated[
        Literal[MixedDependencyFailureTagEnum.FORGE_GATEWAY],
        Field(description="Forge transport or boundary failure variant."),
    ]
    status_code: Annotated[int, Field(description="Gateway Forge error status.")]
    response: Annotated[
        ForgeErrorResponse,
        Field(description="Sanitized Forge error with request correlation."),
    ]


class MixedOrchestrationGatewayFailureSchema(StrictSchemaModel):
    """Sanitized Orchestration Gateway error correlated to its Workspace."""

    backend: Annotated[
        Literal[MixedBackendEnum.ORCHESTRATION], Field(description="Owning backend.")
    ]
    kind: Annotated[
        Literal[MixedDependencyFailureTagEnum.ORCHESTRATION_GATEWAY],
        Field(description="Orchestration transport or boundary failure variant."),
    ]
    status_code: Annotated[int, Field(description="Gateway Orchestration error status.")]
    response: Annotated[
        OrchestrationErrorResponse,
        Field(description="Sanitized error with Workspace correlation."),
    ]


class MixedGatewayTimeoutFailureSchema(StrictSchemaModel):
    """Gateway-owned total request deadline without backend attribution."""

    backend: Annotated[Literal[MixedBackendEnum.GATEWAY], Field(description="Owning layer.")]
    kind: Annotated[
        Literal[MixedDependencyFailureTagEnum.MIXED_GATEWAY_TIMEOUT],
        Field(description="Whole-request deadline failure."),
    ]
    status_code: Annotated[int, Field(description="Gateway request deadline status.")]
    response: Annotated[
        BackendReadError,
        Field(description="Sanitized Gateway deadline error."),
    ]


class MixedDependencyFailureResponse(StrictSchemaModel):
    """One or more typed dependency failures from an owned Mixed fanout."""

    failures: Annotated[
        list[
            Annotated[
                MixedForgeSourceFailureSchema
                | MixedOrchestrationSourceFailureSchema
                | MixedForgeGatewayFailureSchema
                | MixedOrchestrationGatewayFailureSchema
                | MixedGatewayTimeoutFailureSchema,
                Field(discriminator="kind"),
            ]
        ],
        Field(
            description="Typed failures preserving each status and original body.",
            min_length=1,
        ),
    ]


class MixedHttpDetailResponse(StrictSchemaModel):
    """FastAPI HTTPException body used for local Mixed filters and simulation."""

    detail: Annotated[str, Field(description="Request-level explanation.")]


class MixedDependencyFailureError(Exception):
    """Cancel sibling reads after a typed backend reply or transport failure."""

    def __init__(self, failure: MixedDependencyFailureDto) -> None:
        """Keep one closed failure DTO attached to its originating exception.

        Args:
            failure: Source or Gateway error returned to the caller.
        Return:
            None.
        """
        self.failure = failure
        super().__init__(failure)


class MixedRequestContextError(Exception):
    """Reject path and body scope combinations before upstream fanout."""

    def __init__(
        self,
        message: str,
        location: tuple[str, ...],
        rejected_value: str,
    ) -> None:
        """Initialize a sanitized caller-input error.

        Args:
            message: Explanation of the mismatched caller context.
            location: Public request field that failed the identity fence.
            rejected_value: Rejected value for FastAPI validation details.
        Return:
            None.
        """
        self.message = message
        self.location = location
        self.rejected_value = rejected_value
        super().__init__(message)


_FASTAPI_VALIDATION_SCHEMA: JsonObject = {
    "title": "HTTPValidationError",
    "type": "object",
    "properties": {
        "detail": {
            "title": "Detail",
            "type": "array",
            "items": {
                "title": "ValidationError",
                "type": "object",
                "properties": {
                    "loc": {
                        "title": "Location",
                        "type": "array",
                        "items": {"anyOf": [{"type": "string"}, {"type": "integer"}]},
                    },
                    "msg": {"title": "Message", "type": "string"},
                    "type": {"title": "Error Type", "type": "string"},
                    "input": {},
                    "ctx": {"title": "Context", "type": "object"},
                },
                "required": ["loc", "msg", "type"],
            },
        }
    },
}
_VALIDATION_ERROR_CONTENT: JsonObject = {
    "application/json": {
        "schema": {
            "anyOf": [
                {"$ref": "#/components/schemas/MixedDependencyFailureResponse"},
                _FASTAPI_VALIDATION_SCHEMA,
            ]
        }
    }
}


def _mixed_error_responses(*, not_found_model: ResponseModel) -> ResponseModels:
    """Build the shared HTTP error response matrix for Mixed routes.

    Args:
        not_found_model: Route-specific 404 model contract.
    Return:
        Complete status-keyed response catalog for Mixed routes.
    """
    result = build_response_models(
        definitions=(
            ResponseModelDefinition(
                status_code=status.HTTP_202_ACCEPTED,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_400_BAD_REQUEST,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_401_UNAUTHORIZED,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_403_FORBIDDEN,
                model=MixedDependencyFailureResponse | MixedHttpDetailResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_404_NOT_FOUND,
                model=not_found_model,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_409_CONFLICT,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                model=MixedDependencyFailureResponse,
            ),
            ContentResponseDefinition(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                description="Mixed source rejection or FastAPI request validation error.",
                content=_VALIDATION_ERROR_CONTENT,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_502_BAD_GATEWAY,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                model=MixedDependencyFailureResponse,
            ),
            ResponseModelDefinition(status_code="default", model=MixedDependencyFailureResponse),
        )
    )
    return result


MIXED_SWARM_OVERVIEW_RESPONSES: ResponseModels = _mixed_error_responses(
    not_found_model=MixedDependencyFailureResponse | MixedHttpDetailResponse,
)

MIXED_DAG_GOVERNANCE_RESPONSES: ResponseModels = _mixed_error_responses(
    not_found_model=MixedDependencyFailureResponse,
)
