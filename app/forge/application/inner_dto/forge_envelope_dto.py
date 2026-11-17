"""Immutable wire DTOs for common Forge command envelope values."""

from dataclasses import dataclass
from typing import Literal, NotRequired
from uuid import UUID

from pydantic import JsonValue
from typing_extensions import TypedDict

from app.forge.schema.types.forge_types import Int64
from app.shared.ingredient_element.forge.forge_enums import (
    ForgeCommandOpEnum,
    ForgeErrorCodeEnum,
    ForgePrincipalKindEnum,
    ForgeReadbackKindEnum,
)


class ForgeLocatorDict(TypedDict, total=True, closed=True):
    """Serialized Source locator fields."""

    location_id: str
    expected_revision: Int64
    relative_root: str


class ForgeWorkspaceScopeDict(TypedDict, total=True, closed=True):
    """Serialized resolved Workspace scope."""

    workspace_id: str
    workspace_revision: Int64
    locator: ForgeLocatorDict


class ForgePrincipalDict(TypedDict, total=True, closed=True):
    """Serialized principal with Source-omitted absent identities."""

    kind: str
    token_id: NotRequired[str]
    grant_id: NotRequired[str]


class ForgeSessionActorDict(TypedDict, total=True, closed=True):
    """Serialized caller session, principal, and Workspace identity."""

    session_id: str
    principal: ForgePrincipalDict
    workspace_id: str


class ForgeCommandEnvelopeDict(TypedDict, total=True, closed=True):
    """Serialized versioned Forge request envelope."""

    forge_api: int
    request_id: str
    op: str
    payload: JsonValue


class ForgeSwarmWorkspaceReadbackDict(TypedDict, total=True, closed=True):
    """Readback identity for Swarm workspace operations."""

    kind: Literal[ForgeReadbackKindEnum.SWARM_WORKSPACE]
    workspace_id: UUID
    swarm_run_id: UUID
    member_id: UUID


class ForgeSwarmSettlementReadbackDict(TypedDict, total=True, closed=True):
    """Readback identity for Swarm settlement operations."""

    kind: Literal[ForgeReadbackKindEnum.SWARM_SETTLEMENT]
    workspace_id: UUID
    swarm_run_id: UUID
    settlement_id: UUID


type ForgeReadbackDict = ForgeSwarmWorkspaceReadbackDict | ForgeSwarmSettlementReadbackDict


class ForgeWireErrorDict(TypedDict, total=True, closed=True):
    """Sanitized upstream Forge failure body."""

    code: ForgeErrorCodeEnum
    message: str
    category: str
    retryable: bool
    recovery_action: str
    recovery_hint: str
    readback: ForgeReadbackDict | None


class ForgeSuccessEnvelopeDict[ResultDictT](TypedDict, total=True, closed=True):
    """Serialized successful Forge reply envelope."""

    forge_api: int
    request_id: UUID
    ok: Literal[True]
    result: ResultDictT


class ForgeFailureEnvelopeDict(TypedDict, total=True, closed=True):
    """Serialized failed Forge reply envelope."""

    forge_api: int
    request_id: UUID
    ok: Literal[False]
    error: ForgeWireErrorDict


type ForgeCommandResponseDict[ResultDictT] = (
    ForgeSuccessEnvelopeDict[ResultDictT] | ForgeFailureEnvelopeDict
)


class ForgeCommandOutcomeDict[ResultDictT](TypedDict, total=True, closed=True):
    """Validated upstream response body and status retained for the HTTP route."""

    status_code: int
    response: ForgeCommandResponseDict[ResultDictT]


type ForgeErrorReadbackDict = ForgeReadbackDict
type ForgeErrorDtoDict = ForgeWireErrorDict


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeLocatorDto:
    """Immutable Source locator value."""

    location_id: UUID
    expected_revision: Int64
    relative_root: str

    def to_dict(self) -> ForgeLocatorDict:
        """Serialize locator fields using their exact Forge wire names.

        Args:
            None.
        Return:
            Typed locator object.
        """
        result: ForgeLocatorDict = {
            "location_id": str(self.location_id),
            "expected_revision": self.expected_revision,
            "relative_root": self.relative_root,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmWorkspaceReadbackDto:
    """Immutable Swarm workspace readback identity."""

    workspace_id: UUID
    swarm_run_id: UUID
    member_id: UUID

    def to_dict(self) -> ForgeSwarmWorkspaceReadbackDict:
        """Serialize the exact Swarm workspace readback tag and identity.

        Args:
            None.
        Return:
            Typed Swarm workspace readback key.
        """
        result: ForgeSwarmWorkspaceReadbackDict = {
            "kind": ForgeReadbackKindEnum.SWARM_WORKSPACE,
            "workspace_id": self.workspace_id,
            "swarm_run_id": self.swarm_run_id,
            "member_id": self.member_id,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmSettlementReadbackDto:
    """Immutable Swarm settlement readback identity."""

    workspace_id: UUID
    swarm_run_id: UUID
    settlement_id: UUID

    def to_dict(self) -> ForgeSwarmSettlementReadbackDict:
        """Serialize the exact Swarm settlement readback tag and identity.

        Args:
            None.
        Return:
            Typed Swarm settlement readback key.
        """
        result: ForgeSwarmSettlementReadbackDict = {
            "kind": ForgeReadbackKindEnum.SWARM_SETTLEMENT,
            "workspace_id": self.workspace_id,
            "swarm_run_id": self.swarm_run_id,
            "settlement_id": self.settlement_id,
        }
        return result


type ForgeErrorReadbackDto = ForgeSwarmWorkspaceReadbackDto | ForgeSwarmSettlementReadbackDto


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeWireErrorDto:
    """Immutable sanitized failure details from Forge."""

    code: ForgeErrorCodeEnum
    message: str
    category: str
    retryable: bool
    recovery_action: str
    recovery_hint: str
    readback: ForgeErrorReadbackDto | None

    def to_dict(self) -> ForgeErrorDtoDict:
        """Serialize the complete Forge error contract.

        Args:
            None.
        Return:
            Typed Forge error details.
        """
        readback = _readback_to_dict(readback=self.readback)
        result: ForgeErrorDtoDict = {
            "code": self.code,
            "message": self.message,
            "category": self.category,
            "retryable": self.retryable,
            "recovery_action": self.recovery_action,
            "recovery_hint": self.recovery_hint,
            "readback": readback,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeWorkspaceScopeDto:
    """Immutable resolved Workspace scope DTO."""

    workspace_id: UUID
    workspace_revision: Int64
    locator: ForgeLocatorDto

    def to_dict(self) -> ForgeWorkspaceScopeDict:
        """Serialize the exact Forge scope object.

        Args:
            None.
        Return:
            Typed Workspace scope object.
        """
        result: ForgeWorkspaceScopeDict = {
            "workspace_id": str(self.workspace_id),
            "workspace_revision": self.workspace_revision,
            "locator": self.locator.to_dict(),
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgePrincipalDto:
    """Immutable principal DTO excluding absent Source option fields."""

    kind: ForgePrincipalKindEnum
    token_id: UUID | None
    grant_id: UUID | None

    def to_dict(self) -> ForgePrincipalDict:
        """Serialize principal identity with Serde's omission rules.

        Args:
            None.
        Return:
            Typed principal object.
        """
        result: ForgePrincipalDict = {"kind": self.kind.value}
        if self.token_id is not None:
            result["token_id"] = str(self.token_id)
        if self.grant_id is not None:
            result["grant_id"] = str(self.grant_id)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSessionActorDto:
    """Immutable caller identity DTO for mutating Forge operations."""

    session_id: UUID
    principal: ForgePrincipalDto
    workspace_id: UUID

    def to_dict(self) -> ForgeSessionActorDict:
        """Serialize the actor fields used by Forge's strict payload parsers.

        Args:
            None.
        Return:
            Typed session actor object.
        """
        result: ForgeSessionActorDict = {
            "session_id": str(self.session_id),
            "principal": self.principal.to_dict(),
            "workspace_id": str(self.workspace_id),
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeCommandEnvelopeDto:
    """Immutable versioned Forge request envelope."""

    forge_api: int
    request_id: UUID
    op: ForgeCommandOpEnum
    payload: JsonValue

    def to_dict(self) -> ForgeCommandEnvelopeDict:
        """Serialize a command envelope without regenerating its identity.

        Args:
            None.
        Return:
            Complete typed Forge request envelope.
        """
        result: ForgeCommandEnvelopeDict = {
            "forge_api": self.forge_api,
            "request_id": str(self.request_id),
            "op": self.op.value,
            "payload": self.payload,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeCommandSuccessEnvelopeDto[ResultDictT]:
    """Immutable success envelope around an operation-specific result DTO."""

    forge_api: int
    request_id: UUID
    result: ResultDictT

    def to_dict(self) -> ForgeSuccessEnvelopeDict[ResultDictT]:
        """Serialize the common successful Forge response envelope.

        Args:
            None.
        Return:
            Typed successful response envelope.
        """
        result: ForgeSuccessEnvelopeDict[ResultDictT] = {
            "forge_api": self.forge_api,
            "request_id": self.request_id,
            "ok": True,
            "result": self.result,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeCommandFailureEnvelopeDto:
    """Immutable failure envelope preserving Source status and request identity."""

    forge_api: int
    request_id: UUID
    error: ForgeWireErrorDto

    def to_dict(self) -> ForgeFailureEnvelopeDict:
        """Serialize the common failed Forge response envelope.

        Args:
            None.
        Return:
            Typed failed response envelope.
        """
        result: ForgeFailureEnvelopeDict = {
            "forge_api": self.forge_api,
            "request_id": self.request_id,
            "ok": False,
            "error": self.error.to_dict(),
        }
        return result


type ForgeCommandBodyDto[ResultDictT] = (
    ForgeCommandSuccessEnvelopeDto[ResultDictT] | ForgeCommandFailureEnvelopeDto
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeCommandOutcomeDto[ResultDictT]:
    """Immutable HTTP status and typed Forge response envelope."""

    status_code: int
    response: ForgeCommandBodyDto[ResultDictT]

    def to_dict(self) -> ForgeCommandOutcomeDict[ResultDictT]:
        """Serialize the status and nested response envelope for the route.

        Args:
            None.
        Return:
            Typed status and JSON response payload.
        """
        if isinstance(self.response, ForgeCommandSuccessEnvelopeDto):
            response: ForgeCommandResponseDict[ResultDictT] = self.response.to_dict()
        else:
            response = self.response.to_dict()
        result: ForgeCommandOutcomeDict[ResultDictT] = {
            "status_code": self.status_code,
            "response": response,
        }
        return result


def _readback_to_dict(
    readback: ForgeErrorReadbackDto | None,
) -> ForgeErrorReadbackDict | None:
    """Serialize a source-omitted readback identity when present."""
    if isinstance(readback, ForgeSwarmWorkspaceReadbackDto):
        result: ForgeErrorReadbackDict | None = readback.to_dict()
    elif isinstance(readback, ForgeSwarmSettlementReadbackDto):
        result = readback.to_dict()
    else:
        result = None
    return result
