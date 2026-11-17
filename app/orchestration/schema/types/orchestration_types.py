"""Orchestration wire aliases with strict scalar and enum parsing."""

from functools import partial
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BeforeValidator, Field

from app.shared.ingredient_element.orchestration.principal_enums import PrincipalKindEnum
from app.shared.ingredient_element.orchestration.profile_enums import (
    CliEngineEnum,
    ProfileCreationOriginEnum,
    ProfileLifecycleStateEnum,
    ProfileMutationKindEnum,
    ProfileProviderFamilyEnum,
)
from app.shared.types.wire_scalar_types import WireUUID, parse_wire_enum

type ProfileUUID = WireUUID
type McpGrant = WireUUID
type Int64 = Annotated[int, Field(ge=-(2**63), le=2**63 - 1)]
type ProfileRevision = Annotated[int, Field(ge=1, le=2**63 - 1)]
type UInt32 = Annotated[int, Field(ge=0, le=2**32 - 1)]
type UInt64 = Annotated[int, Field(ge=0, le=2**64 - 1)]
type TimestampMs = Annotated[int, Field(ge=0, le=2**63 - 1)]
type ProfileListLimit = Annotated[int, Field(ge=1, le=64)]
type ExecutionTimeoutMs = Annotated[int, Field(ge=1, le=86_400_000)]

type ExecutionPreference = Annotated[
    CliEngineEnum,
    BeforeValidator(partial(parse_wire_enum, CliEngineEnum)),
]
type ProfileLifecycleState = Annotated[
    ProfileLifecycleStateEnum,
    BeforeValidator(partial(parse_wire_enum, ProfileLifecycleStateEnum)),
]
type ProfileProviderFamily = Annotated[
    ProfileProviderFamilyEnum,
    BeforeValidator(partial(parse_wire_enum, ProfileProviderFamilyEnum)),
]
type ProfileCreationOrigin = Annotated[
    ProfileCreationOriginEnum,
    BeforeValidator(partial(parse_wire_enum, ProfileCreationOriginEnum)),
]
type ProfileMutationKind = Annotated[
    ProfileMutationKindEnum,
    BeforeValidator(partial(parse_wire_enum, ProfileMutationKindEnum)),
]
type PrincipalKind = Annotated[
    PrincipalKindEnum,
    BeforeValidator(partial(parse_wire_enum, PrincipalKindEnum)),
]


def _require_non_nil_profile_identity(value: UUID) -> UUID:
    """Reject the nil UUID for a Profile projection.

    Args:
        value: Parsed Profile or creation request UUID.
    Return:
        Non-nil Profile identity.
    """
    if value.int == 0:
        raise ValueError("Profile identities must be non-nil UUIDs")
    result = value
    return result


type ProfileIdentity = Annotated[ProfileUUID, AfterValidator(_require_non_nil_profile_identity)]
