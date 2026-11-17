"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from __future__ import annotations

from typing import NotRequired
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import (
    SwarmBoardMessageDict,
    SwarmConvergenceGateDict,
    SwarmMemberDict,
    SwarmRunDict,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt32, UInt64
from app.orchestration.schema.types.swarm_types import SwarmRunState, SwarmVerdictOutcomeInput


class PostSwarmMessageRequestDict(TypedDict, total=True, closed=True):
    """Source-shaped Swarm message request with omitted optional keys."""

    messageId: str
    channelId: NotRequired[str]
    authorMemberId: NotRequired[str]
    body: str


class CreateSwarmPanelRequestDict(TypedDict, total=True, closed=True):
    """Source-shaped verification panel request."""

    requestId: str
    authorMemberIds: list[str]
    verifierMemberIds: list[str]
    requiredQuorum: UInt32


class RecordSwarmVerdictRequestDict(TypedDict, total=True, closed=True):
    """Source-shaped verdict request with an omitted absent panel ID."""

    requestId: str
    panelId: NotRequired[str]
    verifierMemberId: str
    outcome: SwarmVerdictOutcomeInput
    reviewedDiffDigestHex: str
    rationale: str


class ConvergeSwarmRequestDict(TypedDict, total=True, closed=True):
    """Source-shaped convergence request."""

    requestId: str
    convergedCommitOid: str
    convergedTreeBlake3Hex: str
    convergedDiffDigestHex: str
    targetState: NotRequired[str]
    stageCandidateOnly: bool


class SettleSwarmRequestDict(TypedDict, total=True, closed=True):
    """Source-shaped settlement request."""

    requestId: str


class AbortSwarmRunRequestDict(TypedDict, total=True, closed=True):
    """Explicit empty Swarm abort request body."""


class SwarmStallCheckRequestDict(TypedDict, total=True, closed=True):
    """Source-shaped stall request omitting absent thresholds."""

    stallGraceMs: NotRequired[Int64]
    maxStallNudges: NotRequired[UInt32]
    maxPingPongStreak: NotRequired[UInt32]
    maxMemberTurns: NotRequired[UInt64]
    observedAtMs: NotRequired[Int64]


class PostSwarmMessageResponseDict(TypedDict, total=True, closed=True):
    """Typed message post outcome."""

    message: SwarmBoardMessageDict
    wokenMemberIds: list[UUID]
    coalescedDoorbellMemberIds: list[UUID]
    replayed: bool


class SwarmBoardPageResponseDict(TypedDict, total=True, closed=True):
    """Typed incremental board page."""

    messages: list[SwarmBoardMessageDict]
    nextAfterSequence: UInt64 | None
    hasMore: bool


class ConvergeSwarmResponseDict(TypedDict, total=True, closed=True):
    """Typed convergence or settlement outcome."""

    run: SwarmRunDict
    settled: bool
    gate: SwarmConvergenceGateDict | None


class SwarmStallCheckResponseDict(TypedDict, total=True, closed=True):
    """Typed deterministic stall and livelock report."""

    action: str
    runState: SwarmRunState | None
    workingMembers: UInt64 | None
    targetMemberId: UUID | None
    bottleneckReason: str | None
    livelockReason: str | None
    observedPingPongStreak: UInt32 | None
    observedMemberTurns: UInt64 | None
    run: SwarmRunDict | None
    stoppedMembers: list[SwarmMemberDict]
    emittedMessage: SwarmBoardMessageDict | None
