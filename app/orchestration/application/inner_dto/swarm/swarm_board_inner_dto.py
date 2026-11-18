"""Typed request and response DTOs for Native Swarm board operations."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.orchestration.application.inner_dto.swarm.swarm_state_inner_dto import (
    SwarmBoardMessageDto,
    SwarmConvergenceGateDto,
    SwarmMemberDto,
    SwarmRunDto,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_board_types import (
    AbortSwarmRunRequestDict,
    ConvergeSwarmRequestDict,
    ConvergeSwarmResponseDict,
    CreateSwarmPanelRequestDict,
    PostSwarmMessageRequestDict,
    PostSwarmMessageResponseDict,
    RecordSwarmVerdictRequestDict,
    SettleSwarmRequestDict,
    SwarmBoardPageResponseDict,
    SwarmStallCheckRequestDict,
    SwarmStallCheckResponseDict,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt32, UInt64
from app.orchestration.schema.types.swarm_types import SwarmRunState, SwarmVerdictOutcomeInput


@dataclass(frozen=True, slots=True, kw_only=True)
class PostSwarmMessageCommandDto:
    """Immutable command to post a Swarm board message."""

    message_id: UUID
    channel_id: UUID | None
    author_member_id: UUID | None
    body: str

    def to_dict(self) -> PostSwarmMessageRequestDict:
        """Serialize message command with source omission semantics.

        Args:
            None.
        Return:
            Source-shaped typed message request.
        """
        result = PostSwarmMessageRequestDict(
            messageId=str(self.message_id),
            body=self.body,
        )
        if self.channel_id is not None:
            result["channelId"] = str(self.channel_id)
        if self.author_member_id is not None:
            result["authorMemberId"] = str(self.author_member_id)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateSwarmPanelCommandDto:
    """Immutable command to create a verification panel."""

    request_id: UUID
    author_member_ids: tuple[UUID, ...]
    verifier_member_ids: tuple[UUID, ...]
    required_quorum: UInt32

    def to_dict(self) -> CreateSwarmPanelRequestDict:
        """Serialize the complete typed panel request.

        Args:
            None.
        Return:
            Source-shaped typed verification panel request.
        """
        result = CreateSwarmPanelRequestDict(
            requestId=str(self.request_id),
            authorMemberIds=[str(member_id) for member_id in self.author_member_ids],
            verifierMemberIds=[str(member_id) for member_id in self.verifier_member_ids],
            requiredQuorum=self.required_quorum,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class RecordSwarmVerdictCommandDto:
    """Immutable command to record a Swarm verifier verdict."""

    request_id: UUID
    panel_id: UUID | None
    verifier_member_id: UUID
    outcome: SwarmVerdictOutcomeInput
    reviewed_diff_digest_hex: str
    rationale: str

    def to_dict(self) -> RecordSwarmVerdictRequestDict:
        """Serialize the verdict request with its optional panel identity.

        Args:
            None.
        Return:
            Source-shaped typed verdict request.
        """
        result = RecordSwarmVerdictRequestDict(
            requestId=str(self.request_id),
            verifierMemberId=str(self.verifier_member_id),
            outcome=self.outcome,
            reviewedDiffDigestHex=self.reviewed_diff_digest_hex,
            rationale=self.rationale,
        )
        if self.panel_id is not None:
            result["panelId"] = str(self.panel_id)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ConvergeSwarmCommandDto:
    """Immutable command to converge a Swarm run."""

    request_id: UUID
    converged_commit_oid: str
    converged_tree_blake3_hex: str
    converged_diff_digest_hex: str
    target_state: str | None
    stage_candidate_only: bool

    def to_dict(self) -> ConvergeSwarmRequestDict:
        """Serialize convergence request and omit absent target state.

        Args:
            None.
        Return:
            Source-shaped typed convergence request.
        """
        result = ConvergeSwarmRequestDict(
            requestId=str(self.request_id),
            convergedCommitOid=self.converged_commit_oid,
            convergedTreeBlake3Hex=self.converged_tree_blake3_hex,
            convergedDiffDigestHex=self.converged_diff_digest_hex,
            stageCandidateOnly=self.stage_candidate_only,
        )
        if self.target_state is not None:
            result["targetState"] = self.target_state
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SettleSwarmCommandDto:
    """Immutable command to settle a staged Swarm run."""

    request_id: UUID

    def to_dict(self) -> SettleSwarmRequestDict:
        """Serialize the complete typed settlement request.

        Args:
            None.
        Return:
            Source-shaped typed settlement request.
        """
        result = SettleSwarmRequestDict(requestId=str(self.request_id))
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class AbortSwarmRunCommandDto:
    """Immutable command for an explicit empty-body abort operation."""

    def to_dict(self) -> AbortSwarmRunRequestDict:
        """Serialize the empty typed abort request body.

        Args:
            None.
        Return:
            Source-shaped empty abort request.
        """
        result = AbortSwarmRunRequestDict()
        return result


def _stall_check_request_dict(command: SwarmStallCheckCommandDto) -> SwarmStallCheckRequestDict:
    """Build only source-present stall thresholds in a typed request body.

    Args:
        command: Immutable stall check command.
    Return:
        Request fields with None values omitted.
    """
    result = SwarmStallCheckRequestDict()
    if command.stall_grace_ms is not None:
        result["stallGraceMs"] = command.stall_grace_ms
    if command.max_stall_nudges is not None:
        result["maxStallNudges"] = command.max_stall_nudges
    if command.max_ping_pong_streak is not None:
        result["maxPingPongStreak"] = command.max_ping_pong_streak
    if command.max_member_turns is not None:
        result["maxMemberTurns"] = command.max_member_turns
    if command.observed_at_ms is not None:
        result["observedAtMs"] = command.observed_at_ms
    return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmStallCheckCommandDto:
    """Immutable input thresholds for one Swarm stall check."""

    stall_grace_ms: Int64 | None
    max_stall_nudges: UInt32 | None
    max_ping_pong_streak: UInt32 | None
    max_member_turns: UInt64 | None
    observed_at_ms: Int64 | None

    def to_dict(self) -> SwarmStallCheckRequestDict:
        """Serialize only present stall thresholds.

        Args:
            None.
        Return:
            Source-shaped typed stall check request.
        """
        optional_fields = _stall_check_request_dict(command=self)
        result = SwarmStallCheckRequestDict(**optional_fields)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class PostSwarmMessageResponseDto:
    """Immutable result of posting a Swarm board message."""

    message: SwarmBoardMessageDto
    woken_member_ids: tuple[UUID, ...]
    coalesced_doorbell_member_ids: tuple[UUID, ...]
    replayed: bool

    def to_dict(self) -> PostSwarmMessageResponseDict:
        """Serialize typed message post outcome.

        Args:
            None.
        Return:
            Complete typed message post response.
        """
        result = PostSwarmMessageResponseDict(
            message=self.message.to_dict(),
            wokenMemberIds=list(self.woken_member_ids),
            coalescedDoorbellMemberIds=list(self.coalesced_doorbell_member_ids),
            replayed=self.replayed,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmBoardPageResponseDto:
    """Immutable bounded page of Swarm board messages."""

    messages: tuple[SwarmBoardMessageDto, ...]
    next_after_sequence: UInt64 | None
    has_more: bool

    def to_dict(self) -> SwarmBoardPageResponseDict:
        """Serialize the complete typed message page.

        Args:
            None.
        Return:
            Complete typed Swarm board page.
        """
        result = SwarmBoardPageResponseDict(
            messages=[message.to_dict() for message in self.messages],
            nextAfterSequence=self.next_after_sequence,
            hasMore=self.has_more,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ConvergeSwarmResponseDto:
    """Immutable convergence or settlement response."""

    run: SwarmRunDto
    settled: bool
    gate: SwarmConvergenceGateDto | None

    def to_dict(self) -> ConvergeSwarmResponseDict:
        """Serialize convergence run and optional quorum gate.

        Args:
            None.
        Return:
            Complete typed convergence response.
        """
        gate = self.gate.to_dict() if self.gate is not None else None
        result = ConvergeSwarmResponseDict(
            run=self.run.to_dict(),
            settled=self.settled,
            gate=gate,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmStallCheckResponseDto:
    """Immutable deterministic stall and livelock report."""

    action: str
    run_state: SwarmRunState | None
    working_members: UInt64 | None
    target_member_id: UUID | None
    bottleneck_reason: str | None
    livelock_reason: str | None
    observed_ping_pong_streak: UInt32 | None
    observed_member_turns: UInt64 | None
    run: SwarmRunDto | None
    stopped_members: tuple[SwarmMemberDto, ...]
    emitted_message: SwarmBoardMessageDto | None

    def to_dict(self) -> SwarmStallCheckResponseDict:
        """Serialize the full required-null stall report.

        Args:
            None.
        Return:
            Complete typed stall report.
        """
        run = self.run.to_dict() if self.run is not None else None
        emitted_message = (
            self.emitted_message.to_dict() if self.emitted_message is not None else None
        )
        result = SwarmStallCheckResponseDict(
            action=self.action,
            runState=self.run_state,
            workingMembers=self.working_members,
            targetMemberId=self.target_member_id,
            bottleneckReason=self.bottleneck_reason,
            livelockReason=self.livelock_reason,
            observedPingPongStreak=self.observed_ping_pong_streak,
            observedMemberTurns=self.observed_member_turns,
            run=run,
            stoppedMembers=[member.to_dict() for member in self.stopped_members],
            emittedMessage=emitted_message,
        )
        return result
