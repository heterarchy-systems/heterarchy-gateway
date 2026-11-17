"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing import NotRequired
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.types.autonomy.autonomy_scope_types import (
    WorkspaceQueryScopeDict,
)
from app.orchestration.application.inner_dto.types.swarm.swarm_state_types import (
    SwarmChannelDict,
    SwarmChannelSubscriptionDict,
    SwarmDoorbellDict,
    SwarmMemberDict,
    SwarmMemberIdentityRequestDict,
    SwarmRunDict,
    SwarmRunModeRequestDict,
    SwarmVerdictDict,
    SwarmVerificationPanelDict,
)
from app.orchestration.schema.types.orchestration_types import UInt32, UInt64
from app.orchestration.schema.types.swarm_types import SwarmUInt8


class CreateSwarmRunRequestDict(TypedDict, total=True, closed=True):
    """Complete camelCase source command for creating a Swarm run."""

    requestId: str
    title: str
    mode: SwarmRunModeRequestDict
    maxMembers: UInt32
    maxSpawnDepth: SwarmUInt8
    maxTotalTurns: UInt64
    requiredVerifierQuorum: UInt32
    allowWorkerAllMention: bool
    baselineCommitOid: str
    baselineTreeBlake3Hex: str
    scope: NotRequired[WorkspaceQueryScopeDict]


class CreateSwarmChannelRequestDict(TypedDict, total=True, closed=True):
    """Complete camelCase source command for creating a Swarm channel."""

    channelId: str
    name: str
    purpose: NotRequired[str]
    createdByMemberId: NotRequired[str]


class SubscribeSwarmChannelRequestDict(TypedDict, total=True, closed=True):
    """Complete camelCase source command for subscribing a member."""

    memberId: str


class AddSwarmMemberRequestDict(TypedDict, total=True, closed=True):
    """Complete camelCase source command for adding a Swarm member."""

    memberId: str
    rosterName: str
    roleKind: str
    parentMemberId: NotRequired[str]
    workspaceMode: str
    worktreePath: NotRequired[str]
    identity: SwarmMemberIdentityRequestDict
    initialChannels: list[str]


class KillSwarmMemberRequestDict(TypedDict, total=True, closed=True):
    """Required empty JSON request body for a Swarm member kill."""


class CreateSwarmRunResponseDict(TypedDict, total=True, closed=True):
    """Typed run creation result including the main channel."""

    run: SwarmRunDict
    mainChannel: SwarmChannelDict


class SwarmRunListResponseDict(TypedDict, total=True, closed=True):
    """Typed list of canonical Swarm run records."""

    runs: list[SwarmRunDict]


class SwarmRunInspectionResponseDict(TypedDict, total=True, closed=True):
    """Complete typed inspection snapshot for one Swarm run."""

    run: SwarmRunDict
    channels: list[SwarmChannelDict]
    members: list[SwarmMemberDict]
    subscriptions: list[SwarmChannelSubscriptionDict]
    pendingDoorbells: list[SwarmDoorbellDict]
    verificationPanel: SwarmVerificationPanelDict | None
    verdicts: list[SwarmVerdictDict]


class SubscribeSwarmChannelResponseDict(TypedDict, total=True, closed=True):
    """Complete typed result for a Swarm channel subscription."""

    swarmRunId: UUID
    channelId: UUID
    memberId: UUID
    newlySubscribed: bool


class KillSwarmMemberResponseDict(TypedDict, total=True, closed=True):
    """Complete typed result listing killed members."""

    killedMembers: list[SwarmMemberDict]
