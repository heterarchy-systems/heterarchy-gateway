"""Immutable Profile request and result DTOs with closed wire dictionaries."""

from dataclasses import dataclass
from uuid import UUID

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPreferenceDto,
)
from app.orchestration.application.inner_dto.types.profile_types import (
    CreateProfileRequestDict,
    ProfileCreateOutcomeDict,
    ProfileDict,
    ProfileLifecycleRequestDict,
    ProfileMutationDict,
    UpdateProfileConfigRequestDict,
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


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateProfileCommandDto:
    """Immutable command for creating or replaying an Agent Profile."""

    request_id: UUID
    stable_name: str
    display_name: str
    preferred_model: str | None
    preferred_reasoning: str | None
    base_capabilities: tuple[str, ...]
    execution_preference: ExecutionPreferenceDto | None

    def to_dict(self) -> CreateProfileRequestDict:
        """Serialize the create command to source wire keys.

        Args:
            None.
        Return:
            Complete typed Profile create request.
        """
        preference = (
            self.execution_preference.to_dict() if self.execution_preference is not None else None
        )
        result = CreateProfileRequestDict(
            requestId=str(self.request_id),
            stableName=self.stable_name,
            displayName=self.display_name,
            preferredModel=self.preferred_model,
            preferredReasoning=self.preferred_reasoning,
            baseCapabilities=list(self.base_capabilities),
            executionPreference=preference,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateProfileConfigCommandDto:
    """Immutable command for replacing mutable Profile configuration."""

    request_id: UUID
    expected_revision: ProfileRevision
    display_name: str
    preferred_model: str | None
    preferred_reasoning: str | None
    base_capabilities: tuple[str, ...]
    execution_preference: ExecutionPreferenceDto | None

    def to_dict(self) -> UpdateProfileConfigRequestDict:
        """Serialize the configuration update to source wire keys.

        Args:
            None.
        Return:
            Complete typed Profile configuration request.
        """
        preference = (
            self.execution_preference.to_dict() if self.execution_preference is not None else None
        )
        result = UpdateProfileConfigRequestDict(
            requestId=str(self.request_id),
            expectedRevision=self.expected_revision,
            displayName=self.display_name,
            preferredModel=self.preferred_model,
            preferredReasoning=self.preferred_reasoning,
            baseCapabilities=list(self.base_capabilities),
            executionPreference=preference,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileLifecycleCommandDto:
    """Immutable command for a revision-fenced Profile lifecycle mutation."""

    request_id: UUID
    expected_revision: ProfileRevision

    def to_dict(self) -> ProfileLifecycleRequestDict:
        """Serialize the lifecycle command to source wire keys.

        Args:
            None.
        Return:
            Complete typed Profile lifecycle request.
        """
        result = ProfileLifecycleRequestDict(
            requestId=str(self.request_id),
            expectedRevision=self.expected_revision,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileDto:
    """Immutable Agent Profile result projection."""

    profile_id: UUID
    request_id: UUID
    stable_name: str
    display_name: str
    provider_family: ProfileProviderFamilyEnum
    preferred_model: str | None
    preferred_reasoning: str | None
    base_capabilities: tuple[str, ...]
    lifecycle_state: ProfileLifecycleStateEnum
    creation_origin: ProfileCreationOriginEnum
    created_at_ms: TimestampMs
    updated_at_ms: TimestampMs
    last_used_at_ms: TimestampMs | None
    revision: ProfileRevision
    execution_preference: ExecutionPreferenceDto | None

    def to_dict(self) -> ProfileDict:
        """Serialize the Profile projection to source wire keys.

        Args:
            None.
        Return:
            Complete typed Profile result.
        """
        preference = (
            self.execution_preference.to_schema_dict()
            if self.execution_preference is not None
            else None
        )
        result = ProfileDict(
            profileId=self.profile_id,
            requestId=self.request_id,
            stableName=self.stable_name,
            displayName=self.display_name,
            providerFamily=self.provider_family,
            preferredModel=self.preferred_model,
            preferredReasoning=self.preferred_reasoning,
            baseCapabilities=list(self.base_capabilities),
            lifecycleState=self.lifecycle_state,
            creationOrigin=self.creation_origin,
            createdAtMs=self.created_at_ms,
            updatedAtMs=self.updated_at_ms,
            lastUsedAtMs=self.last_used_at_ms,
            revision=self.revision,
            executionPreference=preference,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileCreateOutcomeDto:
    """Immutable result of creating or replaying a Profile request."""

    profile: ProfileDto
    created: bool

    def to_dict(self) -> ProfileCreateOutcomeDict:
        """Serialize the create outcome to its source response envelope.

        Args:
            None.
        Return:
            Complete typed Profile create outcome.
        """
        result = ProfileCreateOutcomeDict(
            profile=self.profile.to_dict(),
            created=self.created,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ProfileMutationDto:
    """Immutable Profile mutation receipt."""

    request_id: UUID
    expected_revision: ProfileRevision | None
    kind: ProfileMutationKindEnum
    profile: ProfileDto
    replayed: bool

    def to_dict(self) -> ProfileMutationDict:
        """Serialize the mutation receipt to source wire keys.

        Args:
            None.
        Return:
            Complete typed Profile mutation receipt.
        """
        result = ProfileMutationDict(
            requestId=self.request_id,
            expectedRevision=self.expected_revision,
            kind=self.kind,
            profile=self.profile.to_dict(),
            replayed=self.replayed,
        )
        return result
