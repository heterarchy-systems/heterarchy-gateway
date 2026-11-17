"""Immutable command and result DTOs for Native Swarm run operations."""

from dataclasses import dataclass
from typing import NotRequired
from uuid import UUID

from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.autonomy_scope_inner_dto import (
    WorkspaceQueryScopeDict,
    WorkspaceQueryScopeDto,
)
from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
    SwarmChannelDict,
    SwarmChannelDto,
    SwarmChannelSubscriptionDict,
    SwarmChannelSubscriptionDto,
    SwarmDoorbellDict,
    SwarmDoorbellDto,
    SwarmMemberDict,
    SwarmMemberDto,
    SwarmMemberIdentityDto,
    SwarmMemberIdentityRequestDict,
    SwarmRunDict,
    SwarmRunDto,
    SwarmRunModeDto,
    SwarmRunModeRequestDict,
    SwarmVerdictDict,
    SwarmVerdictDto,
    SwarmVerificationPanelDict,
    SwarmVerificationPanelDto,
)
from app.orchestration.schema.types.orchestration_types import UInt32, UInt64
from app.orchestration.schema.types.swarm_types import SwarmUInt8
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmRoleKindEnum,
    SwarmWorkspaceModeEnum,
)


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


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateSwarmRunCommandDto:
    """Immutable source request for creating or replaying one Swarm run."""

    request_id: UUID
    title: str
    mode: SwarmRunModeDto
    max_members: UInt32
    max_spawn_depth: SwarmUInt8
    max_total_turns: UInt64
    required_verifier_quorum: UInt32
    allow_worker_all_mention: bool
    baseline_commit_oid: str
    baseline_tree_blake3_hex: str
    scope: WorkspaceQueryScopeDto | None

    def to_dict(self) -> CreateSwarmRunRequestDict:
        """Serialize the complete source Swarm run command.

        Args:
            None.
        Return:
            CamelCase run request with explicit nullable scope.
        """
        result = CreateSwarmRunRequestDict(
            requestId=str(self.request_id),
            title=self.title,
            mode=self.mode.to_request_dict(),
            maxMembers=self.max_members,
            maxSpawnDepth=self.max_spawn_depth,
            maxTotalTurns=self.max_total_turns,
            requiredVerifierQuorum=self.required_verifier_quorum,
            allowWorkerAllMention=self.allow_worker_all_mention,
            baselineCommitOid=self.baseline_commit_oid,
            baselineTreeBlake3Hex=self.baseline_tree_blake3_hex,
        )
        if self.scope is not None:
            result["scope"] = self.scope.to_dict()
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateSwarmChannelCommandDto:
    """Immutable source request for creating one Swarm channel."""

    channel_id: UUID
    name: str
    purpose: str | None
    created_by_member_id: UUID | None

    def to_dict(self) -> CreateSwarmChannelRequestDict:
        """Serialize the complete source channel command.

        Args:
            None.
        Return:
            CamelCase channel request with nullable fields preserved.
        """
        result = CreateSwarmChannelRequestDict(
            channelId=str(self.channel_id),
            name=self.name,
        )
        if self.purpose is not None:
            result["purpose"] = self.purpose
        if self.created_by_member_id is not None:
            result["createdByMemberId"] = str(self.created_by_member_id)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SubscribeSwarmChannelCommandDto:
    """Immutable source request for subscribing one Swarm member."""

    member_id: UUID

    def to_dict(self) -> SubscribeSwarmChannelRequestDict:
        """Serialize the complete source subscription command.

        Args:
            None.
        Return:
            CamelCase subscription request.
        """
        result = SubscribeSwarmChannelRequestDict(memberId=str(self.member_id))
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class AddSwarmMemberCommandDto:
    """Immutable source request for adding one Swarm roster member."""

    member_id: UUID
    roster_name: str
    role_kind: SwarmRoleKindEnum
    parent_member_id: UUID | None
    workspace_mode: SwarmWorkspaceModeEnum
    worktree_path: str | None
    identity: SwarmMemberIdentityDto
    initial_channels: tuple[str, ...]

    def to_dict(self) -> AddSwarmMemberRequestDict:
        """Serialize the complete source member command.

        Args:
            None.
        Return:
            CamelCase member request with explicit nullable values.
        """
        result = AddSwarmMemberRequestDict(
            memberId=str(self.member_id),
            rosterName=self.roster_name,
            roleKind=self.role_kind.value,
            workspaceMode=self.workspace_mode.value,
            identity=self.identity.to_request_dict(),
            initialChannels=list(self.initial_channels),
        )
        if self.parent_member_id is not None:
            result["parentMemberId"] = str(self.parent_member_id)
        if self.worktree_path is not None:
            result["worktreePath"] = self.worktree_path
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class KillSwarmMemberCommandDto:
    """Immutable empty source request for killing one Swarm member."""

    def to_dict(self) -> KillSwarmMemberRequestDict:
        """Serialize the required empty source request body.

        Args:
            None.
        Return:
            Closed empty JSON object.
        """
        result = KillSwarmMemberRequestDict()
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateSwarmRunInnerDto:
    """Immutable Swarm run create and exact replay result."""

    run: SwarmRunDto
    main_channel: SwarmChannelDto

    def to_dict(self) -> CreateSwarmRunResponseDict:
        """Serialize the typed run and default channel result.

        Args:
            None.
        Return:
            Complete create response dictionary.
        """
        result = CreateSwarmRunResponseDict(
            run=self.run.to_dict(),
            mainChannel=self.main_channel.to_dict(),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmRunListInnerDto:
    """Immutable list result containing canonical Swarm run records."""

    runs: tuple[SwarmRunDto, ...]

    def to_dict(self) -> SwarmRunListResponseDict:
        """Serialize all typed run records in source order.

        Args:
            None.
        Return:
            Complete run list response dictionary.
        """
        result = SwarmRunListResponseDict(runs=[run.to_dict() for run in self.runs])
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SwarmRunInspectionInnerDto:
    """Immutable full inspection snapshot for one Swarm run."""

    run: SwarmRunDto
    channels: tuple[SwarmChannelDto, ...]
    members: tuple[SwarmMemberDto, ...]
    subscriptions: tuple[SwarmChannelSubscriptionDto, ...]
    pending_doorbells: tuple[SwarmDoorbellDto, ...]
    verification_panel: SwarmVerificationPanelDto | None
    verdicts: tuple[SwarmVerdictDto, ...]

    def to_dict(self) -> SwarmRunInspectionResponseDict:
        """Serialize each typed inspection record in source order.

        Args:
            None.
        Return:
            Complete inspection response dictionary.
        """
        panel = self.verification_panel.to_dict() if self.verification_panel is not None else None
        result = SwarmRunInspectionResponseDict(
            run=self.run.to_dict(),
            channels=[channel.to_dict() for channel in self.channels],
            members=[member.to_dict() for member in self.members],
            subscriptions=[subscription.to_dict() for subscription in self.subscriptions],
            pendingDoorbells=[doorbell.to_dict() for doorbell in self.pending_doorbells],
            verificationPanel=panel,
            verdicts=[verdict.to_dict() for verdict in self.verdicts],
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class SubscribeSwarmChannelInnerDto:
    """Immutable result returned after a Swarm channel subscription."""

    swarm_run_id: UUID
    channel_id: UUID
    member_id: UUID
    newly_subscribed: bool

    def to_dict(self) -> SubscribeSwarmChannelResponseDict:
        """Serialize the complete subscription result.

        Args:
            None.
        Return:
            Typed subscription response dictionary.
        """
        result = SubscribeSwarmChannelResponseDict(
            swarmRunId=self.swarm_run_id,
            channelId=self.channel_id,
            memberId=self.member_id,
            newlySubscribed=self.newly_subscribed,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class KillSwarmMemberInnerDto:
    """Immutable result listing the killed target and descendant members."""

    killed_members: tuple[SwarmMemberDto, ...]

    def to_dict(self) -> KillSwarmMemberResponseDict:
        """Serialize all killed members in source order.

        Args:
            None.
        Return:
            Typed kill response dictionary.
        """
        result = KillSwarmMemberResponseDict(
            killedMembers=[member.to_dict() for member in self.killed_members]
        )
        return result
