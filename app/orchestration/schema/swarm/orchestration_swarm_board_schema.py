"""Strict schemas for Native Swarm board and convergence contracts."""

from typing import Annotated, Self
from uuid import UUID

from pydantic import AfterValidator, Field, model_validator

from app.orchestration.application.inner_dto.swarm_board_inner_dto import (
    AbortSwarmRunCommandDto,
    ConvergeSwarmCommandDto,
    CreateSwarmPanelCommandDto,
    PostSwarmMessageCommandDto,
    RecordSwarmVerdictCommandDto,
    SettleSwarmCommandDto,
    SwarmStallCheckCommandDto,
)
from app.orchestration.schema.swarm.orchestration_swarm_state_schema import (
    SwarmBoardMessageSchema,
    SwarmConvergenceGateSchema,
    SwarmMemberSchema,
    SwarmRunSchema,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt32, UInt64
from app.orchestration.schema.types.swarm_types import (
    NonNilSwarmUUID,
    NonZeroDigestHex,
    SwarmCommitOid,
    SwarmConvergenceTargetInput,
    SwarmRunState,
    SwarmVerdictOutcomeInput,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.filter_module.base_filter import BaseFilter
from app.shared.ingredient_element.orchestration.swarm_enums import SwarmConvergenceTargetEnum

_MAX_SWARM_BOARD_PAGE_SIZE = 128


def _require_nonblank_text(value: str) -> str:
    """Reject source-invalid blank text without changing the submitted value.

    Args:
        value: Strictly parsed source string.
    Return:
        Original nonblank source string.
    """
    if not value.strip():
        raise ValueError("Swarm text fields must not be blank")
    result = value
    return result


class PostSwarmMessageRequest(StrictSchemaModel):
    """Append one message to a Swarm board channel."""

    message_id: Annotated[
        NonNilSwarmUUID,
        Field(description="Client-selected message UUID.", alias="messageId"),
    ]
    channel_id: Annotated[
        NonNilSwarmUUID | None,
        Field(
            description="Optional channel UUID; null selects source default channel.",
            alias="channelId",
        ),
    ]
    author_member_id: Annotated[
        NonNilSwarmUUID | None,
        Field(
            description="Optional author member UUID; null selects the system author.",
            alias="authorMemberId",
        ),
    ]
    body: Annotated[
        str,
        Field(description="Nonblank message body."),
        AfterValidator(_require_nonblank_text),
    ]

    def to_inner_dto(self) -> PostSwarmMessageCommandDto:
        """Build the immutable message command.

        Args:
            None.
        Return:
            Typed message command DTO.
        """
        result = PostSwarmMessageCommandDto(
            message_id=self.message_id,
            channel_id=self.channel_id,
            author_member_id=self.author_member_id,
            body=self.body,
        )
        return result


class SwarmBoardMessagesFilter(BaseFilter):
    """Optional query filter for bounded incremental board reads."""

    since_sequence: Annotated[
        UInt64 | None,
        Field(description="Return messages after this sequence.", alias="sinceSequence"),
    ] = None
    channel_id: Annotated[
        NonNilSwarmUUID | None,
        Field(description="Optional channel UUID.", alias="channelId"),
    ] = None
    limit: Annotated[
        int | None,
        Field(
            description="Maximum page size from one through 128.",
            ge=1,
            le=_MAX_SWARM_BOARD_PAGE_SIZE,
        ),
    ] = None


class CreateSwarmVerificationPanelRequest(StrictSchemaModel):
    """Create a lineage-separated verification panel."""

    request_id: Annotated[
        NonNilSwarmUUID,
        Field(description="Idempotency request UUID.", alias="requestId"),
    ]
    author_member_ids: Annotated[
        list[NonNilSwarmUUID],
        Field(description="Panel author member UUIDs.", min_length=1, alias="authorMemberIds"),
    ]
    verifier_member_ids: Annotated[
        list[NonNilSwarmUUID],
        Field(
            description="Independent verifier member UUIDs.",
            min_length=1,
            alias="verifierMemberIds",
        ),
    ]
    required_quorum: Annotated[
        UInt32,
        Field(description="Required accepted verifier quorum.", ge=1, alias="requiredQuorum"),
    ]

    def to_inner_dto(self) -> CreateSwarmPanelCommandDto:
        """Build the immutable panel creation command.

        Args:
            None.
        Return:
            Typed panel creation command DTO.
        """
        result = CreateSwarmPanelCommandDto(
            request_id=self.request_id,
            author_member_ids=tuple(self.author_member_ids),
            verifier_member_ids=tuple(self.verifier_member_ids),
            required_quorum=self.required_quorum,
        )
        return result


class RecordSwarmVerdictRequest(StrictSchemaModel):
    """Record an immutable diff-digest-bound verifier verdict."""

    request_id: Annotated[
        NonNilSwarmUUID,
        Field(description="Idempotency request UUID.", alias="requestId"),
    ]
    panel_id: Annotated[
        NonNilSwarmUUID | None,
        Field(description="Optional verification panel UUID.", alias="panelId"),
    ]
    verifier_member_id: Annotated[
        NonNilSwarmUUID,
        Field(description="Submitting verifier member UUID.", alias="verifierMemberId"),
    ]
    outcome: Annotated[
        SwarmVerdictOutcomeInput,
        Field(description="Source-accepted verifier outcome."),
    ]
    reviewed_diff_digest_hex: Annotated[
        NonZeroDigestHex,
        Field(
            description="Nonzero lowercase SHA-256 digest reviewed.", alias="reviewedDiffDigestHex"
        ),
    ]
    rationale: Annotated[
        str,
        Field(description="Nonblank verifier rationale."),
        AfterValidator(_require_nonblank_text),
    ]

    def to_inner_dto(self) -> RecordSwarmVerdictCommandDto:
        """Build the immutable verdict command.

        Args:
            None.
        Return:
            Typed verdict command DTO.
        """
        result = RecordSwarmVerdictCommandDto(
            request_id=self.request_id,
            panel_id=self.panel_id,
            verifier_member_id=self.verifier_member_id,
            outcome=self.outcome,
            reviewed_diff_digest_hex=self.reviewed_diff_digest_hex,
            rationale=self.rationale,
        )
        return result


class ConvergeSwarmRequest(StrictSchemaModel):
    """Stage a Swarm candidate and optionally attempt quorum settlement."""

    request_id: Annotated[
        NonNilSwarmUUID,
        Field(description="Idempotency request UUID.", alias="requestId"),
    ]
    converged_commit_oid: Annotated[
        SwarmCommitOid,
        Field(
            description="Git commit OID with 40 to 64 ASCII hex characters.",
            alias="convergedCommitOid",
        ),
    ]
    converged_tree_blake3_hex: Annotated[
        NonZeroDigestHex,
        Field(description="Nonzero lowercase tree SHA-256 digest.", alias="convergedTreeBlake3Hex"),
    ]
    converged_diff_digest_hex: Annotated[
        NonZeroDigestHex,
        Field(description="Nonzero lowercase diff SHA-256 digest.", alias="convergedDiffDigestHex"),
    ]
    target_state: Annotated[
        SwarmConvergenceTargetInput | None,
        Field(description="Optional source-supported target state.", alias="targetState"),
    ]
    stage_candidate_only: Annotated[
        bool,
        Field(
            description="Stage the candidate without attempting settlement.",
            alias="stageCandidateOnly",
        ),
    ]

    @model_validator(mode="after")
    def validate_candidate_target(self) -> Self:
        """Reject the source-invalid candidate-only settled target combination.

        Args:
            None.
        Return:
            Validated convergence request.
        """
        if self.stage_candidate_only and self.target_state == SwarmConvergenceTargetEnum.SETTLED:
            raise ValueError("Candidate-only convergence cannot target SETTLED")
        result = self
        return result

    def to_inner_dto(self) -> ConvergeSwarmCommandDto:
        """Build the immutable convergence command.

        Args:
            None.
        Return:
            Typed convergence command DTO.
        """
        target_state = str(self.target_state) if self.target_state is not None else None
        result = ConvergeSwarmCommandDto(
            request_id=self.request_id,
            converged_commit_oid=self.converged_commit_oid,
            converged_tree_blake3_hex=self.converged_tree_blake3_hex,
            converged_diff_digest_hex=self.converged_diff_digest_hex,
            target_state=target_state,
            stage_candidate_only=self.stage_candidate_only,
        )
        return result


class SettleSwarmRequest(StrictSchemaModel):
    """Explicitly settle a candidate-ready Swarm run."""

    request_id: Annotated[
        NonNilSwarmUUID,
        Field(description="Idempotency request UUID.", alias="requestId"),
    ]

    def to_inner_dto(self) -> SettleSwarmCommandDto:
        """Build the immutable settlement command.

        Args:
            None.
        Return:
            Typed settlement command DTO.
        """
        result = SettleSwarmCommandDto(request_id=self.request_id)
        return result


class AbortSwarmRunRequest(StrictSchemaModel):
    """Explicit empty body for aborting a Swarm run."""

    def to_inner_dto(self) -> AbortSwarmRunCommandDto:
        """Build the immutable empty abort command.

        Args:
            None.
        Return:
            Typed abort command DTO.
        """
        result = AbortSwarmRunCommandDto()
        return result


class SwarmStallCheckRequest(StrictSchemaModel):
    """Optional caller-supplied stall policy thresholds and observation time."""

    stall_grace_ms: Annotated[
        Annotated[Int64, Field(ge=1)] | None,
        Field(description="Optional positive stall grace in milliseconds.", alias="stallGraceMs"),
    ]
    max_stall_nudges: Annotated[
        UInt32 | None,
        Field(
            description="Optional maximum stall nudges; zero is source-valid.",
            alias="maxStallNudges",
        ),
    ]
    max_ping_pong_streak: Annotated[
        Annotated[UInt32, Field(ge=1)] | None,
        Field(
            description="Optional positive ping-pong streak threshold.", alias="maxPingPongStreak"
        ),
    ]
    max_member_turns: Annotated[
        Annotated[UInt64, Field(ge=1)] | None,
        Field(description="Optional positive member turn threshold.", alias="maxMemberTurns"),
    ]
    observed_at_ms: Annotated[
        Annotated[Int64, Field(ge=0)] | None,
        Field(
            description="Optional nonnegative observation time in milliseconds.",
            alias="observedAtMs",
        ),
    ]

    def to_inner_dto(self) -> SwarmStallCheckCommandDto:
        """Build the immutable stall check command.

        Args:
            None.
        Return:
            Typed stall check command DTO.
        """
        result = SwarmStallCheckCommandDto(
            stall_grace_ms=self.stall_grace_ms,
            max_stall_nudges=self.max_stall_nudges,
            max_ping_pong_streak=self.max_ping_pong_streak,
            max_member_turns=self.max_member_turns,
            observed_at_ms=self.observed_at_ms,
        )
        return result


class PostSwarmMessageResponse(StrictSchemaModel):
    """Message post result and doorbell effects."""

    message: Annotated[SwarmBoardMessageSchema, Field(description="Posted board message.")]
    woken_member_ids: Annotated[
        list[UUID],
        Field(description="Member UUIDs woken by the message.", alias="wokenMemberIds"),
    ]
    coalesced_doorbell_member_ids: Annotated[
        list[UUID],
        Field(
            description="Member UUIDs with coalesced doorbells.", alias="coalescedDoorbellMemberIds"
        ),
    ]
    replayed: Annotated[bool, Field(description="Whether the source replayed an earlier result.")]


class SwarmBoardPageResponse(StrictSchemaModel):
    """Incremental page of ordered Swarm board messages."""

    messages: Annotated[list[SwarmBoardMessageSchema], Field(description="Ordered board messages.")]
    next_after_sequence: Annotated[
        UInt64 | None,
        Field(description="Nullable next page cursor.", alias="nextAfterSequence"),
    ]
    has_more: Annotated[
        bool, Field(description="Whether another page is available.", alias="hasMore")
    ]


class ConvergeSwarmResponse(StrictSchemaModel):
    """Convergence or settlement result with an optional quorum gate."""

    run: Annotated[SwarmRunSchema, Field(description="Updated canonical Swarm run.")]
    settled: Annotated[bool, Field(description="Whether the source settled the run.")]
    gate: Annotated[
        SwarmConvergenceGateSchema | None,
        Field(description="Optional verified quorum gate."),
    ]


class SwarmStallCheckResponse(StrictSchemaModel):
    """Deterministic stall and livelock report."""

    action: Annotated[str, Field(description="Nonempty source stall action.", min_length=1)]
    run_state: Annotated[
        SwarmRunState | None,
        Field(description="Optional canonical run state.", alias="runState"),
    ]
    working_members: Annotated[
        UInt64 | None,
        Field(description="Optional number of working members.", alias="workingMembers"),
    ]
    target_member_id: Annotated[
        UUID | None,
        Field(description="Optional target member UUID.", alias="targetMemberId"),
    ]
    bottleneck_reason: Annotated[
        str | None,
        Field(description="Optional source bottleneck explanation.", alias="bottleneckReason"),
    ]
    livelock_reason: Annotated[
        str | None,
        Field(description="Optional source livelock explanation.", alias="livelockReason"),
    ]
    observed_ping_pong_streak: Annotated[
        UInt32 | None,
        Field(description="Optional observed ping-pong streak.", alias="observedPingPongStreak"),
    ]
    observed_member_turns: Annotated[
        UInt64 | None,
        Field(description="Optional observed member turns.", alias="observedMemberTurns"),
    ]
    run: Annotated[SwarmRunSchema | None, Field(description="Optional updated Swarm run.")]
    stopped_members: Annotated[
        list[SwarmMemberSchema],
        Field(description="Members stopped by the check.", alias="stoppedMembers"),
    ]
    emitted_message: Annotated[
        SwarmBoardMessageSchema | None,
        Field(description="Optional emitted stall message.", alias="emittedMessage"),
    ]
