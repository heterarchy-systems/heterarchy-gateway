"""Pure request forwarding and normalization for Agent Profile contracts."""

from collections.abc import Mapping
from enum import StrEnum
from functools import partial
from uuid import UUID

from fastapi import status
from pydantic import JsonValue

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPreferenceDto,
)
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.profile_inner_dto import (
    CreateProfileCommandDto,
    ProfileCreateOutcomeDict,
    ProfileCreateOutcomeDto,
    ProfileDict,
    ProfileDto,
    ProfileLifecycleCommandDto,
    ProfileMutationDict,
    ProfileMutationDto,
    UpdateProfileConfigCommandDto,
)
from app.orchestration.application.orchestration_command_utils import (
    execute_orchestration_operation,
)
from app.orchestration.schema.profile.orchestration_profile_schema import (
    CreateProfileRequest,
    ProfileConfigurationEcho,
    ProfileExecutionPreferenceEcho,
    ProfileLifecycleEcho,
    ProfileLifecycleRequest,
    ProfileListFilter,
    ProfileMutationEcho,
    ProfileUpdateEcho,
    UpdateProfileConfigRequest,
)
from app.orchestration.schema.types.orchestration_types import Int64, ProfileRevision
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.ingredient_element.orchestration.profile_enums import (
    CliEngineEnum,
    ProfileCreationOriginEnum,
    ProfileLifecycleStateEnum,
    ProfileMutationKindEnum,
    ProfileProviderFamilyEnum,
)
from app.shared.types.base_types import JsonObject
from app.shared.types.wire_scalar_types import parse_wire_enum, parse_wire_uuid

_PROFILE_REQUIRED_KEYS = (
    "profileId",
    "requestId",
    "stableName",
    "displayName",
    "providerFamily",
    "preferredModel",
    "preferredReasoning",
    "baseCapabilities",
    "lifecycleState",
    "creationOrigin",
    "createdAtMs",
    "updatedAtMs",
    "lastUsedAtMs",
    "revision",
)
_PROFILE_OPTIONAL_KEYS = ("executionPreference",)
_EXECUTION_PREFERENCE_REQUIRED_KEYS = (
    "cliEngine",
    "preferredModel",
    "preferredReasoning",
    "capabilities",
    "rolePromptDigestHex",
)
_MAX_CAPABILITIES = 32
_MAX_CAPABILITY_BYTES = 64
_MAX_PROVIDER_PREFERENCE_BYTES = 128
_ROLE_PROMPT_DIGEST_HEX_BYTES = 64
_LOWER_HEX_DIGITS = "0123456789abcdef"
_MAX_PROFILE_REVISION = 2**63 - 1
_PROFILE_LIFECYCLE_TARGETS = {
    ProfileMutationKindEnum.DISABLE: ProfileLifecycleStateEnum.DISABLED,
    ProfileMutationKindEnum.RETIRE: ProfileLifecycleStateEnum.RETIRED,
}


class ProfileApplication:
    """Forward Profile operations and parse source-owned JSON contracts."""

    def __init__(self, orchestration_calling: OrchestrationCalling) -> None:
        """Initialize the application with the request-scoped caller.

        Args:
            orchestration_calling: Request-scoped Orchestration transport.
        Return:
            None.
        """
        self._orchestration_calling = orchestration_calling

    async def create_profile(
        self,
        request: CreateProfileRequest,
    ) -> OrchestrationOutcomeDto[ProfileCreateOutcomeDict]:
        """Create or exactly replay one Profile request.

        Args:
            request: Validated Profile create contract.
        Return:
            Source status with the typed Profile create outcome.
        """
        command: CreateProfileCommandDto = request.to_inner_dto()
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path="/internal/v1/agent-profiles",
            parse_result=partial(
                _parse_profile_create_result,
                expected_request_id=request.request_id,
            ),
            body=command.to_dict(),
            result_statuses=(status.HTTP_200_OK, status.HTTP_201_CREATED),
        )
        return result

    async def fetch_profiles(
        self,
        filters: ProfileListFilter,
    ) -> OrchestrationOutcomeDto[list[ProfileDict]]:
        """Fetch the bounded root-array Profile catalogue.

        Args:
            filters: Optional source limit query.
        Return:
            Source status with typed Profile result dictionaries.
        """
        result_limit = filters.limit or 64
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path="/internal/v1/agent-profiles",
            parse_result=partial(_parse_profile_list_result, result_limit=result_limit),
            params=filters.to_query_params(),
        )
        return result

    async def fetch_profile(
        self,
        profile_id: UUID,
    ) -> OrchestrationOutcomeDto[ProfileDict]:
        """Fetch one Profile and require its source identity echo.

        Args:
            profile_id: Profile UUID from the route path.
        Return:
            Source status with the typed Profile result.
        """
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="GET",
            path=f"/internal/v1/agent-profiles/{profile_id}",
            parse_result=partial(_parse_profile_result, expected_profile_id=profile_id),
        )
        return result

    async def update_profile_config(
        self,
        profile_id: UUID,
        request: UpdateProfileConfigRequest,
    ) -> OrchestrationOutcomeDto[ProfileMutationDict]:
        """Update mutable Profile configuration at an expected revision.

        Args:
            profile_id: Profile UUID from the route path.
            request: Validated configuration update.
        Return:
            Source status with the typed mutation receipt.
        """
        command: UpdateProfileConfigCommandDto = request.to_inner_dto()
        expected_configuration = _profile_configuration_from_request(command=command)
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="PUT",
            path=f"/internal/v1/agent-profiles/{profile_id}/configuration",
            parse_result=partial(
                _parse_profile_update_result,
                expected_request_id=request.request_id,
                expected_profile_id=profile_id,
                expected_revision=request.expected_revision,
                expected_configuration=expected_configuration,
            ),
            body=command.to_dict(),
        )
        return result

    async def disable_profile(
        self,
        profile_id: UUID,
        request: ProfileLifecycleRequest,
    ) -> OrchestrationOutcomeDto[ProfileMutationDict]:
        """Disable one Profile at an expected revision.

        Args:
            profile_id: Profile UUID from the route path.
            request: Validated lifecycle mutation request.
        Return:
            Source status with the typed mutation receipt.
        """
        result = await self._execute_lifecycle_profile(
            profile_id=profile_id,
            request=request,
            kind=ProfileMutationKindEnum.DISABLE,
        )
        return result

    async def retire_profile(
        self,
        profile_id: UUID,
        request: ProfileLifecycleRequest,
    ) -> OrchestrationOutcomeDto[ProfileMutationDict]:
        """Retire one Profile at an expected revision.

        Args:
            profile_id: Profile UUID from the route path.
            request: Validated lifecycle mutation request.
        Return:
            Source status with the typed mutation receipt.
        """
        result = await self._execute_lifecycle_profile(
            profile_id=profile_id,
            request=request,
            kind=ProfileMutationKindEnum.RETIRE,
        )
        return result

    async def _execute_lifecycle_profile(
        self,
        profile_id: UUID,
        request: ProfileLifecycleRequest,
        kind: ProfileMutationKindEnum,
    ) -> OrchestrationOutcomeDto[ProfileMutationDict]:
        """Forward one lifecycle command and validate its identity receipt.

        Args:
            profile_id: Profile UUID from the route path.
            request: Validated lifecycle mutation request.
            kind: Source mutation kind matching the route.
        Return:
            Source status with the typed mutation receipt.
        """
        command: ProfileLifecycleCommandDto = request.to_inner_dto()
        target_state = _PROFILE_LIFECYCLE_TARGETS[kind]
        result = await execute_orchestration_operation(
            calling=self._orchestration_calling,
            method="POST",
            path=f"/internal/v1/agent-profiles/{profile_id}/{kind.value}",
            parse_result=partial(
                _parse_profile_lifecycle_result,
                expected_request_id=request.request_id,
                expected_profile_id=profile_id,
                expected_revision=request.expected_revision,
                expected_kind=kind,
                expected_state=target_state,
            ),
            body=command.to_dict(),
        )
        return result


def _parse_profile_create_result(
    value: JsonValue,
    *,
    expected_request_id: UUID,
) -> ProfileCreateOutcomeDict:
    """Parse and identity-check the create/replay source response.

    Args:
        value: Decoded Orchestration JSON body.
        expected_request_id: Exact request UUID supplied to the source.
    Return:
        Complete typed Profile create outcome.
    """
    payload = _source_object(value=value, required_keys=("profile", "created"))
    profile = _parse_profile(value=payload["profile"])
    created = _required_bool(payload=payload, key="created")
    if profile.request_id != expected_request_id:
        raise ValueError("Profile create response request identity mismatch")
    if created and profile.provider_family is not ProfileProviderFamilyEnum.UNBOUND:
        raise ValueError("New Profile create response must be unbound")
    result = ProfileCreateOutcomeDto(profile=profile, created=created).to_dict()
    return result


def _parse_profile_list_result(value: JsonValue, *, result_limit: int) -> list[ProfileDict]:
    """Parse the source root-array Profile response.

    Args:
        value: Decoded Orchestration JSON body.
        result_limit: Effective bounded source limit.
    Return:
        Typed Profile dictionaries preserving root-array shape.
    """
    if not isinstance(value, list):
        raise ValueError("Profile list response must be a root array")
    if len(value) > result_limit:
        raise ValueError("Profile list response exceeded the requested limit")
    profiles: list[ProfileDict] = []
    profile_ids: list[UUID] = []
    request_ids: list[UUID] = []
    for item in value:
        profile = _parse_profile(value=item)
        if profile.profile_id in profile_ids:
            raise ValueError("Profile list response contains a duplicate profile identity")
        if profile.request_id in request_ids:
            raise ValueError("Profile list response contains a duplicate request identity")
        profile_ids.append(profile.profile_id)
        request_ids.append(profile.request_id)
        profiles.append(profile.to_dict())
    result = profiles
    return result


def _parse_profile_result(value: JsonValue, *, expected_profile_id: UUID) -> ProfileDict:
    """Parse one source Profile and require its path identity echo.

    Args:
        value: Decoded Orchestration JSON body.
        expected_profile_id: Exact Profile UUID supplied in the route path.
    Return:
        Complete typed Profile result.
    """
    profile = _parse_profile(value=value)
    if profile.profile_id != expected_profile_id:
        raise ValueError("Profile response path identity mismatch")
    result = profile.to_dict()
    return result


def _parse_profile_update_result(
    value: JsonValue,
    *,
    expected_request_id: UUID,
    expected_profile_id: UUID,
    expected_revision: ProfileRevision,
    expected_configuration: ProfileConfigurationEcho,
) -> ProfileMutationDict:
    """Parse a mutation receipt and require source identity echoes.

    Args:
        value: Decoded Orchestration JSON body.
        expected_request_id: Exact mutation request UUID.
        expected_profile_id: Profile UUID supplied in the route path.
        expected_revision: Revision supplied in the request body.
    expected_configuration: Source-canonicalized update configuration.
    Return:
        Complete typed Profile mutation receipt.
    """
    payload = _source_object(
        value=value, required_keys=("requestId", "expectedRevision", "kind", "profile", "replayed")
    )
    mutation = _parse_profile_mutation(payload=payload)
    if mutation.expected_revision is None:
        raise ValueError("Profile mutation response omitted its expected revision")
    observed = ProfileMutationEcho(
        request_id=mutation.request_id,
        profile_id=mutation.profile.profile_id,
        expected_revision=mutation.expected_revision,
        kind=mutation.kind,
    )
    expected = ProfileMutationEcho(
        request_id=expected_request_id,
        profile_id=expected_profile_id,
        expected_revision=expected_revision,
        kind=ProfileMutationKindEnum.UPDATE,
    )
    if observed != expected:
        raise ValueError("Profile mutation response identity mismatch")
    expected_update = ProfileUpdateEcho(
        revision=expected_revision + 1,
        lifecycle_state=ProfileLifecycleStateEnum.ACTIVE,
        configuration=expected_configuration,
    )
    observed_update = ProfileUpdateEcho(
        revision=mutation.profile.revision,
        lifecycle_state=mutation.profile.lifecycle_state,
        configuration=_profile_configuration_from_result(profile=mutation.profile),
    )
    if observed_update != expected_update:
        raise ValueError("Profile update response does not match the source client contract")
    result = mutation.to_dict()
    return result


def _parse_profile_lifecycle_result(
    value: JsonValue,
    *,
    expected_request_id: UUID,
    expected_profile_id: UUID,
    expected_revision: ProfileRevision,
    expected_kind: ProfileMutationKindEnum,
    expected_state: ProfileLifecycleStateEnum,
) -> ProfileMutationDict:
    """Validate a lifecycle receipt with the source's no-op revision rule.

    Args:
        value: Decoded Orchestration JSON body.
        expected_request_id: Exact mutation request UUID.
        expected_profile_id: Profile UUID supplied in the route path.
        expected_revision: Revision supplied in the request body.
        expected_kind: Disable or retire operation selected by route.
        expected_state: Target lifecycle state.
    Return:
        Complete typed Profile mutation receipt.
    """
    mutation = _parse_profile_mutation_json(value=value)
    _require_mutation_echo(
        mutation=mutation,
        expected_request_id=expected_request_id,
        expected_profile_id=expected_profile_id,
        expected_revision=expected_revision,
        expected_kind=expected_kind,
    )
    observed = ProfileLifecycleEcho(
        revision=mutation.profile.revision,
        lifecycle_state=mutation.profile.lifecycle_state,
    )
    unchanged = ProfileLifecycleEcho(
        revision=expected_revision,
        lifecycle_state=expected_state,
    )
    if observed != unchanged:
        advanced = ProfileLifecycleEcho(
            revision=expected_revision + 1,
            lifecycle_state=expected_state,
        )
        if observed != advanced:
            raise ValueError("Profile lifecycle response does not match the source client contract")
    result = mutation.to_dict()
    return result


def _parse_profile_mutation_json(value: JsonValue) -> ProfileMutationDto:
    """Parse a source Profile mutation receipt object.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Profile mutation DTO.
    """
    payload = _source_object(
        value=value, required_keys=("requestId", "expectedRevision", "kind", "profile", "replayed")
    )
    result = _parse_profile_mutation(payload=payload)
    return result


def _require_mutation_echo(
    mutation: ProfileMutationDto,
    expected_request_id: UUID,
    expected_profile_id: UUID,
    expected_revision: ProfileRevision,
    expected_kind: ProfileMutationKindEnum,
) -> None:
    """Require the mutation identity echoed by the source client.

    Args:
        mutation: Parsed source mutation DTO.
        expected_request_id: Exact mutation request UUID.
        expected_profile_id: Profile UUID supplied in the route path.
        expected_revision: Revision supplied in the request body.
        expected_kind: Mutation operation selected by route.
    Return:
        None.
    """
    if mutation.expected_revision is None:
        raise ValueError("Profile mutation response omitted its expected revision")
    observed = ProfileMutationEcho(
        request_id=mutation.request_id,
        profile_id=mutation.profile.profile_id,
        expected_revision=mutation.expected_revision,
        kind=mutation.kind,
    )
    expected = ProfileMutationEcho(
        request_id=expected_request_id,
        profile_id=expected_profile_id,
        expected_revision=expected_revision,
        kind=expected_kind,
    )
    if observed != expected:
        raise ValueError("Profile mutation response identity mismatch")


def _parse_profile(value: JsonValue) -> ProfileDto:
    """Normalize source-legal omission and parse one Profile object.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Profile DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=_PROFILE_REQUIRED_KEYS,
        optional_keys=_PROFILE_OPTIONAL_KEYS,
    )
    execution_preference = _parse_execution_preference(value=payload.get("executionPreference"))
    result = ProfileDto(
        profile_id=_required_uuid(payload=payload, key="profileId"),
        request_id=_required_uuid(payload=payload, key="requestId"),
        stable_name=_required_string(payload=payload, key="stableName"),
        display_name=_required_string(payload=payload, key="displayName"),
        provider_family=_required_enum(
            payload=payload, key="providerFamily", enum_type=ProfileProviderFamilyEnum
        ),
        preferred_model=_required_optional_string(payload=payload, key="preferredModel"),
        preferred_reasoning=_required_optional_string(payload=payload, key="preferredReasoning"),
        base_capabilities=_required_string_tuple(payload=payload, key="baseCapabilities"),
        lifecycle_state=_required_enum(
            payload=payload, key="lifecycleState", enum_type=ProfileLifecycleStateEnum
        ),
        creation_origin=_required_enum(
            payload=payload, key="creationOrigin", enum_type=ProfileCreationOriginEnum
        ),
        created_at_ms=_required_int(payload=payload, key="createdAtMs"),
        updated_at_ms=_required_int(payload=payload, key="updatedAtMs"),
        last_used_at_ms=_required_optional_int(payload=payload, key="lastUsedAtMs"),
        revision=_required_profile_revision(payload=payload, key="revision"),
        execution_preference=execution_preference,
    )
    if result.profile_id.int == 0 or result.request_id.int == 0:
        raise ValueError("Profile response contains a nil identity")
    if result.updated_at_ms < result.created_at_ms:
        raise ValueError("Profile response update time precedes creation time")
    if result.last_used_at_ms is not None and result.last_used_at_ms < 0:
        raise ValueError("Profile response last-use time is negative")
    if result.execution_preference is not None:
        _validate_execution_preference(preference=result.execution_preference)
    return result


def _parse_execution_preference(value: JsonValue | None) -> ExecutionPreferenceDto | None:
    """Parse an optional source execution preference.

    Args:
        value: Decoded nested preference or source-legal absence.
    Return:
        Immutable execution preference DTO or None.
    """
    if value is None:
        result = None
    else:
        payload = _source_object(
            value=value,
            required_keys=_EXECUTION_PREFERENCE_REQUIRED_KEYS,
        )
        result = ExecutionPreferenceDto(
            cli_engine=_required_enum(payload=payload, key="cliEngine", enum_type=CliEngineEnum),
            preferred_model=_required_string(payload=payload, key="preferredModel"),
            preferred_reasoning=_required_optional_string(
                payload=payload, key="preferredReasoning"
            ),
            capabilities=_required_string_tuple(payload=payload, key="capabilities"),
            role_prompt_digest_hex=_required_optional_string(
                payload=payload, key="rolePromptDigestHex"
            ),
        )
    return result


def _parse_profile_mutation(payload: JsonObject) -> ProfileMutationDto:
    """Parse one source Profile mutation receipt object.

    Args:
        payload: Exact decoded mutation receipt fields.
    Return:
        Immutable Profile mutation DTO.
    """
    expected_revision = _required_optional_revision(payload=payload, key="expectedRevision")
    profile = _parse_profile(value=payload["profile"])
    result = ProfileMutationDto(
        request_id=_required_uuid(payload=payload, key="requestId"),
        expected_revision=expected_revision,
        kind=_required_enum(payload=payload, key="kind", enum_type=ProfileMutationKindEnum),
        profile=profile,
        replayed=_required_bool(payload=payload, key="replayed"),
    )
    return result


def _profile_configuration_from_request(
    command: UpdateProfileConfigCommandDto,
) -> ProfileConfigurationEcho:
    """Build the source-canonical configuration expected after update.

    Args:
        command: Validated Profile update command DTO.
    Return:
        Configuration echo with the source's sorted capability lists.
    """
    preference = _profile_preference_echo(
        preference=command.execution_preference,
        sort_capabilities=True,
    )
    result = ProfileConfigurationEcho(
        display_name=command.display_name,
        preferred_model=command.preferred_model,
        preferred_reasoning=command.preferred_reasoning,
        base_capabilities=tuple(sorted(command.base_capabilities)),
        execution_preference=preference,
    )
    return result


def _profile_configuration_from_result(profile: ProfileDto) -> ProfileConfigurationEcho:
    """Build the exact configuration projection returned by the source.

    Args:
        profile: Parsed source Profile DTO.
    Return:
        Configuration echo preserving source capability ordering.
    """
    preference = _profile_preference_echo(
        preference=profile.execution_preference,
        sort_capabilities=False,
    )
    result = ProfileConfigurationEcho(
        display_name=profile.display_name,
        preferred_model=profile.preferred_model,
        preferred_reasoning=profile.preferred_reasoning,
        base_capabilities=profile.base_capabilities,
        execution_preference=preference,
    )
    return result


def _profile_preference_echo(
    preference: ExecutionPreferenceDto | None,
    *,
    sort_capabilities: bool,
) -> ProfileExecutionPreferenceEcho | None:
    """Build a strict execution preference comparison projection.

    Args:
        preference: Immutable execution preference DTO or None.
        sort_capabilities: Whether to apply source configuration ordering.
    Return:
        Strict preference equality projection or None.
    """
    if preference is None:
        result = None
    else:
        capabilities = (
            tuple(sorted(preference.capabilities)) if sort_capabilities else preference.capabilities
        )
        result = ProfileExecutionPreferenceEcho(
            cli_engine=preference.cli_engine,
            preferred_model=preference.preferred_model,
            preferred_reasoning=preference.preferred_reasoning,
            capabilities=capabilities,
            role_prompt_digest_hex=preference.role_prompt_digest_hex,
        )
    return result


def _validate_execution_preference(preference: ExecutionPreferenceDto) -> None:
    """Apply the exact Profile source client's preference validity check.

    Args:
        preference: Parsed source execution preference.
    Return:
        None.
    """
    if not _source_text_is_valid(
        value=preference.preferred_model, maximum_bytes=_MAX_PROVIDER_PREFERENCE_BYTES
    ):
        raise ValueError("Profile execution preference model is invalid")
    if preference.preferred_reasoning is not None and not _source_text_is_valid(
        value=preference.preferred_reasoning,
        maximum_bytes=_MAX_PROVIDER_PREFERENCE_BYTES,
    ):
        raise ValueError("Profile execution preference reasoning is invalid")
    if len(preference.capabilities) > _MAX_CAPABILITIES:
        raise ValueError("Profile execution preference has too many capabilities")
    for capability in preference.capabilities:
        if not _source_text_is_valid(value=capability, maximum_bytes=_MAX_CAPABILITY_BYTES):
            raise ValueError("Profile execution preference capability is invalid")
    if _has_duplicate_values(values=preference.capabilities):
        raise ValueError("Profile execution preference contains duplicate capabilities")
    if preference.role_prompt_digest_hex is not None:
        _validate_role_prompt_digest(value=preference.role_prompt_digest_hex)


def _source_text_is_valid(value: str, maximum_bytes: int) -> bool:
    """Check the source's nonempty UTF-8 byte-length contract.

    Args:
        value: Source text value.
        maximum_bytes: Source maximum encoded byte length.
    Return:
        Whether the string is nonempty and within the source bound.
    """
    encoded_length = len(value.encode("utf-8"))
    result = 0 < encoded_length <= maximum_bytes
    return result


def _has_duplicate_values(values: tuple[str, ...]) -> bool:
    """Detect duplicate source capability labels.

    Args:
        values: Immutable source capability sequence.
    Return:
        Whether a label appears more than once.
    """
    result = any(value in values[index + 1 :] for index, value in enumerate(values))
    return result


def _validate_role_prompt_digest(value: str) -> None:
    """Require a nonzero lowercase 64-character SHA-256 digest.

    Args:
        value: Source hexadecimal digest.
    Return:
        None.
    """
    if len(value) != _ROLE_PROMPT_DIGEST_HEX_BYTES:
        raise ValueError("Profile role prompt digest has an invalid length")
    if not all(character in _LOWER_HEX_DIGITS for character in value):
        raise ValueError("Profile role prompt digest must use lowercase hexadecimal")
    if not any(character != "0" for character in value):
        raise ValueError("Profile role prompt digest must be nonzero")


def _source_object(
    value: JsonValue,
    required_keys: tuple[str, ...],
    *,
    optional_keys: tuple[str, ...] = (),
) -> JsonObject:
    """Narrow a JSON object while rejecting unknown or missing source fields.

    Args:
        value: Decoded JSON value.
        required_keys: Keys that the source contract requires.
        optional_keys: Source-legal omitted keys normalized by the parser.
    Return:
        Validated JSON object mapping.
    """
    if not isinstance(value, dict):
        raise ValueError("Orchestration result must be a JSON object")
    allowed_keys = (*required_keys, *optional_keys)
    if not all(key in value for key in required_keys):
        raise ValueError("Orchestration result is missing a required field")
    if not all(key in allowed_keys for key in value):
        raise ValueError("Orchestration result contains an unknown field")
    result = value
    return result


def _required_string(payload: Mapping[str, JsonValue], key: str) -> str:
    """Extract one required string without coercion.

    Args:
        payload: Validated JSON object mapping.
        key: Required source key.
    Return:
        Exact source string.
    """
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError(f"Orchestration field {key} must be a string")
    result = value
    return result


def _required_optional_string(payload: Mapping[str, JsonValue], key: str) -> str | None:
    """Extract one present nullable string field.

    Args:
        payload: Validated JSON object mapping.
        key: Required nullable source key.
    Return:
        Source string or None.
    """
    value = payload[key]
    if value is None:
        result = None
    elif isinstance(value, str):
        result = value
    else:
        raise ValueError(f"Orchestration field {key} must be a string or null")
    return result


def _required_bool(payload: Mapping[str, JsonValue], key: str) -> bool:
    """Extract one required strict boolean field.

    Args:
        payload: Validated JSON object mapping.
        key: Required source key.
    Return:
        Exact source boolean.
    """
    value = payload[key]
    if type(value) is not bool:
        raise ValueError(f"Orchestration field {key} must be a boolean")
    result = value
    return result


def _required_int(payload: Mapping[str, JsonValue], key: str) -> Int64:
    """Extract one required strict integer field.

    Args:
        payload: Validated JSON object mapping.
        key: Required source key.
    Return:
        Exact source integer.
    """
    value = payload[key]
    if type(value) is not int:
        raise ValueError(f"Orchestration field {key} must be an integer")
    result: Int64 = value
    return result


def _required_profile_revision(
    payload: Mapping[str, JsonValue],
    key: str,
) -> ProfileRevision:
    """Extract a positive signed-64 source Profile revision.

    Args:
        payload: Validated JSON object mapping.
        key: Required source revision key.
    Return:
        Positive source Profile revision.
    """
    value = payload[key]
    if type(value) is not int or not 1 <= value <= _MAX_PROFILE_REVISION:
        raise ValueError(f"Orchestration field {key} must be a positive Profile revision")
    result: ProfileRevision = value
    return result


def _required_optional_int(payload: Mapping[str, JsonValue], key: str) -> Int64 | None:
    """Extract one present nullable strict integer field.

    Args:
        payload: Validated JSON object mapping.
        key: Required nullable source key.
    Return:
        Source integer or None.
    """
    value = payload[key]
    if value is None:
        result = None
    elif type(value) is int:
        result = value
    else:
        raise ValueError(f"Orchestration field {key} must be an integer or null")
    return result


def _required_optional_revision(
    payload: Mapping[str, JsonValue],
    key: str,
) -> ProfileRevision | None:
    """Extract a present nullable source Profile revision.

    Args:
        payload: Validated JSON object mapping.
        key: Required nullable source revision key.
    Return:
        Positive source Profile revision or None.
    """
    value = payload[key]
    if value is None:
        result = None
    elif type(value) is int and 1 <= value <= _MAX_PROFILE_REVISION:
        result = value
    else:
        raise ValueError(f"Orchestration field {key} must be a positive revision or null")
    return result


def _required_string_tuple(payload: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    """Extract one array of source strings without coercion.

    Args:
        payload: Validated JSON object mapping.
        key: Required source key.
    Return:
        Immutable tuple of exact source strings.
    """
    value = payload[key]
    if not isinstance(value, list):
        raise ValueError(f"Orchestration field {key} must be an array")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"Orchestration field {key} entries must be strings")
        items.append(item)
    result = tuple(items)
    return result


def _required_uuid(payload: Mapping[str, JsonValue], key: str) -> UUID:
    """Extract one source UUID from its canonical JSON string.

    Args:
        payload: Validated JSON object mapping.
        key: Required source key.
    Return:
        Parsed UUID instance.
    """
    value = payload[key]
    result = parse_wire_uuid(value=value)
    return result


def _required_enum[EnumT: StrEnum](
    payload: Mapping[str, JsonValue],
    key: str,
    enum_type: type[EnumT],
) -> EnumT:
    """Extract one exact source StrEnum value.

    Args:
        payload: Validated JSON object mapping.
        key: Required source key.
        enum_type: Source-backed enum type.
    Return:
        Exact declared enum member.
    """
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError(f"Orchestration field {key} must be a string enum")
    result = parse_wire_enum(enum_type=enum_type, value=value)
    return result
