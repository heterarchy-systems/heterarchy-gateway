"""Wire parsers and source echo validators for Agent Profile contracts."""

from functools import partial
from uuid import UUID

from pydantic import JsonValue

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPreferenceDto,
)
from app.orchestration.application.inner_dto.profile_inner_dto import (
    ProfileCreateOutcomeDto,
    ProfileDto,
    ProfileMutationDto,
    UpdateProfileConfigCommandDto,
)
from app.orchestration.application.inner_dto.types.profile_types import (
    ProfileCreateOutcomeDict,
    ProfileDict,
    ProfileMutationDict,
)
from app.orchestration.application.orchestration_wire_parsers import (
    INT64_MAX,
    parse_wire_array,
    parse_wire_bool,
    parse_wire_int,
    parse_wire_str,
    parse_wire_str_tuple,
    require_wire_object,
    wire_optional,
)
from app.orchestration.schema.profile.orchestration_profile_schema import (
    ProfileConfigurationEcho,
    ProfileExecutionPreferenceEcho,
    ProfileLifecycleEcho,
    ProfileMutationEcho,
    ProfileUpdateEcho,
)
from app.orchestration.schema.types.orchestration_types import ProfileRevision
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


def parse_profile_create_result(
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
    payload = require_wire_object(payload=value, required_keys=("profile", "created"))
    profile = _parse_profile(value=payload["profile"])
    created = parse_wire_bool(value=payload["created"], label="created")
    if profile.request_id != expected_request_id:
        raise ValueError("Profile create response request identity mismatch")
    if created and profile.provider_family is not ProfileProviderFamilyEnum.UNBOUND:
        raise ValueError("New Profile create response must be unbound")
    result = ProfileCreateOutcomeDto(profile=profile, created=created).to_dict()
    return result


def parse_profile_list_result(value: JsonValue, *, result_limit: int) -> list[ProfileDict]:
    """Parse the source root-array Profile response.

    Args:
        value: Decoded Orchestration JSON body.
        result_limit: Effective bounded source limit.
    Return:
        Typed Profile dictionaries preserving root-array shape.
    """
    items = parse_wire_array(value=value, label="Profile list response")
    if len(items) > result_limit:
        raise ValueError("Profile list response exceeded the requested limit")
    profiles: list[ProfileDict] = []
    profile_ids: list[UUID] = []
    request_ids: list[UUID] = []
    for item in items:
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


def parse_profile_result(value: JsonValue, *, expected_profile_id: UUID) -> ProfileDict:
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


def parse_profile_update_result(
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
    mutation = _parse_profile_mutation_json(value=value)
    _require_mutation_echo(
        mutation=mutation,
        expected_request_id=expected_request_id,
        expected_profile_id=expected_profile_id,
        expected_revision=expected_revision,
        expected_kind=ProfileMutationKindEnum.UPDATE,
    )
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


def parse_profile_lifecycle_result(
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


def profile_configuration_from_request(
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


def _parse_profile_mutation_json(value: JsonValue) -> ProfileMutationDto:
    """Parse a source Profile mutation receipt object.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Profile mutation DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=("requestId", "expectedRevision", "kind", "profile", "replayed"),
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
    payload = require_wire_object(
        payload=value,
        required_keys=_PROFILE_REQUIRED_KEYS,
        optional_keys=_PROFILE_OPTIONAL_KEYS,
    )
    execution_preference = wire_optional(
        value=payload.get("executionPreference"),
        parser=_parse_execution_preference,
    )
    result = ProfileDto(
        profile_id=parse_wire_uuid(value=payload["profileId"]),
        request_id=parse_wire_uuid(value=payload["requestId"]),
        stable_name=parse_wire_str(value=payload["stableName"], label="stableName"),
        display_name=parse_wire_str(value=payload["displayName"], label="displayName"),
        provider_family=parse_wire_enum(
            enum_type=ProfileProviderFamilyEnum, value=payload["providerFamily"]
        ),
        preferred_model=wire_optional(
            value=payload["preferredModel"],
            parser=partial(parse_wire_str, label="preferredModel"),
        ),
        preferred_reasoning=wire_optional(
            value=payload["preferredReasoning"],
            parser=partial(parse_wire_str, label="preferredReasoning"),
        ),
        base_capabilities=parse_wire_str_tuple(
            value=payload["baseCapabilities"], label="baseCapabilities"
        ),
        lifecycle_state=parse_wire_enum(
            enum_type=ProfileLifecycleStateEnum, value=payload["lifecycleState"]
        ),
        creation_origin=parse_wire_enum(
            enum_type=ProfileCreationOriginEnum, value=payload["creationOrigin"]
        ),
        created_at_ms=parse_wire_int(value=payload["createdAtMs"], label="createdAtMs"),
        updated_at_ms=parse_wire_int(value=payload["updatedAtMs"], label="updatedAtMs"),
        last_used_at_ms=wire_optional(
            value=payload["lastUsedAtMs"],
            parser=partial(parse_wire_int, label="lastUsedAtMs"),
        ),
        revision=parse_wire_int(
            value=payload["revision"], minimum=1, maximum=INT64_MAX, label="revision"
        ),
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


def _parse_execution_preference(value: JsonValue) -> ExecutionPreferenceDto:
    """Parse one non-null source execution preference object.

    Args:
        value: Decoded nested preference JSON value.
    Return:
        Immutable execution preference DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=_EXECUTION_PREFERENCE_REQUIRED_KEYS,
    )
    result = ExecutionPreferenceDto(
        cli_engine=parse_wire_enum(enum_type=CliEngineEnum, value=payload["cliEngine"]),
        preferred_model=parse_wire_str(value=payload["preferredModel"], label="preferredModel"),
        preferred_reasoning=wire_optional(
            value=payload["preferredReasoning"],
            parser=partial(parse_wire_str, label="preferredReasoning"),
        ),
        capabilities=parse_wire_str_tuple(value=payload["capabilities"], label="capabilities"),
        role_prompt_digest_hex=wire_optional(
            value=payload["rolePromptDigestHex"],
            parser=partial(parse_wire_str, label="rolePromptDigestHex"),
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
    expected_revision = wire_optional(
        value=payload["expectedRevision"],
        parser=partial(parse_wire_int, minimum=1, maximum=INT64_MAX, label="expectedRevision"),
    )
    profile = _parse_profile(value=payload["profile"])
    result = ProfileMutationDto(
        request_id=parse_wire_uuid(value=payload["requestId"]),
        expected_revision=expected_revision,
        kind=parse_wire_enum(enum_type=ProfileMutationKindEnum, value=payload["kind"]),
        profile=profile,
        replayed=parse_wire_bool(value=payload["replayed"], label="replayed"),
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
