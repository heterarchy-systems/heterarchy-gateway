"""Swarm wire aliases with exact source enum input spellings."""

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


def parse_swarm_run_mode_input(value: SwarmRunModeEnum | JsonValue) -> SwarmRunModeEnum:
    """Parse the exact RunMode spellings accepted by the source API.

    Args:
        value: Source JSON string or already validated enum.
    Return:
        Canonical Swarm run mode enum.
    """
    if value in ("standalone", "STANDALONE"):
        result = SwarmRunModeEnum.STANDALONE
    elif value in ("dag_node_hybrid", "dagNodeHybrid", "DAG_NODE_HYBRID"):
        result = SwarmRunModeEnum.DAG_NODE_HYBRID
    else:
        raise ValueError("Swarm run mode spelling is not accepted by the source")
    return result


def parse_swarm_role_kind_input(value: SwarmRoleKindEnum | JsonValue) -> SwarmRoleKindEnum:
    """Parse the exact lowercase or uppercase source role spellings.

    Args:
        value: Source JSON string or already validated enum.
    Return:
        Canonical Swarm role enum.
    """
    aliases = {
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
    if not isinstance(value, str):
        raise ValueError("Swarm role kind requires a source string")
    result = aliases.get(value)
    if result is None:
        raise ValueError("Swarm role kind spelling is not accepted by the source")
    return result


def parse_swarm_workspace_mode_input(
    value: SwarmWorkspaceModeEnum | JsonValue,
) -> SwarmWorkspaceModeEnum:
    """Parse the exact lowercase or uppercase source workspace modes.

    Args:
        value: Source JSON string or already validated enum.
    Return:
        Canonical Swarm workspace mode enum.
    """
    aliases = {
        "inherit": SwarmWorkspaceModeEnum.INHERIT,
        "INHERIT": SwarmWorkspaceModeEnum.INHERIT,
        "share": SwarmWorkspaceModeEnum.SHARE,
        "SHARE": SwarmWorkspaceModeEnum.SHARE,
        "branch": SwarmWorkspaceModeEnum.BRANCH,
        "BRANCH": SwarmWorkspaceModeEnum.BRANCH,
    }
    if not isinstance(value, str):
        raise ValueError("Swarm workspace mode requires a source string")
    result = aliases.get(value)
    if result is None:
        raise ValueError("Swarm workspace mode spelling is not accepted by the source")
    return result


def parse_swarm_turn_failure_disposition_input(
    value: SwarmTurnFailureDispositionEnum | JsonValue,
) -> SwarmTurnFailureDispositionEnum:
    """Parse the exact source turn failure disposition spellings.

    Args:
        value: Source JSON string or already validated enum.
    Return:
        Canonical Swarm turn failure disposition enum.
    """
    aliases = {
        "transient_retry": SwarmTurnFailureDispositionEnum.TRANSIENT_RETRY,
        "transientRetry": SwarmTurnFailureDispositionEnum.TRANSIENT_RETRY,
        "TRANSIENT_RETRY": SwarmTurnFailureDispositionEnum.TRANSIENT_RETRY,
        "quota_exceeded": SwarmTurnFailureDispositionEnum.QUOTA_EXCEEDED,
        "quotaExceeded": SwarmTurnFailureDispositionEnum.QUOTA_EXCEEDED,
        "QUOTA_EXCEEDED": SwarmTurnFailureDispositionEnum.QUOTA_EXCEEDED,
        "stopped": SwarmTurnFailureDispositionEnum.STOPPED,
        "STOPPED": SwarmTurnFailureDispositionEnum.STOPPED,
    }
    if not isinstance(value, str):
        raise ValueError("Swarm turn failure disposition requires a source string")
    result = aliases.get(value)
    if result is None:
        raise ValueError("Swarm turn failure spelling is not accepted by the source")
    return result


def parse_swarm_convergence_target_input(
    value: SwarmConvergenceTargetEnum | JsonValue,
) -> SwarmConvergenceTargetEnum:
    """Parse the exact source convergence target spellings.

    Args:
        value: Source JSON string or already validated enum.
    Return:
        Canonical Swarm convergence target enum.
    """
    aliases = {
        "candidate_ready": SwarmConvergenceTargetEnum.CANDIDATE_READY,
        "candidateReady": SwarmConvergenceTargetEnum.CANDIDATE_READY,
        "CANDIDATE_READY": SwarmConvergenceTargetEnum.CANDIDATE_READY,
        "settled": SwarmConvergenceTargetEnum.SETTLED,
        "SETTLED": SwarmConvergenceTargetEnum.SETTLED,
    }
    if not isinstance(value, str):
        raise ValueError("Swarm convergence target requires a source string")
    result = aliases.get(value)
    if result is None:
        raise ValueError("Swarm convergence target spelling is not accepted by the source")
    return result


def parse_swarm_verdict_outcome_input(
    value: SwarmVerdictOutcomeEnum | JsonValue,
) -> SwarmVerdictOutcomeEnum:
    """Parse the exact lowercase or canonical source verdict spellings.

    Args:
        value: Source JSON string or already validated enum.
    Return:
        Canonical Swarm verdict outcome enum.
    """
    aliases = {
        "accepted": SwarmVerdictOutcomeEnum.ACCEPTED,
        "ACCEPTED": SwarmVerdictOutcomeEnum.ACCEPTED,
        "rejected": SwarmVerdictOutcomeEnum.REJECTED,
        "REJECTED": SwarmVerdictOutcomeEnum.REJECTED,
        "needs_changes": SwarmVerdictOutcomeEnum.NEEDS_CHANGES,
        "needsChanges": SwarmVerdictOutcomeEnum.NEEDS_CHANGES,
        "NEEDS_CHANGES": SwarmVerdictOutcomeEnum.NEEDS_CHANGES,
    }
    if not isinstance(value, str):
        raise ValueError("Swarm verdict outcome requires a source string")
    result = aliases.get(value)
    if result is None:
        raise ValueError("Swarm verdict outcome spelling is not accepted by the source")
    return result


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
    BeforeValidator(parse_swarm_run_mode_input),
]
type SwarmRoleKindInput = Annotated[
    SwarmRoleKindEnum,
    BeforeValidator(parse_swarm_role_kind_input),
]
type SwarmWorkspaceModeInput = Annotated[
    SwarmWorkspaceModeEnum,
    BeforeValidator(parse_swarm_workspace_mode_input),
]
type SwarmVerdictOutcomeInput = Annotated[
    SwarmVerdictOutcomeEnum,
    BeforeValidator(parse_swarm_verdict_outcome_input),
]
type SwarmTurnFailureDispositionInput = Annotated[
    SwarmTurnFailureDispositionEnum,
    BeforeValidator(parse_swarm_turn_failure_disposition_input),
]
type SwarmConvergenceTargetInput = Annotated[
    SwarmConvergenceTargetEnum,
    BeforeValidator(parse_swarm_convergence_target_input),
]
