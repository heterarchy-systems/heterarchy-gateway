"""Immutable DTO mappings for Forge Location, Workspace, and Activity commands."""

from dataclasses import dataclass
from uuid import UUID

from app.forge.application.inner_dto.types.forge_workspace_types import (
    ForgeActivityListPayloadDict,
    ForgeActivityListResultDict,
    ForgeActivityProjectionDict,
    ForgeActivityScopeDict,
    ForgeLocationEntryDict,
    ForgeLocationListPayloadDict,
    ForgeLocationListResultDict,
    ForgeWorkspaceEntryDict,
    ForgeWorkspaceListPayloadDict,
    ForgeWorkspaceListResultDict,
)
from app.forge.schema.activity.forge_activity_schema import (
    ForgeActivityListPayload,
    ForgeActivityListResult,
    ForgeActivityProjection,
    ForgeActivityScope,
)
from app.forge.schema.location.forge_location_schema import (
    ForgeLocationEntry,
    ForgeLocationListResult,
)
from app.forge.schema.types.forge_types import Int64, UInt32
from app.forge.schema.workspace.forge_workspace_schema import (
    ForgeWorkspaceEntry,
    ForgeWorkspaceListPayload,
    ForgeWorkspaceListResult,
)
from app.shared.ingredient_element.forge.forge_enums import (
    ActivityLivenessEnum,
    ActivityStateEnum,
    LocationStateEnum,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeLocationListCommandDto:
    """Immutable empty command payload for location.list."""

    def to_dict(self) -> ForgeLocationListPayloadDict:
        """Serialize the empty strict Source payload.

        Args:
            None.
        Return:
            Empty typed location.list payload.
        """
        result: ForgeLocationListPayloadDict = ForgeLocationListPayloadDict()
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeWorkspaceListCommandDto:
    """Immutable command payload for workspace.list."""

    location_id: UUID
    expected_revision: Int64

    @classmethod
    def from_payload(cls, payload: ForgeWorkspaceListPayload) -> ForgeWorkspaceListCommandDto:
        """Build a Workspace list command from its validated public payload.

        Args:
            payload: Strict workspace.list operation payload.
        Return:
            Immutable workspace.list command DTO.
        """
        result = cls(
            location_id=payload.location_id,
            expected_revision=payload.expected_revision,
        )
        return result

    def to_dict(self) -> ForgeWorkspaceListPayloadDict:
        """Serialize the exact workspace.list Source payload.

        Args:
            None.
        Return:
            Typed workspace.list operation payload.
        """
        result: ForgeWorkspaceListPayloadDict = ForgeWorkspaceListPayloadDict(
            location_id=str(self.location_id),
            expected_revision=self.expected_revision,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeActivityListCommandDto:
    """Immutable command payload for activity.list."""

    locator: str
    workspace_id: UUID
    workspace_revision: Int64
    limit: UInt32

    @classmethod
    def from_payload(cls, payload: ForgeActivityListPayload) -> ForgeActivityListCommandDto:
        """Build an Activity list command from its validated public payload.

        Args:
            payload: Strict activity.list operation payload.
        Return:
            Immutable activity.list command DTO.
        """
        result = cls(
            locator=payload.locator,
            workspace_id=payload.workspace_id,
            workspace_revision=payload.workspace_revision,
            limit=payload.limit,
        )
        return result

    def to_dict(self) -> ForgeActivityListPayloadDict:
        """Serialize the exact activity.list Source payload.

        Args:
            None.
        Return:
            Typed activity.list operation payload.
        """
        result: ForgeActivityListPayloadDict = ForgeActivityListPayloadDict(
            locator=self.locator,
            workspace_id=str(self.workspace_id),
            workspace_revision=self.workspace_revision,
            limit=self.limit,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeLocationEntryDto:
    """Immutable registered Location result."""

    location_id: UUID
    display_name: str
    revision: Int64
    state: LocationStateEnum

    @classmethod
    def from_schema(cls, entry: ForgeLocationEntry) -> ForgeLocationEntryDto:
        """Convert a validated Location result to its immutable DTO.

        Args:
            entry: Validated Forge Location entry.
        Return:
            Immutable Location result DTO.
        """
        result = cls(
            location_id=entry.location_id,
            display_name=entry.display_name,
            revision=entry.revision,
            state=LocationStateEnum(entry.state),
        )
        return result

    def to_dict(self) -> ForgeLocationEntryDict:
        """Serialize the exact Location result fields.

        Args:
            None.
        Return:
            Typed Location result object.
        """
        result: ForgeLocationEntryDict = ForgeLocationEntryDict(
            location_id=self.location_id,
            display_name=self.display_name,
            revision=self.revision,
            state=self.state,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeLocationListResultDto:
    """Immutable collection returned by location.list."""

    entries: tuple[ForgeLocationEntryDto, ...]

    @classmethod
    def from_schema(cls, result_schema: ForgeLocationListResult) -> ForgeLocationListResultDto:
        """Convert the validated Location result and each nested entry.

        Args:
            result_schema: Validated location.list result payload.
        Return:
            Immutable Location collection DTO.
        """
        entries = tuple(
            ForgeLocationEntryDto.from_schema(entry=entry) for entry in result_schema.entries
        )
        result = cls(entries=entries)
        return result

    def to_dict(self) -> ForgeLocationListResultDict:
        """Serialize the typed location.list result payload.

        Args:
            None.
        Return:
            Typed Location list result.
        """
        result: ForgeLocationListResultDict = ForgeLocationListResultDict(
            entries=[entry.to_dict() for entry in self.entries]
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeWorkspaceEntryDto:
    """Immutable Workspace entry returned by workspace.list."""

    locator: str
    display_name: str
    workspace_id: UUID
    workspace_revision: Int64

    @classmethod
    def from_schema(cls, entry: ForgeWorkspaceEntry) -> ForgeWorkspaceEntryDto:
        """Convert a validated Workspace entry to its immutable DTO.

        Args:
            entry: Validated Forge Workspace entry.
        Return:
            Immutable Workspace entry DTO.
        """
        result = cls(
            locator=entry.locator,
            display_name=entry.display_name,
            workspace_id=entry.workspace_id,
            workspace_revision=entry.workspace_revision,
        )
        return result

    def to_dict(self) -> ForgeWorkspaceEntryDict:
        """Serialize the exact Workspace entry fields.

        Args:
            None.
        Return:
            Typed Workspace entry object.
        """
        result: ForgeWorkspaceEntryDict = ForgeWorkspaceEntryDict(
            locator=self.locator,
            display_name=self.display_name,
            workspace_id=self.workspace_id,
            workspace_revision=self.workspace_revision,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeWorkspaceListResultDto:
    """Immutable collection returned by workspace.list."""

    entries: tuple[ForgeWorkspaceEntryDto, ...]

    @classmethod
    def from_schema(cls, result_schema: ForgeWorkspaceListResult) -> ForgeWorkspaceListResultDto:
        """Convert the validated Workspace result and each nested entry.

        Args:
            result_schema: Validated workspace.list result payload.
        Return:
            Immutable Workspace collection DTO.
        """
        entries = tuple(
            ForgeWorkspaceEntryDto.from_schema(entry=entry) for entry in result_schema.entries
        )
        result = cls(entries=entries)
        return result

    def to_dict(self) -> ForgeWorkspaceListResultDict:
        """Serialize the typed workspace.list result payload.

        Args:
            None.
        Return:
            Typed Workspace list result.
        """
        result: ForgeWorkspaceListResultDict = ForgeWorkspaceListResultDict(
            entries=[entry.to_dict() for entry in self.entries],
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeActivityScopeDto:
    """Immutable Workspace scope echoed by activity.list."""

    workspace_id: UUID
    workspace_revision: Int64
    locator: str

    @classmethod
    def from_schema(cls, scope: ForgeActivityScope) -> ForgeActivityScopeDto:
        """Convert the validated Activity scope to an immutable DTO.

        Args:
            scope: Validated Activity projection scope.
        Return:
            Immutable Activity scope DTO.
        """
        result = cls(
            workspace_id=scope.workspace_id,
            workspace_revision=scope.workspace_revision,
            locator=scope.locator,
        )
        return result

    def to_dict(self) -> ForgeActivityScopeDict:
        """Serialize the Activity scope echo.

        Args:
            None.
        Return:
            Typed Activity scope object.
        """
        result: ForgeActivityScopeDict = ForgeActivityScopeDict(
            workspace_id=self.workspace_id,
            workspace_revision=self.workspace_revision,
            locator=self.locator,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeActivityProjectionDto:
    """Immutable durable Activity projection and lease observation."""

    activity_id: UUID
    workspace_id: UUID
    state: ActivityStateEnum
    liveness: ActivityLivenessEnum
    revision: Int64
    created_at_ms: Int64
    updated_at_ms: Int64
    lease_owner_id: UUID | None
    lease_until_ms: Int64 | None
    lease_revision: Int64

    @classmethod
    def from_schema(cls, activity: ForgeActivityProjection) -> ForgeActivityProjectionDto:
        """Convert a validated Activity projection to its immutable DTO.

        Args:
            activity: Validated Forge Activity projection.
        Return:
            Immutable Activity projection DTO.
        """
        result = cls(
            activity_id=activity.activity_id,
            workspace_id=activity.workspace_id,
            state=ActivityStateEnum(activity.state),
            liveness=ActivityLivenessEnum(activity.liveness),
            revision=activity.revision,
            created_at_ms=activity.created_at_ms,
            updated_at_ms=activity.updated_at_ms,
            lease_owner_id=activity.lease_owner_id,
            lease_until_ms=activity.lease_until_ms,
            lease_revision=activity.lease_revision,
        )
        return result

    def to_dict(self) -> ForgeActivityProjectionDict:
        """Serialize Activity projection with explicit nullable lease fields.

        Args:
            None.
        Return:
            Typed Activity projection object.
        """
        result: ForgeActivityProjectionDict = ForgeActivityProjectionDict(
            activity_id=self.activity_id,
            workspace_id=self.workspace_id,
            state=self.state,
            liveness=self.liveness,
            revision=self.revision,
            created_at_ms=self.created_at_ms,
            updated_at_ms=self.updated_at_ms,
            lease_owner_id=self.lease_owner_id,
            lease_until_ms=self.lease_until_ms,
            lease_revision=self.lease_revision,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeActivityListResultDto:
    """Immutable result returned by activity.list."""

    scope: ForgeActivityScopeDto
    activities: tuple[ForgeActivityProjectionDto, ...]

    @classmethod
    def from_schema(cls, result_schema: ForgeActivityListResult) -> ForgeActivityListResultDto:
        """Convert a validated Activity result and its nested projections.

        Args:
            result_schema: Validated activity.list result payload.
        Return:
            Immutable Activity list result DTO.
        """
        scope = ForgeActivityScopeDto.from_schema(scope=result_schema.scope)
        activities = tuple(
            ForgeActivityProjectionDto.from_schema(activity=activity)
            for activity in result_schema.activities
        )
        result = cls(scope=scope, activities=activities)
        return result

    def to_dict(self) -> ForgeActivityListResultDict:
        """Serialize the typed activity.list result payload.

        Args:
            None.
        Return:
            Typed Activity list result.
        """
        result: ForgeActivityListResultDict = ForgeActivityListResultDict(
            scope=self.scope.to_dict(),
            activities=[activity.to_dict() for activity in self.activities],
        )
        return result
