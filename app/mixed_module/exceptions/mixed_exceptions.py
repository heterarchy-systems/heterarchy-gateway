"""Typed exceptions and response schemas for Mixed compositions."""

from typing import Annotated, Literal

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
