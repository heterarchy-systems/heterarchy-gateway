"""Source-shape parsers for shared Orchestration Swarm leaf records."""

from collections.abc import Callable, Mapping
from enum import StrEnum
from uuid import UUID

from pydantic import JsonValue

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    PrincipalIdentityDto,
)
from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
    DagNodeHybridTargetDto,
    SwarmBoardMessageDto,
    SwarmChannelDto,
    SwarmChannelSubscriptionDto,
    SwarmConvergenceGateDto,
    SwarmDoorbellDto,
    SwarmMemberDto,
    SwarmMemberIdentityDto,
    SwarmPanelSeatDto,
    SwarmRunDto,
    SwarmRunModeDto,
    SwarmVerdictDto,
    SwarmVerificationPanelDto,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt32, UInt64
from app.orchestration.schema.types.swarm_types import SwarmRevision, SwarmUInt8
from app.shared.ingredient_element.orchestration.principal_enums import PrincipalKindEnum
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmDoorbellReasonEnum,
    SwarmMemberStateEnum,
    SwarmPanelSeatKindEnum,
    SwarmRoleKindEnum,
    SwarmRunModeEnum,
    SwarmRunStateEnum,
    SwarmVerdictOutcomeEnum,
    SwarmWorkspaceModeEnum,
)
from app.shared.types.base_types import JsonObject
from app.shared.types.wire_scalar_types import parse_wire_enum, parse_wire_uuid

_RUN_REQUIRED_KEYS = (
    "swarmRunId",
    "workspaceId",
    "title",
    "mode",
    "state",
    "maxMembers",
    "maxSpawnDepth",
    "maxTotalTurns",
    "totalTurnsUsed",
    "requiredVerifierQuorum",
    "allowWorkerAllMention",
    "baselineCommitOid",
    "baselineTreeBlake3Hex",
    "stallNudgeCount",
    "revision",
    "createdAtMs",
    "updatedAtMs",
    "replayed",
)
_RUN_OPTIONAL_KEYS = (
    "convergedCommitOid",
    "convergedTreeBlake3Hex",
    "convergedDiffDigestHex",
    "settlementRequestId",
)
_CHANNEL_OPTIONAL_KEYS = ("purpose", "createdByMemberId")
_MEMBER_OPTIONAL_KEYS = (
    "parentMemberId",
    "worktreePath",
    "activeSnapshotId",
    "pingPongPeerId",
    "lastOutputCommitOid",
    "lastOutputTreeBlake3Hex",
)
_MESSAGE_OPTIONAL_KEYS = ("authorMemberId", "authorEpoch")
_PANEL_KEYS = (
    "panelId",
    "swarmRunId",
    "workspaceId",
    "requiredQuorum",
    "autoCreated",
    "seats",
    "createdAtMs",
    "replayed",
)


def parse_dag_node_hybrid_target(value: JsonValue) -> DagNodeHybridTargetDto:
    """Parse one source DAG-node hybrid target record.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable DAG-node hybrid target DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=(
            "goalId",
            "dagRevision",
            "nodeId",
            "declaredWriteManifestBlake3Hex",
        ),
    )
    result = DagNodeHybridTargetDto(
        goal_id=_required_uuid(payload=payload, key="goalId"),
        dag_revision=_required_int(payload=payload, key="dagRevision"),
        node_id=_required_uuid(payload=payload, key="nodeId"),
        declared_write_manifest_blake3_hex=_required_string(
            payload=payload,
            key="declaredWriteManifestBlake3Hex",
        ),
    )
    return result


def parse_swarm_run_mode(value: JsonValue) -> SwarmRunModeDto:
    """Parse the canonical source Swarm run mode record.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Swarm run mode DTO.
    """
    payload = _source_object(value=value, required_keys=("kind",), optional_keys=("hybridTarget",))
    hybrid_target = _optional_nested(
        value=payload.get("hybridTarget"),
        parser=parse_dag_node_hybrid_target,
    )
    result = SwarmRunModeDto(
        kind=_required_enum(payload=payload, key="kind", enum_type=SwarmRunModeEnum),
        hybrid_target=hybrid_target,
    )
    return result


def parse_swarm_run(value: JsonValue) -> SwarmRunDto:
    """Parse one source Swarm run projection and its legal omissions.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Swarm run DTO.
    """
    payload = _source_object(
        value=value, required_keys=_RUN_REQUIRED_KEYS, optional_keys=_RUN_OPTIONAL_KEYS
    )
    result = SwarmRunDto(
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        workspace_id=_required_uuid(payload=payload, key="workspaceId"),
        title=_required_string(payload=payload, key="title"),
        mode=parse_swarm_run_mode(value=payload["mode"]),
        state=_required_enum(payload=payload, key="state", enum_type=SwarmRunStateEnum),
        max_members=_required_uint32(payload=payload, key="maxMembers"),
        max_spawn_depth=_required_uint8(payload=payload, key="maxSpawnDepth"),
        max_total_turns=_required_uint64(payload=payload, key="maxTotalTurns"),
        total_turns_used=_required_uint64(payload=payload, key="totalTurnsUsed"),
        required_verifier_quorum=_required_uint32(payload=payload, key="requiredVerifierQuorum"),
        allow_worker_all_mention=_required_bool(payload=payload, key="allowWorkerAllMention"),
        baseline_commit_oid=_required_string(payload=payload, key="baselineCommitOid"),
        baseline_tree_blake3_hex=_required_string(payload=payload, key="baselineTreeBlake3Hex"),
        converged_commit_oid=_optional_string(value=payload.get("convergedCommitOid")),
        converged_tree_blake3_hex=_optional_string(value=payload.get("convergedTreeBlake3Hex")),
        converged_diff_digest_hex=_optional_string(value=payload.get("convergedDiffDigestHex")),
        stall_nudge_count=_required_uint32(payload=payload, key="stallNudgeCount"),
        settlement_request_id=_optional_uuid(value=payload.get("settlementRequestId")),
        revision=_required_positive_int(payload=payload, key="revision"),
        created_at_ms=_required_int(payload=payload, key="createdAtMs"),
        updated_at_ms=_required_int(payload=payload, key="updatedAtMs"),
        replayed=_required_bool(payload=payload, key="replayed"),
    )
    if result.title == "":
        raise ValueError("Swarm run response title must be nonempty")
    if result.created_at_ms < 0:
        raise ValueError("Swarm run response creation time is negative")
    if result.updated_at_ms < result.created_at_ms:
        raise ValueError("Swarm run response update time precedes creation time")
    return result


def parse_swarm_channel(value: JsonValue) -> SwarmChannelDto:
    """Parse one source Swarm channel projection.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Swarm channel DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=("channelId", "swarmRunId", "workspaceId", "name", "createdAtMs"),
        optional_keys=_CHANNEL_OPTIONAL_KEYS,
    )
    result = SwarmChannelDto(
        channel_id=_required_uuid(payload=payload, key="channelId"),
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        workspace_id=_required_uuid(payload=payload, key="workspaceId"),
        name=_required_string(payload=payload, key="name"),
        purpose=_optional_string(value=payload.get("purpose")),
        created_by_member_id=_optional_uuid(value=payload.get("createdByMemberId")),
        created_at_ms=_required_int(payload=payload, key="createdAtMs"),
    )
    return result


def parse_swarm_channel_subscription(value: JsonValue) -> SwarmChannelSubscriptionDto:
    """Parse one source Swarm channel subscription edge.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable subscription DTO.
    """
    payload = _source_object(value=value, required_keys=("channelId", "memberId"))
    result = SwarmChannelSubscriptionDto(
        channel_id=_required_uuid(payload=payload, key="channelId"),
        member_id=_required_uuid(payload=payload, key="memberId"),
    )
    return result


def parse_swarm_doorbell(value: JsonValue) -> SwarmDoorbellDto:
    """Parse one pending source Swarm wakeup doorbell.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable doorbell DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=("swarmRunId", "targetMemberId", "sequence", "reason", "enqueuedAtMs"),
    )
    result = SwarmDoorbellDto(
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        target_member_id=_required_uuid(payload=payload, key="targetMemberId"),
        sequence=_required_uint64(payload=payload, key="sequence"),
        reason=_required_enum(payload=payload, key="reason", enum_type=SwarmDoorbellReasonEnum),
        enqueued_at_ms=_required_int(payload=payload, key="enqueuedAtMs"),
    )
    return result


def parse_swarm_member_identity(value: JsonValue) -> SwarmMemberIdentityDto:
    """Parse one three-axis source Swarm member identity.

    The source gives a missing principal `id` the explicit default empty string.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable member identity DTO.
    """
    payload = _source_object(value=value, required_keys=("profileId", "participantId", "principal"))
    principal = _parse_principal_identity(value=payload["principal"])
    result = SwarmMemberIdentityDto(
        profile_id=_required_uuid(payload=payload, key="profileId"),
        participant_id=_required_uuid(payload=payload, key="participantId"),
        principal=principal,
    )
    return result


def parse_swarm_member(value: JsonValue) -> SwarmMemberDto:
    """Parse one source Swarm member projection and legal omissions.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Swarm member DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=(
            "memberId",
            "swarmRunId",
            "workspaceId",
            "rosterName",
            "roleKind",
            "spawnDepth",
            "workspaceMode",
            "memberState",
            "identity",
            "committedSeenSeq",
            "inflightTargetSeq",
            "attemptEpoch",
            "turnsUsed",
            "pingPongStreak",
            "createdAtMs",
            "updatedAtMs",
        ),
        optional_keys=_MEMBER_OPTIONAL_KEYS,
    )
    result = SwarmMemberDto(
        member_id=_required_uuid(payload=payload, key="memberId"),
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        workspace_id=_required_uuid(payload=payload, key="workspaceId"),
        roster_name=_required_string(payload=payload, key="rosterName"),
        role_kind=_required_enum(payload=payload, key="roleKind", enum_type=SwarmRoleKindEnum),
        parent_member_id=_optional_uuid(value=payload.get("parentMemberId")),
        spawn_depth=_required_uint8(payload=payload, key="spawnDepth"),
        workspace_mode=_required_enum(
            payload=payload, key="workspaceMode", enum_type=SwarmWorkspaceModeEnum
        ),
        worktree_path=_optional_string(value=payload.get("worktreePath")),
        member_state=_required_enum(
            payload=payload, key="memberState", enum_type=SwarmMemberStateEnum
        ),
        identity=parse_swarm_member_identity(value=payload["identity"]),
        committed_seen_seq=_required_uint64(payload=payload, key="committedSeenSeq"),
        inflight_target_seq=_required_uint64(payload=payload, key="inflightTargetSeq"),
        active_snapshot_id=_optional_uuid(value=payload.get("activeSnapshotId")),
        attempt_epoch=_required_uint64(payload=payload, key="attemptEpoch"),
        turns_used=_required_uint64(payload=payload, key="turnsUsed"),
        ping_pong_peer_id=_optional_uuid(value=payload.get("pingPongPeerId")),
        ping_pong_streak=_required_uint32(payload=payload, key="pingPongStreak"),
        last_output_commit_oid=_optional_string(value=payload.get("lastOutputCommitOid")),
        last_output_tree_blake3_hex=_optional_string(value=payload.get("lastOutputTreeBlake3Hex")),
        created_at_ms=_required_int(payload=payload, key="createdAtMs"),
        updated_at_ms=_required_int(payload=payload, key="updatedAtMs"),
    )
    if result.roster_name == "":
        raise ValueError("Swarm member response roster name must be nonempty")
    return result


def parse_swarm_board_message(value: JsonValue) -> SwarmBoardMessageDto:
    """Parse one source Swarm board message and its legal omissions.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable board message DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=(
            "messageId",
            "workspaceId",
            "sequence",
            "swarmRunId",
            "channelId",
            "channelName",
            "authorRosterName",
            "body",
            "submittedAtMs",
        ),
        optional_keys=_MESSAGE_OPTIONAL_KEYS,
    )
    result = SwarmBoardMessageDto(
        message_id=_required_uuid(payload=payload, key="messageId"),
        workspace_id=_required_uuid(payload=payload, key="workspaceId"),
        sequence=_required_uint64(payload=payload, key="sequence"),
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        channel_id=_required_uuid(payload=payload, key="channelId"),
        channel_name=_required_string(payload=payload, key="channelName"),
        author_member_id=_optional_uuid(value=payload.get("authorMemberId")),
        author_roster_name=_required_string(payload=payload, key="authorRosterName"),
        author_epoch=_optional_int(value=payload.get("authorEpoch")),
        body=_required_string(payload=payload, key="body"),
        submitted_at_ms=_required_int(payload=payload, key="submittedAtMs"),
    )
    return result


def parse_swarm_panel_seat(value: JsonValue) -> SwarmPanelSeatDto:
    """Parse one source Swarm verification panel seat.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable panel seat DTO.
    """
    payload = _source_object(value=value, required_keys=("memberId", "seatKind", "assignedAtMs"))
    result = SwarmPanelSeatDto(
        member_id=_required_uuid(payload=payload, key="memberId"),
        seat_kind=_required_enum(payload=payload, key="seatKind", enum_type=SwarmPanelSeatKindEnum),
        assigned_at_ms=_required_int(payload=payload, key="assignedAtMs"),
    )
    return result


def parse_swarm_verification_panel(value: JsonValue) -> SwarmVerificationPanelDto:
    """Parse one source Swarm verification panel with nested seats.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable verification panel DTO.
    """
    payload = _source_object(value=value, required_keys=_PANEL_KEYS)
    seats = _required_object_items(payload=payload, key="seats", parser=parse_swarm_panel_seat)
    result = SwarmVerificationPanelDto(
        panel_id=_required_uuid(payload=payload, key="panelId"),
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        workspace_id=_required_uuid(payload=payload, key="workspaceId"),
        required_quorum=_required_uint32(payload=payload, key="requiredQuorum"),
        auto_created=_required_bool(payload=payload, key="autoCreated"),
        seats=tuple(seats),
        created_at_ms=_required_int(payload=payload, key="createdAtMs"),
        replayed=_required_bool(payload=payload, key="replayed"),
    )
    return result


def parse_swarm_verdict(value: JsonValue) -> SwarmVerdictDto:
    """Parse one source immutable Swarm verifier verdict.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Swarm verdict DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=(
            "verdictId",
            "requestId",
            "panelId",
            "swarmRunId",
            "verifierMemberId",
            "outcome",
            "reviewedDiffDigestHex",
            "rationale",
            "recordedAtMs",
            "replayed",
        ),
    )
    result = SwarmVerdictDto(
        verdict_id=_required_uuid(payload=payload, key="verdictId"),
        request_id=_required_uuid(payload=payload, key="requestId"),
        panel_id=_required_uuid(payload=payload, key="panelId"),
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        verifier_member_id=_required_uuid(payload=payload, key="verifierMemberId"),
        outcome=_required_enum(payload=payload, key="outcome", enum_type=SwarmVerdictOutcomeEnum),
        reviewed_diff_digest_hex=_required_string(payload=payload, key="reviewedDiffDigestHex"),
        rationale=_required_string(payload=payload, key="rationale"),
        recorded_at_ms=_required_int(payload=payload, key="recordedAtMs"),
        replayed=_required_bool(payload=payload, key="replayed"),
    )
    return result


def parse_swarm_convergence_gate(value: JsonValue) -> SwarmConvergenceGateDto:
    """Parse one source verified Swarm convergence gate.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable convergence gate DTO.
    """
    payload = _source_object(
        value=value,
        required_keys=(
            "panelId",
            "swarmRunId",
            "convergedDiffDigestHex",
            "requiredQuorum",
            "acceptedVerdicts",
        ),
    )
    verdicts = _required_object_items(
        payload=payload, key="acceptedVerdicts", parser=parse_swarm_verdict
    )
    result = SwarmConvergenceGateDto(
        panel_id=_required_uuid(payload=payload, key="panelId"),
        swarm_run_id=_required_uuid(payload=payload, key="swarmRunId"),
        converged_diff_digest_hex=_required_string(payload=payload, key="convergedDiffDigestHex"),
        required_quorum=_required_uint32(payload=payload, key="requiredQuorum"),
        accepted_verdicts=tuple(verdicts),
    )
    return result


def _parse_principal_identity(value: JsonValue) -> PrincipalIdentityDto:
    """Parse a principal identity and source-defaulted ID.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable principal identity DTO.
    """
    payload = _source_object(value=value, required_keys=("kind",), optional_keys=("id",))
    principal_id = "" if "id" not in payload else _required_string(payload=payload, key="id")
    result = PrincipalIdentityDto(
        kind=_required_enum(payload=payload, key="kind", enum_type=PrincipalKindEnum),
        id=principal_id,
    )
    return result


def _required_object_items[DtoT](
    payload: Mapping[str, JsonValue],
    key: str,
    parser: Callable[[JsonValue], DtoT],
) -> list[DtoT]:
    """Parse one required array of source objects into leaf DTOs.

    Args:
        payload: Validated JSON object mapping.
        key: Required source array key.
        parser: Source leaf parser.
    Return:
        Parsed immutable leaf DTOs.
    """
    value = payload[key]
    if not isinstance(value, list):
        raise ValueError(f"Swarm field {key} must be an array")
    result = [parser(item) for item in value]
    return result


def _optional_nested[DtoT](
    value: JsonValue | None,
    parser: Callable[[JsonValue], DtoT],
) -> DtoT | None:
    """Normalize a source-omitted optional nested wire object.

    Args:
        value: Source nested object, null or legal omission.
        parser: Typed parser for the nested source object.
    Return:
        Parsed nested DTO or None.
    """
    if value is None:
        result = None
    else:
        result = parser(value)
    return result


def _source_object(
    value: JsonValue,
    required_keys: tuple[str, ...],
    *,
    optional_keys: tuple[str, ...] = (),
) -> JsonObject:
    """Narrow a source JSON object and reject unknown or missing fields.

    Args:
        value: Decoded JSON value.
        required_keys: Fields required by the Rust wire type.
        optional_keys: Fields source-omitted with a Serde default.
    Return:
        Validated JSON object mapping.
    """
    if not isinstance(value, dict):
        raise ValueError("Swarm result must be a JSON object")
    allowed_keys = (*required_keys, *optional_keys)
    if not all(key in value for key in required_keys):
        raise ValueError("Swarm result is missing a required field")
    if not all(key in allowed_keys for key in value):
        raise ValueError("Swarm result contains an unknown field")
    result = value
    return result


def _required_string(payload: Mapping[str, JsonValue], key: str) -> str:
    """Extract a required source string without coercion.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
    Return:
        Exact source string.
    """
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError(f"Swarm field {key} must be a string")
    result = value
    return result


def _optional_string(value: JsonValue | None) -> str | None:
    """Normalize a source-omitted nullable string.

    Args:
        value: Source string or null/omission.
    Return:
        Source string or None.
    """
    if value is None:
        result = None
    elif isinstance(value, str):
        result = value
    else:
        raise ValueError("Swarm nullable string field must be a string or null")
    return result


def _optional_uuid(value: JsonValue | None) -> UUID | None:
    """Normalize a source-omitted nullable UUID.

    Args:
        value: Source UUID string or null/omission.
    Return:
        Parsed UUID or None.
    """
    if value is None:
        result = None
    else:
        result = parse_wire_uuid(value=value)
    return result


def _optional_int(value: JsonValue | None) -> UInt64 | None:
    """Normalize a source-omitted nullable unsigned integer.

    Args:
        value: Source integer or null/omission.
    Return:
        Exact integer or None.
    """
    if value is None:
        result = None
    elif type(value) is int and 0 <= value <= 2**64 - 1:
        result = value
    else:
        raise ValueError("Swarm nullable sequence field must be an unsigned integer or null")
    return result


def _required_uuid(payload: Mapping[str, JsonValue], key: str) -> UUID:
    """Extract a required source UUID value.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
    Return:
        Parsed Python UUID.
    """
    value = payload[key]
    result = parse_wire_uuid(value=value)
    return result


def _required_bool(payload: Mapping[str, JsonValue], key: str) -> bool:
    """Extract a required strict source boolean.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
    Return:
        Exact source boolean.
    """
    value = payload[key]
    if type(value) is not bool:
        raise ValueError(f"Swarm field {key} must be a boolean")
    result = value
    return result


def _required_int(payload: Mapping[str, JsonValue], key: str) -> Int64:
    """Extract a required signed-64 source integer.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
    Return:
        Exact source integer.
    """
    value = payload[key]
    if type(value) is not int or not -(2**63) <= value <= 2**63 - 1:
        raise ValueError(f"Swarm field {key} must be a signed-64 integer")
    result: Int64 = value
    return result


def _required_positive_int(payload: Mapping[str, JsonValue], key: str) -> SwarmRevision:
    """Extract a positive unsigned-64 source revision.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
    Return:
        Positive source run revision.
    """
    value = payload[key]
    if type(value) is not int or not 1 <= value <= 2**64 - 1:
        raise ValueError(f"Swarm field {key} must be a positive unsigned-64 revision")
    result: SwarmRevision = value
    return result


def _required_uint32(payload: Mapping[str, JsonValue], key: str) -> UInt32:
    """Extract a required unsigned-32 source integer.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
    Return:
        Exact unsigned-32 source integer.
    """
    value = payload[key]
    if type(value) is not int or not 0 <= value <= 2**32 - 1:
        raise ValueError(f"Swarm field {key} must be an unsigned-32 integer")
    result: UInt32 = value
    return result


def _required_uint8(payload: Mapping[str, JsonValue], key: str) -> SwarmUInt8:
    """Extract a required unsigned-8 source integer.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
    Return:
        Exact unsigned-8 source integer.
    """
    value = payload[key]
    if type(value) is not int or not 0 <= value <= 255:
        raise ValueError(f"Swarm field {key} must be an unsigned-8 integer")
    result: SwarmUInt8 = value
    return result


def _required_uint64(payload: Mapping[str, JsonValue], key: str) -> UInt64:
    """Extract a required unsigned-64 source integer.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
    Return:
        Exact unsigned-64 source integer.
    """
    value = payload[key]
    if type(value) is not int or not 0 <= value <= 2**64 - 1:
        raise ValueError(f"Swarm field {key} must be an unsigned-64 integer")
    result: UInt64 = value
    return result


def _required_enum[EnumT: StrEnum](
    payload: Mapping[str, JsonValue],
    key: str,
    enum_type: type[EnumT],
) -> EnumT:
    """Extract a canonical source StrEnum value.

    Args:
        payload: Validated source JSON mapping.
        key: Required source key.
        enum_type: Canonical source enum type.
    Return:
        Exact declared enum member.
    """
    value = payload[key]
    if not isinstance(value, str):
        raise ValueError(f"Swarm field {key} must be a canonical string enum")
    result = parse_wire_enum(enum_type=enum_type, value=value)
    return result
