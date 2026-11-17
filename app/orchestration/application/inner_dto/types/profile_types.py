"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.types.orchestration_execution_types import (
    ExecutionPreferenceDict,
    ExecutionPreferenceResultDict,
)
from app.orchestration.schema.types.orchestration_types import (
    ProfileRevision,
    TimestampMs,
)
from app.shared.ingredient_element.orchestration.profile_enums import (
    ProfileCreationOriginEnum,
    ProfileLifecycleStateEnum,
    ProfileMutationKindEnum,
    ProfileProviderFamilyEnum,
)


class CreateProfileRequestDict(TypedDict, total=True, closed=True):
    """Typed upstream request for creating or replaying a Profile."""

    requestId: str
    stableName: str
    displayName: str
    preferredModel: str | None
    preferredReasoning: str | None
    baseCapabilities: list[str]
    executionPreference: ExecutionPreferenceDict | None


class UpdateProfileConfigRequestDict(TypedDict, total=True, closed=True):
    """Typed upstream request for updating Profile configuration."""

    requestId: str
    expectedRevision: ProfileRevision
    displayName: str
    preferredModel: str | None
    preferredReasoning: str | None
    baseCapabilities: list[str]
    executionPreference: ExecutionPreferenceDict | None


class ProfileLifecycleRequestDict(TypedDict, total=True, closed=True):
    """Typed upstream request for disabling or retiring a Profile."""

    requestId: str
    expectedRevision: ProfileRevision


class ProfileDict(TypedDict, total=True, closed=True):
    """Typed Profile projection with exact Orchestration wire keys."""

    profileId: UUID
    requestId: UUID
    stableName: str
    displayName: str
    providerFamily: ProfileProviderFamilyEnum
    preferredModel: str | None
    preferredReasoning: str | None
    baseCapabilities: list[str]
    lifecycleState: ProfileLifecycleStateEnum
    creationOrigin: ProfileCreationOriginEnum
    createdAtMs: TimestampMs
    updatedAtMs: TimestampMs
    lastUsedAtMs: TimestampMs | None
    revision: ProfileRevision
    executionPreference: ExecutionPreferenceResultDict | None


class ProfileCreateOutcomeDict(TypedDict, total=True, closed=True):
    """Typed create/replay response envelope."""

    profile: ProfileDict
    created: bool


class ProfileMutationDict(TypedDict, total=True, closed=True):
    """Typed durable Profile mutation receipt."""

    requestId: UUID
    expectedRevision: ProfileRevision | None
    kind: ProfileMutationKindEnum
    profile: ProfileDict
    replayed: bool
