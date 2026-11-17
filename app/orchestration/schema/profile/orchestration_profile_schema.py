"""Strict Gateway schemas for the six Agent Profile endpoints."""

from typing import Annotated

from pydantic import Field

from app.orchestration.application.inner_dto.profile_inner_dto import (
    CreateProfileCommandDto,
    ProfileLifecycleCommandDto,
    UpdateProfileConfigCommandDto,
)
from app.orchestration.schema.execution.orchestration_execution_schema import (
    ExecutionPreferenceSchema,
)
from app.orchestration.schema.types.orchestration_types import (
    ExecutionPreference,
    ProfileCreationOrigin,
    ProfileIdentity,
    ProfileLifecycleState,
    ProfileListLimit,
    ProfileMutationKind,
    ProfileProviderFamily,
    ProfileRevision,
    TimestampMs,
)
from app.shared.base_schema import StrictRootSchemaModel, StrictSchemaModel
from app.shared.filter_module.base_filter import BaseFilter


class CreateProfileRequest(StrictSchemaModel):
    """Validated request to create or exactly replay an Agent Profile."""

    request_id: Annotated[
        ProfileIdentity, Field(alias="requestId", description="Stable request UUID.")
    ]
    stable_name: Annotated[str, Field(alias="stableName", description="Stable Profile name.")]
    display_name: Annotated[str, Field(alias="displayName", description="Display name.")]
    preferred_model: Annotated[
        str | None,
        Field(alias="preferredModel", description="Preferred model or null."),
    ]
    preferred_reasoning: Annotated[
        str | None,
        Field(alias="preferredReasoning", description="Preferred reasoning or null."),
    ]
    base_capabilities: Annotated[
        list[str],
        Field(alias="baseCapabilities", description="Reusable capability labels."),
    ]
    execution_preference: Annotated[
        ExecutionPreferenceSchema | None,
        Field(alias="executionPreference", description="Optional reusable CLI preference."),
    ]

    def to_inner_dto(self) -> CreateProfileCommandDto:
        """Convert the validated request to an immutable command DTO.

        Args:
            None.
        Return:
            Immutable Profile create command.
        """
        preference = (
            self.execution_preference.to_inner_dto()
            if self.execution_preference is not None
            else None
        )
        result = CreateProfileCommandDto(
            request_id=self.request_id,
            stable_name=self.stable_name,
            display_name=self.display_name,
            preferred_model=self.preferred_model,
            preferred_reasoning=self.preferred_reasoning,
            base_capabilities=tuple(self.base_capabilities),
            execution_preference=preference,
        )
        return result


class ProfileListFilter(BaseFilter):
    """Optional bounded query for the Agent Profile catalogue."""

    limit: Annotated[
        ProfileListLimit | None,
        Field(description="Optional result limit from 1 through 64."),
    ] = None


class ProfileResponse(StrictSchemaModel):
    """Canonical global Profile readback."""

    profile_id: Annotated[ProfileIdentity, Field(alias="profileId", description="Profile UUID.")]
    request_id: Annotated[
        ProfileIdentity, Field(alias="requestId", description="Creation request UUID.")
    ]
    stable_name: Annotated[str, Field(alias="stableName", description="Stable Profile name.")]
    display_name: Annotated[str, Field(alias="displayName", description="Display name.")]
    provider_family: Annotated[
        ProfileProviderFamily,
        Field(alias="providerFamily", description="Provider family metadata."),
    ]
    preferred_model: Annotated[
        str | None,
        Field(alias="preferredModel", description="Preferred model or null."),
    ]
    preferred_reasoning: Annotated[
        str | None,
        Field(alias="preferredReasoning", description="Preferred reasoning or null."),
    ]
    base_capabilities: Annotated[
        list[str],
        Field(alias="baseCapabilities", description="Reusable capability labels."),
    ]
    lifecycle_state: Annotated[
        ProfileLifecycleState,
        Field(alias="lifecycleState", description="Durable Profile lifecycle state."),
    ]
    creation_origin: Annotated[
        ProfileCreationOrigin,
        Field(alias="creationOrigin", description="Profile creation audit origin."),
    ]
    created_at_ms: Annotated[
        TimestampMs,
        Field(alias="createdAtMs", description="Creation time in Unix milliseconds."),
    ]
    updated_at_ms: Annotated[
        TimestampMs,
        Field(alias="updatedAtMs", description="Last update time in Unix milliseconds."),
    ]
    last_used_at_ms: Annotated[
        TimestampMs | None,
        Field(alias="lastUsedAtMs", description="Last use time or null."),
    ]
    revision: Annotated[ProfileRevision, Field(description="Source Profile revision.")]
    execution_preference: Annotated[
        ExecutionPreferenceSchema | None,
        Field(alias="executionPreference", description="Reusable CLI preference or null."),
    ]


class ProfileCreateResponse(StrictSchemaModel):
    """Create result or exact replay outcome."""

    profile: Annotated[ProfileResponse, Field(description="Canonical Profile readback.")]
    created: Annotated[bool, Field(description="Whether this request created the Profile.")]


class ProfileLifecycleRequest(StrictSchemaModel):
    """Request to disable or retire a Profile at an expected revision."""

    request_id: Annotated[
        ProfileIdentity, Field(alias="requestId", description="Stable mutation UUID.")
    ]
    expected_revision: Annotated[
        ProfileRevision,
        Field(alias="expectedRevision", description="Expected Profile revision."),
    ]

    def to_inner_dto(self) -> ProfileLifecycleCommandDto:
        """Convert the validated lifecycle request to an immutable DTO.

        Args:
            None.
        Return:
            Immutable Profile lifecycle command.
        """
        result = ProfileLifecycleCommandDto(
            request_id=self.request_id,
            expected_revision=self.expected_revision,
        )
        return result


class UpdateProfileConfigRequest(StrictSchemaModel):
    """Request to replace mutable Profile configuration."""

    request_id: Annotated[
        ProfileIdentity, Field(alias="requestId", description="Stable mutation UUID.")
    ]
    expected_revision: Annotated[
        ProfileRevision,
        Field(alias="expectedRevision", description="Expected Profile revision."),
    ]
    display_name: Annotated[str, Field(alias="displayName", description="New display name.")]
    preferred_model: Annotated[
        str | None,
        Field(alias="preferredModel", description="Preferred model or null."),
    ]
    preferred_reasoning: Annotated[
        str | None,
        Field(alias="preferredReasoning", description="Preferred reasoning or null."),
    ]
    base_capabilities: Annotated[
        list[str],
        Field(alias="baseCapabilities", description="Reusable capability labels."),
    ]
    execution_preference: Annotated[
        ExecutionPreferenceSchema | None,
        Field(alias="executionPreference", description="Optional reusable CLI preference."),
    ]

    def to_inner_dto(self) -> UpdateProfileConfigCommandDto:
        """Convert the validated configuration request to an immutable DTO.

        Args:
            None.
        Return:
            Immutable Profile configuration command.
        """
        preference = (
            self.execution_preference.to_inner_dto()
            if self.execution_preference is not None
            else None
        )
        result = UpdateProfileConfigCommandDto(
            request_id=self.request_id,
            expected_revision=self.expected_revision,
            display_name=self.display_name,
            preferred_model=self.preferred_model,
            preferred_reasoning=self.preferred_reasoning,
            base_capabilities=tuple(self.base_capabilities),
            execution_preference=preference,
        )
        return result


class ProfileMutationResponse(StrictSchemaModel):
    """Immutable receipt for an update, disable or retire operation."""

    request_id: Annotated[
        ProfileIdentity, Field(alias="requestId", description="Mutation request UUID.")
    ]
    expected_revision: Annotated[
        ProfileRevision | None,
        Field(alias="expectedRevision", description="Expected revision or null for create."),
    ]
    kind: Annotated[ProfileMutationKind, Field(description="Durable mutation kind.")]
    profile: Annotated[ProfileResponse, Field(description="Canonical Profile readback.")]
    replayed: Annotated[bool, Field(description="Whether the source returned a replay receipt.")]


class ProfileMutationEcho(StrictSchemaModel):
    """Required mutation identity fields compared as one strict projection."""

    request_id: Annotated[ProfileIdentity, Field(description="Mutation request UUID.")]
    profile_id: Annotated[ProfileIdentity, Field(description="Profile UUID.")]
    expected_revision: Annotated[ProfileRevision, Field(description="Expected Profile revision.")]
    kind: Annotated[ProfileMutationKind, Field(description="Source mutation kind.")]


class ProfileExecutionPreferenceEcho(StrictSchemaModel):
    """Validated Profile preference compared with configuration updates."""

    cli_engine: Annotated[ExecutionPreference, Field(description="CLI engine.")]
    preferred_model: Annotated[str, Field(description="Preferred model.")]
    preferred_reasoning: Annotated[str | None, Field(description="Preferred reasoning or null.")]
    capabilities: Annotated[tuple[str, ...], Field(description="Canonical capabilities.")]
    role_prompt_digest_hex: Annotated[
        str | None,
        Field(description="Role prompt digest or null."),
    ]


class ProfileConfigurationEcho(StrictSchemaModel):
    """Strict equality projection for Profile configuration echoes."""

    display_name: Annotated[str, Field(description="Profile display name.")]
    preferred_model: Annotated[str | None, Field(description="Preferred model or null.")]
    preferred_reasoning: Annotated[str | None, Field(description="Preferred reasoning or null.")]
    base_capabilities: Annotated[tuple[str, ...], Field(description="Canonical capabilities.")]
    execution_preference: Annotated[
        ProfileExecutionPreferenceEcho | None,
        Field(description="Execution preference or null."),
    ]


class ProfileUpdateEcho(StrictSchemaModel):
    """Profile fields the source client requires after an update."""

    revision: Annotated[ProfileRevision, Field(description="Expected next Profile revision.")]
    lifecycle_state: Annotated[
        ProfileLifecycleState,
        Field(description="Profile lifecycle remains active."),
    ]
    configuration: Annotated[
        ProfileConfigurationEcho,
        Field(description="Updated Profile configuration echo."),
    ]


class ProfileLifecycleEcho(StrictSchemaModel):
    """Profile fields the source client requires after a lifecycle mutation."""

    revision: Annotated[ProfileRevision, Field(description="Expected Profile revision.")]
    lifecycle_state: Annotated[
        ProfileLifecycleState,
        Field(description="Target Profile lifecycle state."),
    ]


class ProfileListResponse(StrictRootSchemaModel[list[ProfileResponse]]):
    """Root-array response containing bounded Agent Profile records."""
