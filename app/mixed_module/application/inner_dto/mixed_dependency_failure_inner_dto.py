"""Immutable DTOs for preserving typed Mixed dependency failures."""

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from typing_extensions import TypedDict

from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandFailureEnvelopeDto,
    ForgeFailureEnvelopeDict,
)
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationBackendErrorDict,
    OrchestrationBackendErrorDto,
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
type MixedDependencyFailureDto = (
    ForgeSourceFailureDto
    | OrchestrationSourceFailureDto
    | ForgeGatewayFailureDto
    | OrchestrationGatewayFailureDto
    | MixedGatewayTimeoutFailureDto
)


class MixedDependencyFailureResponseDict(TypedDict, total=True, closed=True):
    """Typed outer response retaining every failing dependency result."""

    failures: list[MixedDependencyFailureDict]


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSourceFailureDto:
    status_code: int
    response: ForgeCommandFailureEnvelopeDto

    def to_dict(self) -> ForgeSourceFailureDict:
        """Serialize the original Forge status and full failure envelope.

        Args:
            None.
        Return:
            Typed Forge source failure.
        """
        result = ForgeSourceFailureDict(
            backend=MixedBackendEnum.FORGE,
            kind=MixedDependencyFailureTagEnum.FORGE_SOURCE,
            status_code=self.status_code,
            response=self.response.to_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class OrchestrationSourceFailureDto:
    status_code: int
    response: OrchestrationBackendErrorDto

    def to_dict(self) -> OrchestrationSourceFailureDict:
        """Serialize the original Orchestration status and failure body.

        Args:
            None.
        Return:
            Typed Orchestration source failure.
        """
        result = OrchestrationSourceFailureDict(
            backend=MixedBackendEnum.ORCHESTRATION,
            kind=MixedDependencyFailureTagEnum.ORCHESTRATION_SOURCE,
            status_code=self.status_code,
            response=self.response.to_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeGatewayFailureDto:
    status_code: int
    code: str
    message: str
    retryable: bool
    request_id: UUID | None

    def to_dict(self) -> ForgeGatewayFailureDict:
        """Serialize a Forge Gateway error and its caller request identity.

        Args:
            None.
        Return:
            Typed Forge Gateway failure.
        """
        response = ForgeGatewayErrorDict(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            request_id=self.request_id,
        )
        result = ForgeGatewayFailureDict(
            backend=MixedBackendEnum.FORGE,
            kind=MixedDependencyFailureTagEnum.FORGE_GATEWAY,
            status_code=self.status_code,
            response=response,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class OrchestrationGatewayFailureDto:
    status_code: int
    code: str
    message: str
    retryable: bool
    workspace_id: UUID | None

    def to_dict(self) -> OrchestrationGatewayFailureDict:
        """Serialize an Orchestration Gateway error and Workspace identity.

        Args:
            None.
        Return:
            Typed Orchestration Gateway failure.
        """
        response = OrchestrationGatewayErrorDict(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            workspace_id=self.workspace_id,
        )
        result = OrchestrationGatewayFailureDict(
            backend=MixedBackendEnum.ORCHESTRATION,
            kind=MixedDependencyFailureTagEnum.ORCHESTRATION_GATEWAY,
            status_code=self.status_code,
            response=response,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class MixedGatewayTimeoutFailureDto:
    status_code: int
    code: str
    message: str
    retryable: bool

    def to_dict(self) -> MixedGatewayTimeoutFailureDict:
        """Serialize the request deadline without naming either backend.

        Args:
            None.
        Return:
            Typed Gateway deadline failure.
        """
        response = MixedGatewayErrorDict(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
        )
        result = MixedGatewayTimeoutFailureDict(
            backend=MixedBackendEnum.GATEWAY,
            kind=MixedDependencyFailureTagEnum.MIXED_GATEWAY_TIMEOUT,
            status_code=self.status_code,
            response=response,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class MixedDependencyFailureSetDto:
    status_code: int
    failures: tuple[MixedDependencyFailureDto, ...]

    def to_dict(self) -> MixedDependencyFailureResponseDict:
        """Serialize every typed failure captured by the owned fanout.

        Args:
            None.
        Return:
            Typed Mixed dependency failure response.
        """
        result = MixedDependencyFailureResponseDict(
            failures=[failure.to_dict() for failure in self.failures]
        )
        return result
