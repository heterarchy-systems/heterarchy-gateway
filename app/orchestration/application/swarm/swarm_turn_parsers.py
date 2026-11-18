"""Wire parsers and identity validators for the Native Swarm turn lane."""

from functools import partial
from uuid import UUID

from pydantic import JsonValue

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPreferenceDto,
)
from app.orchestration.application.inner_dto.swarm.swarm_state_inner_dto import SwarmMemberDto
from app.orchestration.application.inner_dto.swarm.swarm_turn_inner_dto import (
    DispatchedTurnDispositionDto,
    DispatchedTurnSupervisionDto,
    DispatchSwarmTurnInnerDto,
    SwarmModelSwitchInnerDto,
    SwarmWakeupBatchDto,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import SwarmMemberDict
from app.orchestration.application.inner_dto.types.swarm.swarm_turn_types import (
    DispatchSwarmTurnResponseDict,
    SwarmModelSwitchResponseDict,
    SwarmWakeupBatchDict,
)
from app.orchestration.application.orchestration_wire_parsers import (
    INT32_MAX,
    INT32_MIN,
    INT64_MAX,
    UINT64_MAX,
    parse_wire_array,
    parse_wire_bool,
    parse_wire_int,
    parse_wire_str,
    parse_wire_str_tuple,
    require_wire_object,
    wire_optional,
)
from app.orchestration.application.swarm.swarm_state_parsers import (
    parse_swarm_board_message,
    parse_swarm_member,
)
from app.orchestration.application.swarm.swarm_turn_snapshot_parsers import (
    parse_committed_snapshot,
    parse_launch_ledger_record,
)
from app.shared.ingredient_element.orchestration.profile_enums import CliEngineEnum
from app.shared.types.threaded_mapping import threaded_map
from app.shared.types.wire_scalar_types import parse_wire_enum, parse_wire_uuid


def parse_claim_result(
    value: JsonValue,
    *,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
    snapshot_id: UUID,
) -> SwarmWakeupBatchDict:
    """Parse and correlate one wakeup claim result.

    Args:
        value: Decoded Orchestration JSON result.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
        snapshot_id: Snapshot identity supplied by the request.
    Return:
        Closed typed source wakeup response.
    """
    batch = _parse_wakeup_batch(value=value)
    _require_wakeup_context(
        batch=batch,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        snapshot_id=snapshot_id,
    )
    result = batch.to_dict()
    return result


def parse_member_result(
    value: JsonValue,
    *,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
) -> SwarmMemberDict:
    """Parse and correlate a member mutation receipt.

    Args:
        value: Decoded Orchestration JSON result.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
    Return:
        Closed typed Swarm member result.
    """
    member = parse_swarm_member(value=value)
    _require_member_scope(
        member=member, workspace_id=workspace_id, swarm_run_id=swarm_run_id, member_id=member_id
    )
    result = member.to_dict()
    return result


def parse_dispatch_result(
    value: JsonValue,
    *,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
    snapshot_id: UUID,
) -> DispatchSwarmTurnResponseDict:
    """Parse and correlate the full supervised dispatch receipt.

    Args:
        value: Decoded Orchestration JSON result.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
        snapshot_id: Snapshot identity supplied by the request.
    Return:
        Closed typed dispatch result.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=(
            "wakeupBatch",
            "committedSnapshot",
            "supervision",
            "disposition",
            "usedParentSpawnerSlot",
        ),
    )
    response = DispatchSwarmTurnInnerDto(
        wakeup_batch=_parse_wakeup_batch(value=payload["wakeupBatch"]),
        committed_snapshot=parse_committed_snapshot(value=payload["committedSnapshot"]),
        supervision=_parse_supervision(value=payload["supervision"]),
        disposition=_parse_disposition(value=payload["disposition"]),
        used_parent_spawner_slot=parse_wire_bool(
            value=payload["usedParentSpawnerSlot"], label="usedParentSpawnerSlot"
        ),
    )
    _require_dispatch_context(
        response=response,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        snapshot_id=snapshot_id,
    )
    result = response.to_dict()
    return result


def parse_model_switch_result(
    value: JsonValue,
    *,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
) -> SwarmModelSwitchResponseDict:
    """Parse and correlate a source model-switch receipt.

    Args:
        value: Decoded Orchestration JSON result.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
    Return:
        Closed typed model-switch result.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=("member", "profileId", "profileRevision", "resolvedPreference"),
    )
    preference = _parse_execution_preference(value=payload["resolvedPreference"])
    response = SwarmModelSwitchInnerDto(
        member=parse_swarm_member(value=payload["member"]),
        profile_id=parse_wire_uuid(value=payload["profileId"]),
        profile_revision=parse_wire_int(
            value=payload["profileRevision"],
            minimum=1,
            maximum=INT64_MAX,
            label="profileRevision",
        ),
        resolved_preference=preference,
    )
    _require_member_scope(
        member=response.member,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
    )
    if response.profile_id.int == 0 or response.profile_revision <= 0:
        raise ValueError("Model-switch response contains an invalid Profile identity or revision")
    result = response.to_dict()
    return result


def _require_member_scope(
    member: SwarmMemberDto,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
) -> None:
    """Enforce the source client member identity readback contract.

    Args:
        member: Parsed source member projection.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
    Return:
        None.
    """
    observed = (member.workspace_id, member.swarm_run_id, member.member_id)
    expected = (workspace_id, swarm_run_id, member_id)
    if observed != expected:
        raise ValueError("Swarm member response escaped the requested identity scope")


def _parse_wakeup_batch(value: JsonValue) -> SwarmWakeupBatchDto:
    """Parse one exact source wakeup batch and its bounded board messages.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable source wakeup batch DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=(
            "swarmRunId",
            "member",
            "snapshotId",
            "committedSeenSeq",
            "inflightTargetSeq",
            "messages",
            "totalBodyBytes",
        ),
    )
    message_values = parse_wire_array(value=payload["messages"], label="messages")
    messages = tuple(threaded_map(function=parse_swarm_board_message, values=message_values))
    result = SwarmWakeupBatchDto(
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        member=parse_swarm_member(value=payload["member"]),
        snapshot_id=parse_wire_uuid(value=payload["snapshotId"]),
        committed_seen_seq=parse_wire_int(
            value=payload["committedSeenSeq"],
            minimum=0,
            maximum=UINT64_MAX,
            label="committedSeenSeq",
        ),
        inflight_target_seq=parse_wire_int(
            value=payload["inflightTargetSeq"],
            minimum=0,
            maximum=UINT64_MAX,
            label="inflightTargetSeq",
        ),
        messages=messages,
        total_body_bytes=parse_wire_int(
            value=payload["totalBodyBytes"],
            minimum=0,
            maximum=UINT64_MAX,
            label="totalBodyBytes",
        ),
    )
    return result


def _require_wakeup_context(
    batch: SwarmWakeupBatchDto,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
    snapshot_id: UUID,
) -> None:
    """Check the source client wakeup and member identity correlations.

    Args:
        batch: Parsed wakeup batch.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
        snapshot_id: Snapshot identity supplied by the request.
    Return:
        None.
    """
    observed = (batch.swarm_run_id, batch.snapshot_id)
    expected = (swarm_run_id, snapshot_id)
    if observed != expected:
        raise ValueError("Swarm wakeup response escaped the requested run snapshot")
    _require_member_scope(
        member=batch.member,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
    )


def _parse_execution_preference(value: JsonValue) -> ExecutionPreferenceDto:
    """Parse a source execution preference and normalize nullable omissions.

    Args:
        value: Decoded Orchestration execution-preference object.
    Return:
        Immutable validated execution preference DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=("cliEngine", "preferredModel", "capabilities"),
        optional_keys=("preferredReasoning", "rolePromptDigestHex"),
    )
    result = ExecutionPreferenceDto(
        cli_engine=parse_wire_enum(enum_type=CliEngineEnum, value=payload["cliEngine"]),
        preferred_model=parse_wire_str(value=payload["preferredModel"], label="preferredModel"),
        preferred_reasoning=wire_optional(
            value=payload.get("preferredReasoning"),
            parser=partial(parse_wire_str, label="preferredReasoning"),
        ),
        capabilities=parse_wire_str_tuple(value=payload["capabilities"], label="capabilities"),
        role_prompt_digest_hex=wire_optional(
            value=payload.get("rolePromptDigestHex"),
            parser=partial(parse_wire_str, label="rolePromptDigestHex"),
        ),
    )
    return result


def _parse_supervision(value: JsonValue) -> DispatchedTurnSupervisionDto:
    """Parse one source supervision projection and launch-ledger record.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable dispatch supervision DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=("status", "ledger"),
        optional_keys=("exitCode", "termination", "unknownReason"),
    )
    result = DispatchedTurnSupervisionDto(
        status=parse_wire_str(value=payload["status"], label="status"),
        ledger=parse_launch_ledger_record(value=payload["ledger"]),
        exit_code=wire_optional(
            value=payload.get("exitCode"),
            parser=partial(parse_wire_int, minimum=INT32_MIN, maximum=INT32_MAX, label="exitCode"),
        ),
        termination=wire_optional(
            value=payload.get("termination"),
            parser=partial(parse_wire_str, label="termination"),
        ),
        unknown_reason=wire_optional(
            value=payload.get("unknownReason"),
            parser=partial(parse_wire_str, label="unknownReason"),
        ),
    )
    return result


def _parse_disposition(value: JsonValue) -> DispatchedTurnDispositionDto:
    """Parse one source-owned member disposition.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable member disposition DTO.
    """
    payload = require_wire_object(
        payload=value, required_keys=("kind", "member", "timedOut"), optional_keys=("exitCode",)
    )
    result = DispatchedTurnDispositionDto(
        kind=parse_wire_str(value=payload["kind"], label="kind"),
        member=parse_swarm_member(value=payload["member"]),
        exit_code=wire_optional(
            value=payload.get("exitCode"),
            parser=partial(parse_wire_int, minimum=INT32_MIN, maximum=INT32_MAX, label="exitCode"),
        ),
        timed_out=parse_wire_bool(value=payload["timedOut"], label="timedOut"),
    )
    return result


def _require_dispatch_context(
    response: DispatchSwarmTurnInnerDto,
    workspace_id: UUID,
    swarm_run_id: UUID,
    member_id: UUID,
    snapshot_id: UUID,
) -> None:
    """Apply exactly the Rust client dispatch snapshot and member readback checks.

    Args:
        response: Parsed dispatch receipt.
        workspace_id: Workspace identity selected by the route.
        swarm_run_id: Swarm run identity selected by the route.
        member_id: Member identity selected by the route.
        snapshot_id: Snapshot identity supplied by the request.
    Return:
        None.
    """
    batch = response.wakeup_batch
    _require_wakeup_context(
        batch=batch,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
        snapshot_id=snapshot_id,
    )
    snapshot = response.committed_snapshot
    if (snapshot.snapshot_id, snapshot.workspace_id) != (snapshot_id, workspace_id):
        raise ValueError("Committed snapshot response escaped the requested scope")
    ledger = response.supervision.ledger
    if (ledger.snapshot_id, ledger.workspace_id) != (snapshot_id, workspace_id):
        raise ValueError("Launch ledger response escaped the requested snapshot scope")
    if not response.supervision.status or not response.disposition.kind:
        raise ValueError("Dispatch response contains an empty supervision or disposition kind")
    _require_member_scope(
        member=response.disposition.member,
        workspace_id=workspace_id,
        swarm_run_id=swarm_run_id,
        member_id=member_id,
    )
