"""Strict request and response contracts for native Swarm run operations."""

from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from app.orchestration.application.inner_dto.autonomy_scope_inner_dto import (
    WorkspaceQueryScopeDto,
)
from app.orchestration.application.inner_dto.swarm_run_inner_dto import (
    AddSwarmMemberCommandDto,
    CreateSwarmChannelCommandDto,
    CreateSwarmRunCommandDto,
    KillSwarmMemberCommandDto,
    SubscribeSwarmChannelCommandDto,
)
from app.orchestration.application.inner_dto.swarm_state_inner_dto import (
    DagNodeHybridTargetDto,
    SwarmMemberIdentityDto,
    SwarmRunModeDto,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_reviewer_schema import (
    ExecutionAuthorSchema,
)
from app.orchestration.schema.autonomy.orchestration_autonomy_scope_schema import (
    WorkspaceQueryScopeSchema,
)
from app.orchestration.schema.execution.orchestration_execution_schema import (
    PrincipalIdentitySchema,
)
from app.orchestration.schema.swarm.orchestration_swarm_state_schema import (
    DagNodeHybridTargetSchema,
    SwarmChannelSchema,
    SwarmChannelSubscriptionSchema,
    SwarmDoorbellSchema,
    SwarmMemberSchema,
    SwarmRunSchema,
    SwarmVerdictSchema,
    SwarmVerificationPanelSchema,
)
from app.orchestration.schema.types.orchestration_types import UInt32, UInt64
from app.orchestration.schema.types.swarm_types import (
    NonNilCanonicalSwarmUUID,
    NonZeroDigestHex,
    SwarmCommitOid,
    SwarmRoleKindInput,
    SwarmRunModeKindInput,
    SwarmUInt8,
    SwarmUUID,
    SwarmWorkspaceModeInput,
    parse_canonical_swarm_uuid,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.filter_module.base_filter import BaseFilter
from app.shared.ingredient_element.orchestration.principal_enums import PrincipalKindEnum
from app.shared.ingredient_element.orchestration.swarm_enums import (
    SwarmRoleKindEnum,
    SwarmRunModeEnum,
    SwarmWorkspaceModeEnum,
)

MAX_SWARM_RUN_LIST_SIZE = 128


def _validate_swarm_principal_id(kind: PrincipalKindEnum, principal_id: str) -> None:
    """Apply Orchestration's principal identity discriminator rules.

    Args:
        kind: Validated source principal kind.
        principal_id: Original source principal ID string.
    Return:
        None.
    """
    if kind is PrincipalKindEnum.TRUSTED_STDIO and principal_id != "":
        raise ValueError("trusted_stdio principal ID must be empty")
    if (
        kind is not PrincipalKindEnum.TRUSTED_STDIO
        and parse_canonical_swarm_uuid(value=principal_id).int == 0
    ):
        raise ValueError("Swarm principal ID must be non-nil")


class SwarmPrincipalIdentityRequestSchema(PrincipalIdentitySchema):
    """Match source principal identity rules for Swarm execution authors."""

    @model_validator(mode="after")
    def validate_principal_identity(self) -> Self:
        """Require empty trusted-stdio IDs or canonical non-nil token UUIDs.

        Args:
            None.
        Return:
            The validated principal identity.
        """
        _validate_swarm_principal_id(kind=PrincipalKindEnum(self.kind), principal_id=self.id)
        result = self
        return result


class SwarmExecutionAuthorRequestSchema(ExecutionAuthorSchema):
    """Use canonical non-nil identities accepted by Swarm source clients."""

    profile_id: Annotated[
        NonNilCanonicalSwarmUUID,
        Field(alias="profileId", description="Canonical non-nil Agent Profile UUID."),
    ]
    participant_id: Annotated[
        NonNilCanonicalSwarmUUID,
        Field(alias="participantId", description="Canonical non-nil Workspace participant UUID."),
    ]
    principal: Annotated[
        SwarmPrincipalIdentityRequestSchema,
        Field(description="Validated source principal identity."),
    ]


class SwarmRunModeRequestSchema(StrictSchemaModel):
    """Exact source request spelling for one Swarm execution mode."""

    kind: Annotated[
        SwarmRunModeKindInput,
        Field(description="Accepted Orchestration Swarm run mode spelling."),
    ]
    hybrid_target: Annotated[
        DagNodeHybridTargetSchema | None,
        Field(alias="hybridTarget", description="DAG node target, or null for standalone mode."),
    ]

    @model_validator(mode="after")
    def validate_target_matches_mode(self) -> Self:
        """Require a DAG target only for DAG-node hybrid runs.

        Args:
            None.
        Return:
            The validated standalone or hybrid mode.
        """
        mode = SwarmRunModeEnum(self.kind)
        if mode is SwarmRunModeEnum.STANDALONE and self.hybrid_target is not None:
            raise ValueError("standalone Swarm mode cannot include a hybrid target")
        if mode is SwarmRunModeEnum.DAG_NODE_HYBRID and self.hybrid_target is None:
            raise ValueError("DAG-node hybrid Swarm mode requires a target")
        result = self
        return result

    def to_inner_dto(self) -> SwarmRunModeDto:
        """Convert the validated mode into its immutable wire DTO.

        Args:
            None.
        Return:
            Immutable mode DTO preserving the source target fields.
        """
        target = self.hybrid_target
        target_dto = (
            DagNodeHybridTargetDto(
                goal_id=target.goal_id,
                dag_revision=target.dag_revision,
                node_id=target.node_id,
                declared_write_manifest_blake3_hex=target.declared_write_manifest_blake3_hex,
            )
            if target is not None
            else None
        )
        result = SwarmRunModeDto(kind=SwarmRunModeEnum(self.kind), hybrid_target=target_dto)
        return result


class CreateSwarmRunRequest(StrictSchemaModel):
    """Create or exactly replay a standalone or DAG hybrid Swarm run."""

    request_id: Annotated[
        NonNilCanonicalSwarmUUID,
        Field(alias="requestId", description="Canonical non-nil request UUID."),
    ]
    title: Annotated[
        str,
        Field(description="Nonblank display title for the Swarm run.", min_length=1),
    ]
    mode: Annotated[
        SwarmRunModeRequestSchema,
        Field(description="Discriminated standalone or DAG hybrid execution mode."),
    ]
    max_members: Annotated[
        UInt32,
        Field(
            alias="maxMembers",
            description="Positive maximum roster size accepted by Orchestration.",
            gt=0,
        ),
    ]
    max_spawn_depth: Annotated[
        SwarmUInt8,
        Field(alias="maxSpawnDepth", description="Maximum nested spawn depth."),
    ]
    max_total_turns: Annotated[
        UInt64,
        Field(alias="maxTotalTurns", description="Positive maximum total Swarm turns.", gt=0),
    ]
    required_verifier_quorum: Annotated[
        UInt32,
        Field(
            alias="requiredVerifierQuorum",
            description="Positive required independent verifier quorum.",
            gt=0,
        ),
    ]
    allow_worker_all_mention: Annotated[
        bool,
        Field(
            alias="allowWorkerAllMention", description="Whether worker @all mentions are allowed."
        ),
    ]
    baseline_commit_oid: Annotated[
        SwarmCommitOid,
        Field(alias="baselineCommitOid", description="Baseline Git commit object ID."),
    ]
    baseline_tree_blake3_hex: Annotated[
        NonZeroDigestHex,
        Field(alias="baselineTreeBlake3Hex", description="Baseline tree digest as hexadecimal."),
    ]
    scope: Annotated[
        WorkspaceQueryScopeSchema | None,
        Field(description="Optional operator-owned Workspace scope proof."),
    ]

    @field_validator("title")
    @classmethod
    def validate_nonblank_title(cls, value: str) -> str:
        """Reject titles the source client considers blank.

        Args:
            value: Requested Swarm run title.
        Return:
            The unchanged nonblank title.
        """
        if not value.strip():
            raise ValueError("Swarm run title must not be blank")
        result = value
        return result

    def to_inner_dto(self) -> CreateSwarmRunCommandDto:
        """Convert the validated request into an immutable run command.

        Args:
            None.
        Return:
            Complete source-shaped Swarm run command.
        """
        scope = self.scope
        scope_dto = (
            WorkspaceQueryScopeDto(
                workspace_id=scope.workspace_id,
                location_id=scope.location_id,
                location_revision=scope.location_revision,
                workspace_revision=scope.workspace_revision,
                locator=scope.locator,
            )
            if scope is not None
            else None
        )
        result = CreateSwarmRunCommandDto(
            request_id=self.request_id,
            title=self.title,
            mode=self.mode.to_inner_dto(),
            max_members=self.max_members,
            max_spawn_depth=self.max_spawn_depth,
            max_total_turns=self.max_total_turns,
            required_verifier_quorum=self.required_verifier_quorum,
            allow_worker_all_mention=self.allow_worker_all_mention,
            baseline_commit_oid=self.baseline_commit_oid,
            baseline_tree_blake3_hex=self.baseline_tree_blake3_hex,
            scope=scope_dto,
        )
        return result


class SwarmRunListFilter(BaseFilter):
    """Optional bounded Swarm run list query."""

    limit: Annotated[
        int | None,
        Field(
            description="Optional result count from 1 through 128.",
            ge=1,
            le=MAX_SWARM_RUN_LIST_SIZE,
        ),
    ] = None


class CreateSwarmChannelRequest(StrictSchemaModel):
    """Create one named channel inside an existing Swarm run."""

    channel_id: Annotated[
        NonNilCanonicalSwarmUUID,
        Field(alias="channelId", description="Canonical non-nil channel UUID."),
    ]
    name: Annotated[str, Field(description="Nonblank Swarm channel name.", min_length=1)]
    purpose: Annotated[str | None, Field(description="Channel purpose, or null when absent.")]
    created_by_member_id: Annotated[
        NonNilCanonicalSwarmUUID | None,
        Field(
            alias="createdByMemberId",
            description="Canonical non-nil creating member UUID, or null for system creation.",
        ),
    ]

    @field_validator("name")
    @classmethod
    def validate_nonblank_name(cls, value: str) -> str:
        """Reject channel names the source client considers blank.

        Args:
            value: Requested Swarm channel name.
        Return:
            The unchanged nonblank channel name.
        """
        if not value.strip():
            raise ValueError("Swarm channel name must not be blank")
        result = value
        return result

    def to_inner_dto(self) -> CreateSwarmChannelCommandDto:
        """Convert the validated channel request into a command DTO.

        Args:
            None.
        Return:
            Complete source-shaped channel command.
        """
        result = CreateSwarmChannelCommandDto(
            channel_id=self.channel_id,
            name=self.name,
            purpose=self.purpose,
            created_by_member_id=self.created_by_member_id,
        )
        return result


class SubscribeSwarmChannelRequest(StrictSchemaModel):
    """Subscribe one existing Swarm member to a channel."""

    member_id: Annotated[
        NonNilCanonicalSwarmUUID,
        Field(alias="memberId", description="Canonical non-nil member UUID to subscribe."),
    ]

    def to_inner_dto(self) -> SubscribeSwarmChannelCommandDto:
        """Convert the validated subscription request into a command DTO.

        Args:
            None.
        Return:
            Complete source-shaped subscription command.
        """
        result = SubscribeSwarmChannelCommandDto(member_id=self.member_id)
        return result


class AddSwarmMemberRequest(StrictSchemaModel):
    """Add one typed execution identity to a Swarm roster."""

    member_id: Annotated[
        NonNilCanonicalSwarmUUID,
        Field(alias="memberId", description="Canonical non-nil member UUID."),
    ]
    roster_name: Annotated[
        str,
        Field(alias="rosterName", description="Nonblank stable member roster name.", min_length=1),
    ]
    role_kind: Annotated[
        SwarmRoleKindInput,
        Field(alias="roleKind", description="Source-accepted role kind spelling."),
    ]
    parent_member_id: Annotated[
        NonNilCanonicalSwarmUUID | None,
        Field(
            alias="parentMemberId",
            description="Canonical non-nil parent member UUID, or null for a root member.",
        ),
    ]
    workspace_mode: Annotated[
        SwarmWorkspaceModeInput,
        Field(alias="workspaceMode", description="Source-accepted workspace mode spelling."),
    ]
    worktree_path: Annotated[
        str | None,
        Field(alias="worktreePath", description="Member worktree path, or null when absent."),
    ]
    identity: Annotated[
        SwarmExecutionAuthorRequestSchema,
        Field(description="Profile, Workspace participant, and principal identity."),
    ]
    initial_channels: Annotated[
        list[str],
        Field(alias="initialChannels", description="Initial channel names for the new member."),
    ]

    @field_validator("roster_name")
    @classmethod
    def validate_nonblank_roster_name(cls, value: str) -> str:
        """Reject roster names the source client considers blank.

        Args:
            value: Requested stable member roster name.
        Return:
            The unchanged nonblank roster name.
        """
        if not value.strip():
            raise ValueError("Swarm member roster name must not be blank")
        result = value
        return result

    def to_inner_dto(self) -> AddSwarmMemberCommandDto:
        """Convert the validated roster request into an immutable command.

        Args:
            None.
        Return:
            Complete source-shaped member command.
        """
        identity = SwarmMemberIdentityDto(
            profile_id=self.identity.profile_id,
            participant_id=self.identity.participant_id,
            principal=self.identity.principal.to_inner_dto(),
        )
        result = AddSwarmMemberCommandDto(
            member_id=self.member_id,
            roster_name=self.roster_name,
            role_kind=SwarmRoleKindEnum(self.role_kind),
            parent_member_id=self.parent_member_id,
            workspace_mode=SwarmWorkspaceModeEnum(self.workspace_mode),
            worktree_path=self.worktree_path,
            identity=identity,
            initial_channels=tuple(self.initial_channels),
        )
        return result


class KillSwarmMemberRequest(StrictSchemaModel):
    """Required empty request body for a member kill operation."""

    def to_inner_dto(self) -> KillSwarmMemberCommandDto:
        """Build the immutable empty kill command.

        Args:
            None.
        Return:
            Empty Swarm member kill command.
        """
        result = KillSwarmMemberCommandDto()
        return result


class CreateSwarmRunResponse(StrictSchemaModel):
    """Run creation or exact replay result, including its main channel."""

    run: Annotated[SwarmRunSchema, Field(description="Canonical run readback.")]
    main_channel: Annotated[
        SwarmChannelSchema,
        Field(alias="mainChannel", description="Default main channel readback."),
    ]


class SwarmRunListResponse(StrictSchemaModel):
    """Bounded list of Swarm runs in one Workspace."""

    runs: Annotated[list[SwarmRunSchema], Field(description="Canonical Swarm run records.")]


class SwarmRunInspectionResponse(StrictSchemaModel):
    """Canonical Swarm run snapshot, channels, members, and activity."""

    run: Annotated[SwarmRunSchema, Field(description="Canonical run readback.")]
    channels: Annotated[list[SwarmChannelSchema], Field(description="Run channels.")]
    members: Annotated[list[SwarmMemberSchema], Field(description="Current run roster.")]
    subscriptions: Annotated[
        list[SwarmChannelSubscriptionSchema],
        Field(description="Channel-to-member subscription edges."),
    ]
    pending_doorbells: Annotated[
        list[SwarmDoorbellSchema],
        Field(alias="pendingDoorbells", description="Pending member wakeup notifications."),
    ]
    verification_panel: Annotated[
        SwarmVerificationPanelSchema | None,
        Field(
            alias="verificationPanel", description="Active verification panel, or null when absent."
        ),
    ]
    verdicts: Annotated[list[SwarmVerdictSchema], Field(description="Recorded verifier verdicts.")]


class SubscribeSwarmChannelResponse(StrictSchemaModel):
    """Subscription result from Orchestration."""

    swarm_run_id: Annotated[SwarmUUID, Field(alias="swarmRunId", description="Swarm run UUID.")]
    channel_id: Annotated[SwarmUUID, Field(alias="channelId", description="Channel UUID.")]
    member_id: Annotated[SwarmUUID, Field(alias="memberId", description="Subscribed member UUID.")]
    newly_subscribed: Annotated[
        bool,
        Field(
            alias="newlySubscribed", description="Whether the source created a new subscription."
        ),
    ]


class KillSwarmMemberResponse(StrictSchemaModel):
    """Killed target member and cascade-cancelled descendant helpers."""

    killed_members: Annotated[
        list[SwarmMemberSchema],
        Field(alias="killedMembers", description="Members killed by this request."),
    ]


class SwarmRunScopeIdentity(StrictSchemaModel):
    """Comparable run identity used to check source path echoes."""

    workspace_id: Annotated[SwarmUUID, Field(description="Workspace UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(description="Swarm run UUID.")]


class SwarmChannelScopeIdentity(StrictSchemaModel):
    """Comparable channel identity used to check source path echoes."""

    workspace_id: Annotated[SwarmUUID, Field(description="Workspace UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(description="Swarm run UUID.")]
    channel_id: Annotated[SwarmUUID, Field(description="Channel UUID.")]


class SwarmMemberScopeIdentity(StrictSchemaModel):
    """Comparable member identity used to check source path echoes."""

    workspace_id: Annotated[SwarmUUID, Field(description="Workspace UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(description="Swarm run UUID.")]
    member_id: Annotated[SwarmUUID, Field(description="Member UUID.")]


class SwarmSubscriptionPathIdentity(StrictSchemaModel):
    """Comparable subscription identity used to check source path echoes."""

    workspace_id: Annotated[SwarmUUID, Field(description="Workspace UUID.")]
    swarm_run_id: Annotated[SwarmUUID, Field(description="Swarm run UUID.")]
    channel_id: Annotated[SwarmUUID, Field(description="Channel UUID.")]
    member_id: Annotated[SwarmUUID, Field(description="Member UUID.")]
