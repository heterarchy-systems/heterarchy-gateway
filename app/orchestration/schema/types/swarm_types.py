"""Swarm wire aliases with exact source enum input spellings."""

from collections.abc import Mapping
from enum import StrEnum
from functools import partial
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BeforeValidator, Field, JsonValue

from app.orchestration.schema.types.orchestration_types import Int64, UInt64
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmConvergenceTargetEnum,
    SwarmDoorbellReasonEnum,
    SwarmMemberStateEnum,
    SwarmPanelSeatKindEnum,
    SwarmRoleKindEnum,
    SwarmRunModeEnum,
    SwarmRunStateEnum,
    SwarmTurnFailureDispositionEnum,
    SwarmVerdictOutcomeEnum,
    SwarmWorkspaceModeEnum,
)
from app.shared.types.wire_scalar_types import WireUUID, parse_wire_enum, parse_wire_uuid

type SwarmUUID = WireUUID
type SwarmUInt8 = Annotated[int, Field(ge=0, le=255)]
type SwarmDagRevision = Annotated[Int64, Field(ge=1)]
type SwarmRevision = Annotated[UInt64, Field(ge=1)]

type SwarmRunModeKind = Annotated[
    SwarmRunModeEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmRunModeEnum)),
]
type SwarmRunState = Annotated[
    SwarmRunStateEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmRunStateEnum)),
]
type SwarmRoleKind = Annotated[
    SwarmRoleKindEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmRoleKindEnum)),
]
type SwarmWorkspaceMode = Annotated[
    SwarmWorkspaceModeEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmWorkspaceModeEnum)),
]
type SwarmMemberState = Annotated[
    SwarmMemberStateEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmMemberStateEnum)),
]
type SwarmDoorbellReason = Annotated[
    SwarmDoorbellReasonEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmDoorbellReasonEnum)),
]
type SwarmPanelSeatKind = Annotated[
    SwarmPanelSeatKindEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmPanelSeatKindEnum)),
]
type SwarmVerdictOutcome = Annotated[
    SwarmVerdictOutcomeEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmVerdictOutcomeEnum)),
]
type SwarmTurnFailureDisposition = Annotated[
    SwarmTurnFailureDispositionEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmTurnFailureDispositionEnum)),
]
type SwarmConvergenceTarget = Annotated[
    SwarmConvergenceTargetEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmConvergenceTargetEnum)),
]


def _require_non_nil_swarm_uuid(value: UUID | JsonValue) -> UUID:
    """Parse a source UUID and reject its nil identity.

    Args:
        value: UUID object or JSON UUID string.
    Return:
        Non-nil Swarm UUID.
    """
    parsed = parse_wire_uuid(value=value)
    if parsed.int == 0:
        raise ValueError("Swarm identities must be non-nil UUIDs")
    result = parsed
    return result


def parse_non_zero_digest_hex(value: str | JsonValue) -> str:
    """Validate a source 64-character lowercase nonzero digest.

    Args:
        value: Source digest JSON value.
    Return:
        Exact validated source digest string.
    """
    if not isinstance(value, str):
        raise ValueError("Swarm digest must be a string")
    if len(value) != 64:
        raise ValueError("Swarm digest must contain 64 hexadecimal characters")
    if not all(character in "0123456789abcdef" for character in value):
        raise ValueError("Swarm digest must use lowercase hexadecimal")
    if not any(character != "0" for character in value):
        raise ValueError("Swarm digest must be nonzero")
    result = value
    return result


type NonZeroDigestHex = Annotated[str, BeforeValidator(parse_non_zero_digest_hex)]


def _parse_aliased_enum[EnumT: StrEnum](
    aliases: Mapping[str, EnumT],
    label: str,
    value: EnumT | JsonValue,
) -> EnumT:
    """Parse exact source enum spellings using an explicit closed alias table.

    Args:
        aliases: Closed spelling-to-enum lookup owned by this Swarm field.
        label: Human-readable field label for validation errors.
        value: Source JSON string or already validated enum.
    Return:
        Canonical Swarm enum member.
    """
    if not isinstance(value, str):
        raise ValueError(f"{label} requires a source string")
    result = aliases.get(value)
    if result is None:
        raise ValueError(f"{label} spelling is not accepted by the source")
    return result


_RUN_MODE_ALIASES: dict[str, SwarmRunModeEnum] = {
    "standalone": SwarmRunModeEnum.STANDALONE,
    "STANDALONE": SwarmRunModeEnum.STANDALONE,
    "dag_node_hybrid": SwarmRunModeEnum.DAG_NODE_HYBRID,
    "dagNodeHybrid": SwarmRunModeEnum.DAG_NODE_HYBRID,
    "DAG_NODE_HYBRID": SwarmRunModeEnum.DAG_NODE_HYBRID,
}
_ROLE_KIND_ALIASES: dict[str, SwarmRoleKindEnum] = {
    "coordinator": SwarmRoleKindEnum.COORDINATOR,
    "COORDINATOR": SwarmRoleKindEnum.COORDINATOR,
    "worker": SwarmRoleKindEnum.WORKER,
    "WORKER": SwarmRoleKindEnum.WORKER,
    "helper": SwarmRoleKindEnum.HELPER,
    "HELPER": SwarmRoleKindEnum.HELPER,
    "verifier": SwarmRoleKindEnum.VERIFIER,
    "VERIFIER": SwarmRoleKindEnum.VERIFIER,
    "monitor": SwarmRoleKindEnum.MONITOR,
    "MONITOR": SwarmRoleKindEnum.MONITOR,
}
_WORKSPACE_MODE_ALIASES: dict[str, SwarmWorkspaceModeEnum] = {
    "inherit": SwarmWorkspaceModeEnum.INHERIT,
    "INHERIT": SwarmWorkspaceModeEnum.INHERIT,
    "share": SwarmWorkspaceModeEnum.SHARE,
    "SHARE": SwarmWorkspaceModeEnum.SHARE,
    "branch": SwarmWorkspaceModeEnum.BRANCH,
    "BRANCH": SwarmWorkspaceModeEnum.BRANCH,
}
_FAILURE_DISPOSITION_ALIASES: dict[str, SwarmTurnFailureDispositionEnum] = {
    "transient_retry": SwarmTurnFailureDispositionEnum.TRANSIENT_RETRY,
    "transientRetry": SwarmTurnFailureDispositionEnum.TRANSIENT_RETRY,
    "TRANSIENT_RETRY": SwarmTurnFailureDispositionEnum.TRANSIENT_RETRY,
    "quota_exceeded": SwarmTurnFailureDispositionEnum.QUOTA_EXCEEDED,
    "quotaExceeded": SwarmTurnFailureDispositionEnum.QUOTA_EXCEEDED,
    "QUOTA_EXCEEDED": SwarmTurnFailureDispositionEnum.QUOTA_EXCEEDED,
    "stopped": SwarmTurnFailureDispositionEnum.STOPPED,
    "STOPPED": SwarmTurnFailureDispositionEnum.STOPPED,
}
_CONVERGENCE_TARGET_ALIASES: dict[str, SwarmConvergenceTargetEnum] = {
    "candidate_ready": SwarmConvergenceTargetEnum.CANDIDATE_READY,
    "candidateReady": SwarmConvergenceTargetEnum.CANDIDATE_READY,
    "CANDIDATE_READY": SwarmConvergenceTargetEnum.CANDIDATE_READY,
    "settled": SwarmConvergenceTargetEnum.SETTLED,
    "SETTLED": SwarmConvergenceTargetEnum.SETTLED,
}
_VERDICT_OUTCOME_ALIASES: dict[str, SwarmVerdictOutcomeEnum] = {
    "accepted": SwarmVerdictOutcomeEnum.ACCEPTED,
    "ACCEPTED": SwarmVerdictOutcomeEnum.ACCEPTED,
    "rejected": SwarmVerdictOutcomeEnum.REJECTED,
    "REJECTED": SwarmVerdictOutcomeEnum.REJECTED,
    "needs_changes": SwarmVerdictOutcomeEnum.NEEDS_CHANGES,
    "needsChanges": SwarmVerdictOutcomeEnum.NEEDS_CHANGES,
    "NEEDS_CHANGES": SwarmVerdictOutcomeEnum.NEEDS_CHANGES,
}


def parse_canonical_swarm_uuid(value: UUID | JsonValue) -> UUID:
    """Parse a source UUID while requiring canonical lowercase hyphenated text.

    Args:
        value: UUID object or source JSON UUID string.
    Return:
        Parsed canonical UUID.
    """
    parsed = parse_wire_uuid(value=value)
    if isinstance(value, str) and str(parsed) != value:
        raise ValueError("Swarm identity must use canonical lowercase UUID text")
    result = parsed
    return result


def parse_swarm_commit_oid_input(value: str | JsonValue) -> str:
    """Validate source Git commit OID spelling without changing request text.

    Args:
        value: Source commit OID JSON value.
    Return:
        Original source string after validating its trimmed lowercase form.
    """
    if not isinstance(value, str):
        raise ValueError("Swarm commit OID must be a string")
    normalized = value.strip()
    if not 40 <= len(normalized) <= 64:
        raise ValueError("Swarm commit OID length is outside the source range")
    if not all(character in "0123456789abcdefABCDEF" for character in normalized):
        raise ValueError("Swarm commit OID must use hexadecimal characters")
    result = value
    return result


type CanonicalSwarmUUID = Annotated[UUID, BeforeValidator(parse_canonical_swarm_uuid)]
type NonNilSwarmUUID = Annotated[CanonicalSwarmUUID, AfterValidator(_require_non_nil_swarm_uuid)]
type NonNilCanonicalSwarmUUID = NonNilSwarmUUID
type SwarmCommitOid = Annotated[str, BeforeValidator(parse_swarm_commit_oid_input)]

type SwarmRunModeKindInput = Annotated[
    SwarmRunModeEnum,
    BeforeValidator(partial(_parse_aliased_enum, _RUN_MODE_ALIASES, "Swarm run mode")),
]
type SwarmRoleKindInput = Annotated[
    SwarmRoleKindEnum,
    BeforeValidator(partial(_parse_aliased_enum, _ROLE_KIND_ALIASES, "Swarm role kind")),
]
type SwarmWorkspaceModeInput = Annotated[
    SwarmWorkspaceModeEnum,
    BeforeValidator(partial(_parse_aliased_enum, _WORKSPACE_MODE_ALIASES, "Swarm workspace mode")),
]
type SwarmVerdictOutcomeInput = Annotated[
    SwarmVerdictOutcomeEnum,
    BeforeValidator(
        partial(_parse_aliased_enum, _VERDICT_OUTCOME_ALIASES, "Swarm verdict outcome")
    ),
]
type SwarmTurnFailureDispositionInput = Annotated[
    SwarmTurnFailureDispositionEnum,
    BeforeValidator(
        partial(
            _parse_aliased_enum,
            _FAILURE_DISPOSITION_ALIASES,
            "Swarm turn failure disposition",
        )
    ),
]
type SwarmConvergenceTargetInput = Annotated[
    SwarmConvergenceTargetEnum,
    BeforeValidator(
        partial(_parse_aliased_enum, _CONVERGENCE_TARGET_ALIASES, "Swarm convergence target")
    ),
]
