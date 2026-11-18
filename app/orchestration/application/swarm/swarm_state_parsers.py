"""Source-shape parsers for shared Orchestration Swarm leaf records."""

from functools import partial

from pydantic import JsonValue

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    PrincipalIdentityDto,
)
from app.orchestration.application.inner_dto.swarm.swarm_state_inner_dto import (
    DagNodeHybridTargetDto,
    SwarmBoardMessageDto,
    SwarmChannelDto,
    SwarmChannelSubscriptionDto,
    SwarmDoorbellDto,
    SwarmMemberDto,
    SwarmMemberIdentityDto,
    SwarmRunDto,
    SwarmRunModeDto,
)
from app.orchestration.application.orchestration_wire_parsers import (
    UINT8_MAX,
    UINT32_MAX,
    UINT64_MAX,
    parse_wire_bool,
    parse_wire_int,
    parse_wire_str,
    require_wire_object,
    wire_optional,
)
from app.orchestration.schema.types.orchestration_types import UInt32, UInt64
from app.orchestration.schema.types.swarm_types import SwarmUInt8
from app.shared.ingredient_element.orchestration.principal_enums import PrincipalKindEnum
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmDoorbellReasonEnum,
    SwarmMemberStateEnum,
    SwarmRoleKindEnum,
    SwarmRunModeEnum,
    SwarmRunStateEnum,
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


def _swarm_object(
    value: JsonValue,
    required_keys: tuple[str, ...],
    optional_keys: tuple[str, ...] = (),
) -> JsonObject:
    """Require one Swarm wire JSON object with only its declared keys.

    Args:
        value: Decoded JSON value.
        required_keys: Keys required by the Rust wire type.
        optional_keys: Keys source-omitted while serializing None.
    Return:
        Validated JSON object mapping.
    """
    result = require_wire_object(
        payload=value,
        required_keys=required_keys,
        optional_keys=optional_keys,
        label="Swarm result",
    )
    return result


def _uint8(payload: JsonObject, key: str) -> SwarmUInt8:
    """Parse one required unsigned-8 Swarm wire field.

    Args:
        payload: Validated source JSON object.
        key: Required field key.
    Return:
        Validated unsigned-8 integer.
    """
    result = parse_wire_int(value=payload[key], minimum=0, maximum=UINT8_MAX, label=key)
    return result


def _uint32(payload: JsonObject, key: str) -> UInt32:
    """Parse one required unsigned-32 Swarm wire field.

    Args:
        payload: Validated source JSON object.
        key: Required field key.
    Return:
        Validated unsigned-32 integer.
    """
    result = parse_wire_int(value=payload[key], minimum=0, maximum=UINT32_MAX, label=key)
    return result


def _uint64(payload: JsonObject, key: str) -> UInt64:
    """Parse one required unsigned-64 Swarm wire field.

    Args:
        payload: Validated source JSON object.
        key: Required field key.
    Return:
        Validated unsigned-64 integer.
    """
    result = parse_wire_int(value=payload[key], minimum=0, maximum=UINT64_MAX, label=key)
    return result


def parse_dag_node_hybrid_target(value: JsonValue) -> DagNodeHybridTargetDto:
    """Parse one source DAG-node hybrid target record.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable DAG-node hybrid target DTO.
    """
    payload = _swarm_object(
        value=value,
        required_keys=(
            "goalId",
            "dagRevision",
            "nodeId",
            "declaredWriteManifestBlake3Hex",
        ),
    )
    result = DagNodeHybridTargetDto(
        goal_id=parse_wire_uuid(value=payload["goalId"]),
        dag_revision=parse_wire_int(value=payload["dagRevision"], label="dagRevision"),
        node_id=parse_wire_uuid(value=payload["nodeId"]),
        declared_write_manifest_blake3_hex=parse_wire_str(
            value=payload["declaredWriteManifestBlake3Hex"],
            label="declaredWriteManifestBlake3Hex",
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
    payload = _swarm_object(value=value, required_keys=("kind",), optional_keys=("hybridTarget",))
    hybrid_target = wire_optional(
        value=payload.get("hybridTarget"),
        parser=parse_dag_node_hybrid_target,
    )
    result = SwarmRunModeDto(
        kind=parse_wire_enum(enum_type=SwarmRunModeEnum, value=payload["kind"]),
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
    payload = _swarm_object(
        value=value, required_keys=_RUN_REQUIRED_KEYS, optional_keys=_RUN_OPTIONAL_KEYS
    )
    result = SwarmRunDto(
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        workspace_id=parse_wire_uuid(value=payload["workspaceId"]),
        title=parse_wire_str(value=payload["title"], label="title"),
        mode=parse_swarm_run_mode(value=payload["mode"]),
        state=parse_wire_enum(enum_type=SwarmRunStateEnum, value=payload["state"]),
        max_members=_uint32(payload=payload, key="maxMembers"),
        max_spawn_depth=_uint8(payload=payload, key="maxSpawnDepth"),
        max_total_turns=_uint64(payload=payload, key="maxTotalTurns"),
        total_turns_used=_uint64(payload=payload, key="totalTurnsUsed"),
        required_verifier_quorum=_uint32(payload=payload, key="requiredVerifierQuorum"),
        allow_worker_all_mention=parse_wire_bool(
            value=payload["allowWorkerAllMention"], label="allowWorkerAllMention"
        ),
        baseline_commit_oid=parse_wire_str(
            value=payload["baselineCommitOid"], label="baselineCommitOid"
        ),
        baseline_tree_blake3_hex=parse_wire_str(
            value=payload["baselineTreeBlake3Hex"], label="baselineTreeBlake3Hex"
        ),
        converged_commit_oid=wire_optional(
            value=payload.get("convergedCommitOid"),
            parser=partial(parse_wire_str, label="convergedCommitOid"),
        ),
        converged_tree_blake3_hex=wire_optional(
            value=payload.get("convergedTreeBlake3Hex"),
            parser=partial(parse_wire_str, label="convergedTreeBlake3Hex"),
        ),
        converged_diff_digest_hex=wire_optional(
            value=payload.get("convergedDiffDigestHex"),
            parser=partial(parse_wire_str, label="convergedDiffDigestHex"),
        ),
        stall_nudge_count=_uint32(payload=payload, key="stallNudgeCount"),
        settlement_request_id=wire_optional(
            value=payload.get("settlementRequestId"), parser=parse_wire_uuid
        ),
        revision=parse_wire_int(
            value=payload["revision"], minimum=1, maximum=UINT64_MAX, label="revision"
        ),
        created_at_ms=parse_wire_int(value=payload["createdAtMs"], label="createdAtMs"),
        updated_at_ms=parse_wire_int(value=payload["updatedAtMs"], label="updatedAtMs"),
        replayed=parse_wire_bool(value=payload["replayed"], label="replayed"),
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
    payload = _swarm_object(
        value=value,
        required_keys=("channelId", "swarmRunId", "workspaceId", "name", "createdAtMs"),
        optional_keys=_CHANNEL_OPTIONAL_KEYS,
    )
    result = SwarmChannelDto(
        channel_id=parse_wire_uuid(value=payload["channelId"]),
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        workspace_id=parse_wire_uuid(value=payload["workspaceId"]),
        name=parse_wire_str(value=payload["name"], label="name"),
        purpose=wire_optional(
            value=payload.get("purpose"), parser=partial(parse_wire_str, label="purpose")
        ),
        created_by_member_id=wire_optional(
            value=payload.get("createdByMemberId"), parser=parse_wire_uuid
        ),
        created_at_ms=parse_wire_int(value=payload["createdAtMs"], label="createdAtMs"),
    )
    return result


def parse_swarm_channel_subscription(value: JsonValue) -> SwarmChannelSubscriptionDto:
    """Parse one source Swarm channel subscription edge.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable subscription DTO.
    """
    payload = _swarm_object(value=value, required_keys=("channelId", "memberId"))
    result = SwarmChannelSubscriptionDto(
        channel_id=parse_wire_uuid(value=payload["channelId"]),
        member_id=parse_wire_uuid(value=payload["memberId"]),
    )
    return result


def parse_swarm_doorbell(value: JsonValue) -> SwarmDoorbellDto:
    """Parse one pending source Swarm wakeup doorbell.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable doorbell DTO.
    """
    payload = _swarm_object(
        value=value,
        required_keys=("swarmRunId", "targetMemberId", "sequence", "reason", "enqueuedAtMs"),
    )
    result = SwarmDoorbellDto(
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        target_member_id=parse_wire_uuid(value=payload["targetMemberId"]),
        sequence=_uint64(payload=payload, key="sequence"),
        reason=parse_wire_enum(enum_type=SwarmDoorbellReasonEnum, value=payload["reason"]),
        enqueued_at_ms=parse_wire_int(value=payload["enqueuedAtMs"], label="enqueuedAtMs"),
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
    payload = _swarm_object(value=value, required_keys=("profileId", "participantId", "principal"))
    principal = _parse_principal_identity(value=payload["principal"])
    result = SwarmMemberIdentityDto(
        profile_id=parse_wire_uuid(value=payload["profileId"]),
        participant_id=parse_wire_uuid(value=payload["participantId"]),
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
    payload = _swarm_object(
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
        member_id=parse_wire_uuid(value=payload["memberId"]),
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        workspace_id=parse_wire_uuid(value=payload["workspaceId"]),
        roster_name=parse_wire_str(value=payload["rosterName"], label="rosterName"),
        role_kind=parse_wire_enum(enum_type=SwarmRoleKindEnum, value=payload["roleKind"]),
        parent_member_id=wire_optional(value=payload.get("parentMemberId"), parser=parse_wire_uuid),
        spawn_depth=_uint8(payload=payload, key="spawnDepth"),
        workspace_mode=parse_wire_enum(
            enum_type=SwarmWorkspaceModeEnum, value=payload["workspaceMode"]
        ),
        worktree_path=wire_optional(
            value=payload.get("worktreePath"),
            parser=partial(parse_wire_str, label="worktreePath"),
        ),
        member_state=parse_wire_enum(enum_type=SwarmMemberStateEnum, value=payload["memberState"]),
        identity=parse_swarm_member_identity(value=payload["identity"]),
        committed_seen_seq=_uint64(payload=payload, key="committedSeenSeq"),
        inflight_target_seq=_uint64(payload=payload, key="inflightTargetSeq"),
        active_snapshot_id=wire_optional(
            value=payload.get("activeSnapshotId"), parser=parse_wire_uuid
        ),
        attempt_epoch=_uint64(payload=payload, key="attemptEpoch"),
        turns_used=_uint64(payload=payload, key="turnsUsed"),
        ping_pong_peer_id=wire_optional(
            value=payload.get("pingPongPeerId"), parser=parse_wire_uuid
        ),
        ping_pong_streak=_uint32(payload=payload, key="pingPongStreak"),
        last_output_commit_oid=wire_optional(
            value=payload.get("lastOutputCommitOid"),
            parser=partial(parse_wire_str, label="lastOutputCommitOid"),
        ),
        last_output_tree_blake3_hex=wire_optional(
            value=payload.get("lastOutputTreeBlake3Hex"),
            parser=partial(parse_wire_str, label="lastOutputTreeBlake3Hex"),
        ),
        created_at_ms=parse_wire_int(value=payload["createdAtMs"], label="createdAtMs"),
        updated_at_ms=parse_wire_int(value=payload["updatedAtMs"], label="updatedAtMs"),
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
    payload = _swarm_object(
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
        message_id=parse_wire_uuid(value=payload["messageId"]),
        workspace_id=parse_wire_uuid(value=payload["workspaceId"]),
        sequence=_uint64(payload=payload, key="sequence"),
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        channel_id=parse_wire_uuid(value=payload["channelId"]),
        channel_name=parse_wire_str(value=payload["channelName"], label="channelName"),
        author_member_id=wire_optional(value=payload.get("authorMemberId"), parser=parse_wire_uuid),
        author_roster_name=parse_wire_str(
            value=payload["authorRosterName"], label="authorRosterName"
        ),
        author_epoch=wire_optional(
            value=payload.get("authorEpoch"),
            parser=partial(parse_wire_int, minimum=0, maximum=UINT64_MAX, label="authorEpoch"),
        ),
        body=parse_wire_str(value=payload["body"], label="body"),
        submitted_at_ms=parse_wire_int(value=payload["submittedAtMs"], label="submittedAtMs"),
    )
    return result


def _parse_principal_identity(value: JsonValue) -> PrincipalIdentityDto:
    """Parse a principal identity and source-defaulted ID.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable principal identity DTO.
    """
    payload = _swarm_object(value=value, required_keys=("kind",), optional_keys=("id",))
    principal_id = "" if "id" not in payload else parse_wire_str(value=payload["id"], label="id")
    result = PrincipalIdentityDto(
        kind=parse_wire_enum(enum_type=PrincipalKindEnum, value=payload["kind"]),
        id=principal_id,
    )
    return result
