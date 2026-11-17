"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing import Literal, NotRequired
from uuid import UUID

from pydantic import JsonValue
from typing_extensions import TypedDict

from app.forge.schema.types.forge_types import Int64
from app.shared.ingredient_element.forge.forge_enums import (
    ForgeErrorCodeEnum,
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
