"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing import Literal
from uuid import UUID

from typing_extensions import TypedDict

from app.forge.application.inner_dto.types.forge_envelope_types import (
    ForgeFailureEnvelopeDict,
)
from app.orchestration.application.inner_dto.types.orchestration_outcome_types import (
    OrchestrationBackendErrorDict,
)
from app.shared.ingredient_element.gateway.mixed_enums import (
    MixedBackendEnum,
    MixedDependencyFailureTagEnum,
)


class ForgeGatewayErrorDict(TypedDict, total=True, closed=True):
    """Sanitized Forge error correlated to the request identifier."""

    code: str
    message: str
    retryable: bool
    request_id: UUID | None


class OrchestrationGatewayErrorDict(TypedDict, total=True, closed=True):
    """Sanitized Orchestration error correlated to the Workspace."""

    code: str
    message: str
    retryable: bool
    workspace_id: UUID | None


class MixedGatewayErrorDict(TypedDict, total=True, closed=True):
    """Sanitized Gateway-owned request deadline error."""

    code: str
    message: str
    retryable: bool


class ForgeSourceFailureDict(TypedDict, total=True, closed=True):
    """Original typed Forge rejection and source status."""

    backend: Literal[MixedBackendEnum.FORGE]
    kind: Literal[MixedDependencyFailureTagEnum.FORGE_SOURCE]
    status_code: int
    response: ForgeFailureEnvelopeDict


class OrchestrationSourceFailureDict(TypedDict, total=True, closed=True):
    """Original typed Orchestration rejection and source status."""

    backend: Literal[MixedBackendEnum.ORCHESTRATION]
    kind: Literal[MixedDependencyFailureTagEnum.ORCHESTRATION_SOURCE]
    status_code: int
    response: OrchestrationBackendErrorDict


class ForgeGatewayFailureDict(TypedDict, total=True, closed=True):
    """Sanitized Forge transport or boundary error."""

    backend: Literal[MixedBackendEnum.FORGE]
    kind: Literal[MixedDependencyFailureTagEnum.FORGE_GATEWAY]
    status_code: int
    response: ForgeGatewayErrorDict


class OrchestrationGatewayFailureDict(TypedDict, total=True, closed=True):
    """Sanitized Orchestration transport or boundary error."""

    backend: Literal[MixedBackendEnum.ORCHESTRATION]
    kind: Literal[MixedDependencyFailureTagEnum.ORCHESTRATION_GATEWAY]
    status_code: int
    response: OrchestrationGatewayErrorDict


class MixedGatewayTimeoutFailureDict(TypedDict, total=True, closed=True):
    """Gateway-owned total deadline failure without backend attribution."""

    backend: Literal[MixedBackendEnum.GATEWAY]
    kind: Literal[MixedDependencyFailureTagEnum.MIXED_GATEWAY_TIMEOUT]
    status_code: int
    response: MixedGatewayErrorDict


type MixedDependencyFailureDict = (
    ForgeSourceFailureDict
    | OrchestrationSourceFailureDict
    | ForgeGatewayFailureDict
    | OrchestrationGatewayFailureDict
    | MixedGatewayTimeoutFailureDict
)


class MixedDependencyFailureResponseDict(TypedDict, total=True, closed=True):
    """Typed outer response retaining every failing dependency result."""

    failures: list[MixedDependencyFailureDict]
