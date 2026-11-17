"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing_extensions import TypedDict

from app.orchestration.schema.types.autonomy_types import (
    PositiveInt64,
    UnixTimestampMs,
    UnsignedRevision,
)


class WorkspaceQueryScopeDict(TypedDict, total=True, closed=True):
    """Complete camelCase scope request dictionary."""

    workspaceId: str
    locationId: str
    locationRevision: PositiveInt64
    workspaceRevision: PositiveInt64
    locator: str


class WorkspaceScopeRegisterRequestDict(TypedDict, total=True, closed=True):
    """Complete camelCase scope registration request dictionary."""

    requestId: str
    expectedRevision: UnsignedRevision
    scope: WorkspaceQueryScopeDict


class RegisteredWorkspaceScopeDict(TypedDict, total=True, closed=True):
    """Complete registered scope response dictionary."""

    workspaceId: str
    locationId: str
    locationRevision: PositiveInt64
    workspaceRevision: PositiveInt64
    locator: str
    active: bool
    revision: UnsignedRevision
    generation: UnsignedRevision
    updatedAtMs: UnixTimestampMs
    replayed: bool


class WorkspaceScopeQueryResponseDict(TypedDict, total=True, closed=True):
    """Complete scope query response dictionary with normalized absence."""

    workspaceId: str
    scope: RegisteredWorkspaceScopeDict | None
