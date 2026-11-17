"""Immutable DTOs and typed wire dictionaries for Workspace scopes."""

from dataclasses import dataclass
from uuid import UUID

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


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceQueryScopeDto:
    """Immutable Workspace scope command data."""

    workspace_id: UUID
    location_id: UUID
    location_revision: PositiveInt64
    workspace_revision: PositiveInt64
    locator: str

    def to_dict(self) -> WorkspaceQueryScopeDict:
        """Serialize the scope using upstream camelCase wire keys.

        Args:
            None.
        Return:
            Complete Workspace scope dictionary.
        """
        result = WorkspaceQueryScopeDict(
            workspaceId=str(self.workspace_id),
            locationId=str(self.location_id),
            locationRevision=self.location_revision,
            workspaceRevision=self.workspace_revision,
            locator=self.locator,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceScopeRegisterCommandDto:
    """Immutable scope registration command."""

    request_id: UUID
    expected_revision: UnsignedRevision
    scope: WorkspaceQueryScopeDto

    def to_dict(self) -> WorkspaceScopeRegisterRequestDict:
        """Serialize the registration command for Orchestration.

        Args:
            None.
        Return:
            Complete Workspace scope registration dictionary.
        """
        result = WorkspaceScopeRegisterRequestDict(
            requestId=str(self.request_id),
            expectedRevision=self.expected_revision,
            scope=self.scope.to_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisteredWorkspaceScopeDto:
    """Immutable registered Workspace scope projection."""

    workspace_id: UUID
    location_id: UUID
    location_revision: PositiveInt64
    workspace_revision: PositiveInt64
    locator: str
    active: bool
    revision: UnsignedRevision
    generation: UnsignedRevision
    updated_at_ms: UnixTimestampMs
    replayed: bool

    def to_dict(self) -> RegisteredWorkspaceScopeDict:
        """Serialize the registered scope response projection.

        Args:
            None.
        Return:
            Complete registered scope response dictionary.
        """
        result = RegisteredWorkspaceScopeDict(
            workspaceId=str(self.workspace_id),
            locationId=str(self.location_id),
            locationRevision=self.location_revision,
            workspaceRevision=self.workspace_revision,
            locator=self.locator,
            active=self.active,
            revision=self.revision,
            generation=self.generation,
            updatedAtMs=self.updated_at_ms,
            replayed=self.replayed,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class WorkspaceScopeQueryDto:
    """Immutable response for reading one active Workspace scope."""

    workspace_id: UUID
    scope: RegisteredWorkspaceScopeDto | None

    def to_dict(self) -> WorkspaceScopeQueryResponseDict:
        """Serialize a scope query and normalize missing scope to null.

        Args:
            None.
        Return:
            Complete Workspace scope query response dictionary.
        """
        scope = self.scope.to_dict() if self.scope is not None else None
        result = WorkspaceScopeQueryResponseDict(
            workspaceId=str(self.workspace_id),
            scope=scope,
        )
        return result
