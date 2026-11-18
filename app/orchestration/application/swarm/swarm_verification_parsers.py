"""Source-shape parsers for Orchestration Swarm verification panels and gates."""

from pydantic import JsonValue

from app.orchestration.application.inner_dto.swarm.swarm_state_inner_dto import (
    SwarmConvergenceGateDto,
    SwarmPanelSeatDto,
    SwarmVerdictDto,
    SwarmVerificationPanelDto,
)
from app.orchestration.application.orchestration_wire_parsers import (
    UINT32_MAX,
    parse_wire_bool,
    parse_wire_int,
    parse_wire_object_items,
    parse_wire_str,
    require_wire_object,
)
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmPanelSeatKindEnum,
    SwarmVerdictOutcomeEnum,
)
from app.shared.types.wire_scalar_types import parse_wire_enum, parse_wire_uuid

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


def parse_swarm_panel_seat(value: JsonValue) -> SwarmPanelSeatDto:
    """Parse one source Swarm verification panel seat.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable panel seat DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=("memberId", "seatKind", "assignedAtMs"),
        label="Swarm result",
    )
    result = SwarmPanelSeatDto(
        member_id=parse_wire_uuid(value=payload["memberId"]),
        seat_kind=parse_wire_enum(enum_type=SwarmPanelSeatKindEnum, value=payload["seatKind"]),
        assigned_at_ms=parse_wire_int(value=payload["assignedAtMs"], label="assignedAtMs"),
    )
    return result


def parse_swarm_verification_panel(value: JsonValue) -> SwarmVerificationPanelDto:
    """Parse one source Swarm verification panel with nested seats.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable verification panel DTO.
    """
    payload = require_wire_object(payload=value, required_keys=_PANEL_KEYS, label="Swarm result")
    seats = parse_wire_object_items(
        value=payload["seats"], parser=parse_swarm_panel_seat, label="seats"
    )
    result = SwarmVerificationPanelDto(
        panel_id=parse_wire_uuid(value=payload["panelId"]),
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        workspace_id=parse_wire_uuid(value=payload["workspaceId"]),
        required_quorum=parse_wire_int(
            value=payload["requiredQuorum"],
            minimum=0,
            maximum=UINT32_MAX,
            label="requiredQuorum",
        ),
        auto_created=parse_wire_bool(value=payload["autoCreated"], label="autoCreated"),
        seats=seats,
        created_at_ms=parse_wire_int(value=payload["createdAtMs"], label="createdAtMs"),
        replayed=parse_wire_bool(value=payload["replayed"], label="replayed"),
    )
    return result


def parse_swarm_verdict(value: JsonValue) -> SwarmVerdictDto:
    """Parse one source immutable Swarm verifier verdict.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable Swarm verdict DTO.
    """
    payload = require_wire_object(
        payload=value,
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
        label="Swarm result",
    )
    result = SwarmVerdictDto(
        verdict_id=parse_wire_uuid(value=payload["verdictId"]),
        request_id=parse_wire_uuid(value=payload["requestId"]),
        panel_id=parse_wire_uuid(value=payload["panelId"]),
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        verifier_member_id=parse_wire_uuid(value=payload["verifierMemberId"]),
        outcome=parse_wire_enum(enum_type=SwarmVerdictOutcomeEnum, value=payload["outcome"]),
        reviewed_diff_digest_hex=parse_wire_str(
            value=payload["reviewedDiffDigestHex"], label="reviewedDiffDigestHex"
        ),
        rationale=parse_wire_str(value=payload["rationale"], label="rationale"),
        recorded_at_ms=parse_wire_int(value=payload["recordedAtMs"], label="recordedAtMs"),
        replayed=parse_wire_bool(value=payload["replayed"], label="replayed"),
    )
    return result


def parse_swarm_convergence_gate(value: JsonValue) -> SwarmConvergenceGateDto:
    """Parse one source verified Swarm convergence gate.

    Args:
        value: Decoded Orchestration JSON value.
    Return:
        Immutable convergence gate DTO.
    """
    payload = require_wire_object(
        payload=value,
        required_keys=(
            "panelId",
            "swarmRunId",
            "convergedDiffDigestHex",
            "requiredQuorum",
            "acceptedVerdicts",
        ),
        label="Swarm result",
    )
    verdicts = parse_wire_object_items(
        value=payload["acceptedVerdicts"],
        parser=parse_swarm_verdict,
        label="acceptedVerdicts",
    )
    result = SwarmConvergenceGateDto(
        panel_id=parse_wire_uuid(value=payload["panelId"]),
        swarm_run_id=parse_wire_uuid(value=payload["swarmRunId"]),
        converged_diff_digest_hex=parse_wire_str(
            value=payload["convergedDiffDigestHex"], label="convergedDiffDigestHex"
        ),
        required_quorum=parse_wire_int(
            value=payload["requiredQuorum"],
            minimum=0,
            maximum=UINT32_MAX,
            label="requiredQuorum",
        ),
        accepted_verdicts=verdicts,
    )
    return result
