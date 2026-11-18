"""Immutable Forge Swarm command DTOs and tagged target helpers."""

from dataclasses import dataclass
from uuid import UUID

from app.forge.application.inner_dto.forge_envelope_dto import ForgeSessionActorDto
from app.forge.application.inner_dto.types.forge_envelope_types import (
    ForgeSessionActorDict,
    ForgeWorkspaceScopeDict,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmConvergenceCandidateDict,
    ForgeSwarmConvergePayloadDict,
    ForgeSwarmDagNodeHybridTargetDict,
    ForgeSwarmMaterializeHybridPayloadDict,
    ForgeSwarmMemberCapturePayloadDict,
    ForgeSwarmPurgePayloadDict,
    ForgeSwarmSettlementGetPayloadDict,
    ForgeSwarmSettlePayloadDict,
    ForgeSwarmStandaloneTargetDict,
    ForgeSwarmTargetDict,
    ForgeSwarmWorkspaceGetPayloadDict,
    ForgeSwarmWorkspaceProvisionPayloadDict,
)
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import (
    ForgeSwarmMemberCaptureRequest,
)
from app.forge.schema.swarm.convergence.forge_swarm_convergence_schema import (
    ForgeSwarmConvergeRequest,
)
from app.forge.schema.swarm.identity.forge_swarm_identity_schema import (
    ForgeSwarmStandaloneTarget,
    ForgeSwarmTarget,
)
from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmMaterializeHybridRequest,
    ForgeSwarmSettlementGetRequest,
    ForgeSwarmSettleRequest,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeRequest,
    ForgeSwarmWorkspaceGetRequest,
    ForgeSwarmWorkspaceProvisionRequest,
)
from app.shared.ingredient_element.forge.forge_enums import (
    SwarmTargetKindEnum,
    SwarmWorkspaceModeEnum,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmTargetDto:
    """Immutable tagged target used in a Swarm command payload."""

    kind: SwarmTargetKindEnum
    goal_id: UUID | None
    dag_revision: int | None
    node_id: UUID | None

    def to_dict(self) -> ForgeSwarmTargetDict:
        """Serialize the source's tagged target shape.

        Args:
            None.
        Return:
            Standalone or DAG node hybrid target dictionary.
        """
        if self.kind is SwarmTargetKindEnum.STANDALONE_SWARM:
            result: ForgeSwarmTargetDict = ForgeSwarmStandaloneTargetDict(kind=self.kind.value)
            return result
        if self.goal_id is None or self.dag_revision is None or self.node_id is None:
            raise ValueError("DAG node hybrid target requires goal, revision, and node identities")
        result = ForgeSwarmDagNodeHybridTargetDict(
            kind=self.kind.value,
            goal_id=str(self.goal_id),
            dag_revision=self.dag_revision,
            node_id=str(self.node_id),
        )
        return result


def target_dto(target: ForgeSwarmTarget) -> ForgeSwarmTargetDto:
    """Convert a validated Pydantic target into a typed immutable DTO.

    Args:
        target: Validated standalone or hybrid target model.
    Return:
        Tagged target DTO with runtime enum values restored.
    """
    kind = SwarmTargetKindEnum(target.kind)
    if isinstance(target, ForgeSwarmStandaloneTarget):
        result = ForgeSwarmTargetDto(
            kind=kind,
            goal_id=None,
            dag_revision=None,
            node_id=None,
        )
        return result
    result = ForgeSwarmTargetDto(
        kind=kind,
        goal_id=target.goal_id,
        dag_revision=target.dag_revision,
        node_id=target.node_id,
    )
    return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmWorkspaceProvisionCommandDto:
    """Immutable command body provisioning one Swarm workspace."""

    scope: ForgeWorkspaceScopeDict
    actor: ForgeSessionActorDict
    swarm_run_id: UUID
    member_id: UUID
    mode: SwarmWorkspaceModeEnum
    target: ForgeSwarmTargetDto
    candidate_commit_oid: str | None
    observed_at_ms: int

    @classmethod
    def from_request(
        cls,
        request: ForgeSwarmWorkspaceProvisionRequest,
        scope: ForgeWorkspaceScopeDict,
        actor: ForgeSessionActorDto,
    ) -> ForgeSwarmWorkspaceProvisionCommandDto:
        """Build the immutable provision command from the validated boundary.

        Args:
            request: Validated Gateway request schema.
            scope: Serialized Forge scope DTO.
            actor: Authenticated actor DTO.
        Return:
            Typed command DTO for the Forge operation payload.
        """
        result = cls(
            scope=scope,
            actor=actor.to_dict(),
            swarm_run_id=request.swarm_run_id,
            member_id=request.member_id,
            mode=SwarmWorkspaceModeEnum(request.mode),
            target=target_dto(target=request.target),
            candidate_commit_oid=request.candidate_commit_oid,
            observed_at_ms=request.observed_at_ms,
        )
        return result

    def to_dict(self) -> ForgeSwarmWorkspaceProvisionPayloadDict:
        """Serialize the provision payload using exact Forge keys.

        Args:
            None.
        Return:
            Closed `swarm.workspace_provision` payload dictionary.
        """
        result: ForgeSwarmWorkspaceProvisionPayloadDict = ForgeSwarmWorkspaceProvisionPayloadDict(
            scope=self.scope,
            actor=self.actor,
            swarm_run_id=str(self.swarm_run_id),
            member_id=str(self.member_id),
            mode=self.mode.value,
            target=self.target.to_dict(),
            candidate_commit_oid=self.candidate_commit_oid,
            observed_at_ms=self.observed_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmWorkspaceGetCommandDto:
    """Immutable command body reading one member workspace receipt."""

    scope: ForgeWorkspaceScopeDict
    swarm_run_id: UUID
    member_id: UUID

    @classmethod
    def from_request(
        cls,
        request: ForgeSwarmWorkspaceGetRequest,
        scope: ForgeWorkspaceScopeDict,
    ) -> ForgeSwarmWorkspaceGetCommandDto:
        """Build the workspace lookup command from its validated schema.

        Args:
            request: Validated Gateway request schema.
            scope: Serialized Forge scope DTO.
        Return:
            Typed command DTO for the Forge operation payload.
        """
        result = cls(scope=scope, swarm_run_id=request.swarm_run_id, member_id=request.member_id)
        return result

    def to_dict(self) -> ForgeSwarmWorkspaceGetPayloadDict:
        """Serialize the workspace lookup payload using exact Forge keys.

        Args:
            None.
        Return:
            Closed `swarm.workspace_get` payload dictionary.
        """
        result: ForgeSwarmWorkspaceGetPayloadDict = ForgeSwarmWorkspaceGetPayloadDict(
            scope=self.scope,
            swarm_run_id=str(self.swarm_run_id),
            member_id=str(self.member_id),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmMemberCaptureCommandDto:
    """Immutable command body capturing one member output."""

    scope: ForgeWorkspaceScopeDict
    actor: ForgeSessionActorDict
    swarm_run_id: UUID
    member_id: UUID
    captured_at_ms: int

    @classmethod
    def from_request(
        cls,
        request: ForgeSwarmMemberCaptureRequest,
        scope: ForgeWorkspaceScopeDict,
        actor: ForgeSessionActorDto,
    ) -> ForgeSwarmMemberCaptureCommandDto:
        """Build the member capture command from the validated schema.

        Args:
            request: Validated Gateway request schema.
            scope: Serialized Forge scope DTO.
            actor: Authenticated actor DTO.
        Return:
            Typed command DTO for the Forge operation payload.
        """
        result = cls(
            scope=scope,
            actor=actor.to_dict(),
            swarm_run_id=request.swarm_run_id,
            member_id=request.member_id,
            captured_at_ms=request.captured_at_ms,
        )
        return result

    def to_dict(self) -> ForgeSwarmMemberCapturePayloadDict:
        """Serialize the member capture payload using exact Forge keys.

        Args:
            None.
        Return:
            Closed `swarm.member_capture` payload dictionary.
        """
        result: ForgeSwarmMemberCapturePayloadDict = ForgeSwarmMemberCapturePayloadDict(
            scope=self.scope,
            actor=self.actor,
            swarm_run_id=str(self.swarm_run_id),
            member_id=str(self.member_id),
            captured_at_ms=self.captured_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmConvergenceCandidateDto:
    """Immutable member output expectation used by convergence."""

    member_id: UUID
    expected_output_commit_oid: str | None
    expected_diff_digest: str | None

    def to_dict(self) -> ForgeSwarmConvergenceCandidateDict:
        """Serialize only non-null candidate fields, matching Forge Serde.

        Args:
            None.
        Return:
            Closed candidate payload with absent optional members omitted.
        """
        result: ForgeSwarmConvergenceCandidateDict = ForgeSwarmConvergenceCandidateDict(
            member_id=str(self.member_id)
        )
        if self.expected_output_commit_oid is not None:
            result["expected_output_commit_oid"] = self.expected_output_commit_oid
        if self.expected_diff_digest is not None:
            result["expected_diff_digest"] = self.expected_diff_digest
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmConvergeCommandDto:
    """Immutable command body comparing member workspace outputs."""

    scope: ForgeWorkspaceScopeDict
    actor: ForgeSessionActorDict
    swarm_run_id: UUID
    candidates: tuple[ForgeSwarmConvergenceCandidateDto, ...]
    observed_at_ms: int

    @classmethod
    def from_request(
        cls,
        request: ForgeSwarmConvergeRequest,
        scope: ForgeWorkspaceScopeDict,
        actor: ForgeSessionActorDto,
    ) -> ForgeSwarmConvergeCommandDto:
        """Build the convergence command from the validated schema.

        Args:
            request: Validated Gateway request schema.
            scope: Serialized Forge scope DTO.
            actor: Authenticated actor DTO.
        Return:
            Typed command DTO for the Forge operation payload.
        """
        candidates = tuple(
            ForgeSwarmConvergenceCandidateDto(
                member_id=candidate.member_id,
                expected_output_commit_oid=candidate.expected_output_commit_oid,
                expected_diff_digest=candidate.expected_diff_digest,
            )
            for candidate in request.candidates
        )
        result = cls(
            scope=scope,
            actor=actor.to_dict(),
            swarm_run_id=request.swarm_run_id,
            candidates=candidates,
            observed_at_ms=request.observed_at_ms,
        )
        return result

    def to_dict(self) -> ForgeSwarmConvergePayloadDict:
        """Serialize the convergence payload using exact Forge keys.

        Args:
            None.
        Return:
            Closed `swarm.converge` payload dictionary.
        """
        result: ForgeSwarmConvergePayloadDict = ForgeSwarmConvergePayloadDict(
            scope=self.scope,
            actor=self.actor,
            swarm_run_id=str(self.swarm_run_id),
            candidates=[candidate.to_dict() for candidate in self.candidates],
            observed_at_ms=self.observed_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmSettleCommandDto:
    """Immutable command body settling a converged Swarm run."""

    scope: ForgeWorkspaceScopeDict
    activity_id: UUID | None
    actor: ForgeSessionActorDict
    coordinator_agent_id: UUID
    swarm_run_id: UUID
    settlement_id: UUID
    converged_commit_oid: str
    expected_diff_digest: str | None
    settled_at_ms: int

    @classmethod
    def from_request(
        cls,
        request: ForgeSwarmSettleRequest,
        scope: ForgeWorkspaceScopeDict,
        actor: ForgeSessionActorDto,
    ) -> ForgeSwarmSettleCommandDto:
        """Build the settlement command from the validated schema.

        Args:
            request: Validated Gateway request schema.
            scope: Serialized Forge scope DTO.
            actor: Authenticated actor DTO.
        Return:
            Typed command DTO for the Forge operation payload.
        """
        result = cls(
            scope=scope,
            activity_id=request.activity_id,
            actor=actor.to_dict(),
            coordinator_agent_id=request.coordinator_agent_id,
            swarm_run_id=request.swarm_run_id,
            settlement_id=request.settlement_id,
            converged_commit_oid=request.converged_commit_oid,
            expected_diff_digest=request.expected_diff_digest,
            settled_at_ms=request.settled_at_ms,
        )
        return result

    def to_dict(self) -> ForgeSwarmSettlePayloadDict:
        """Serialize the settlement payload using exact Forge keys.

        Args:
            None.
        Return:
            Closed `swarm.settle` payload dictionary.
        """
        result: ForgeSwarmSettlePayloadDict = ForgeSwarmSettlePayloadDict(
            scope=self.scope,
            activity_id=str(self.activity_id) if self.activity_id is not None else None,
            actor=self.actor,
            coordinator_agent_id=str(self.coordinator_agent_id),
            swarm_run_id=str(self.swarm_run_id),
            settlement_id=str(self.settlement_id),
            converged_commit_oid=self.converged_commit_oid,
            expected_diff_digest=self.expected_diff_digest,
            settled_at_ms=self.settled_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmMaterializeHybridCommandDto:
    """Immutable command body materializing a settlement into the DAG."""

    scope: ForgeWorkspaceScopeDict
    activity_id: UUID
    actor: ForgeSessionActorDict
    swarm_run_id: UUID
    settlement_id: UUID
    goal_id: UUID
    expected_goal_revision: int
    expected_dag_revision: int
    node_id: UUID
    converged_commit_oid: str
    expected_diff_digest: str | None
    settled_at_ms: int

    @classmethod
    def from_request(
        cls,
        request: ForgeSwarmMaterializeHybridRequest,
        scope: ForgeWorkspaceScopeDict,
        actor: ForgeSessionActorDto,
    ) -> ForgeSwarmMaterializeHybridCommandDto:
        """Build the hybrid materialization command from its schema.

        Args:
            request: Validated Gateway request schema.
            scope: Serialized Forge scope DTO.
            actor: Authenticated actor DTO.
        Return:
            Typed command DTO for the Forge operation payload.
        """
        result = cls(
            scope=scope,
            activity_id=request.activity_id,
            actor=actor.to_dict(),
            swarm_run_id=request.swarm_run_id,
            settlement_id=request.settlement_id,
            goal_id=request.goal_id,
            expected_goal_revision=request.expected_goal_revision,
            expected_dag_revision=request.expected_dag_revision,
            node_id=request.node_id,
            converged_commit_oid=request.converged_commit_oid,
            expected_diff_digest=request.expected_diff_digest,
            settled_at_ms=request.settled_at_ms,
        )
        return result

    def to_dict(self) -> ForgeSwarmMaterializeHybridPayloadDict:
        """Serialize hybrid materialization using exact Forge keys.

        Args:
            None.
        Return:
            Closed `swarm.materialize_hybrid` payload dictionary.
        """
        result: ForgeSwarmMaterializeHybridPayloadDict = ForgeSwarmMaterializeHybridPayloadDict(
            scope=self.scope,
            activity_id=str(self.activity_id),
            actor=self.actor,
            swarm_run_id=str(self.swarm_run_id),
            settlement_id=str(self.settlement_id),
            goal_id=str(self.goal_id),
            expected_goal_revision=self.expected_goal_revision,
            expected_dag_revision=self.expected_dag_revision,
            node_id=str(self.node_id),
            converged_commit_oid=self.converged_commit_oid,
            expected_diff_digest=self.expected_diff_digest,
            settled_at_ms=self.settled_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmSettlementGetCommandDto:
    """Immutable command body reading one Swarm settlement projection."""

    scope: ForgeWorkspaceScopeDict
    swarm_run_id: UUID

    @classmethod
    def from_request(
        cls,
        request: ForgeSwarmSettlementGetRequest,
        scope: ForgeWorkspaceScopeDict,
    ) -> ForgeSwarmSettlementGetCommandDto:
        """Build the settlement lookup command from its validated schema.

        Args:
            request: Validated Gateway request schema.
            scope: Serialized Forge scope DTO.
        Return:
            Typed command DTO for the Forge operation payload.
        """
        result = cls(scope=scope, swarm_run_id=request.swarm_run_id)
        return result

    def to_dict(self) -> ForgeSwarmSettlementGetPayloadDict:
        """Serialize the settlement lookup payload using exact Forge keys.

        Args:
            None.
        Return:
            Closed `swarm.settlement_get` payload dictionary.
        """
        result: ForgeSwarmSettlementGetPayloadDict = ForgeSwarmSettlementGetPayloadDict(
            scope=self.scope,
            swarm_run_id=str(self.swarm_run_id),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmPurgeCommandDto:
    """Immutable command body purging one Swarm workspace projection."""

    scope: ForgeWorkspaceScopeDict
    actor: ForgeSessionActorDict
    swarm_run_id: UUID

    @classmethod
    def from_request(
        cls,
        request: ForgeSwarmPurgeRequest,
        scope: ForgeWorkspaceScopeDict,
        actor: ForgeSessionActorDto,
    ) -> ForgeSwarmPurgeCommandDto:
        """Build the purge command from its validated schema.

        Args:
            request: Validated Gateway request schema.
            scope: Serialized Forge scope DTO.
            actor: Authenticated actor DTO.
        Return:
            Typed command DTO for the Forge operation payload.
        """
        result = cls(scope=scope, actor=actor.to_dict(), swarm_run_id=request.swarm_run_id)
        return result

    def to_dict(self) -> ForgeSwarmPurgePayloadDict:
        """Serialize the purge payload using exact Forge keys.

        Args:
            None.
        Return:
            Closed `swarm.purge` payload dictionary.
        """
        result: ForgeSwarmPurgePayloadDict = ForgeSwarmPurgePayloadDict(
            scope=self.scope,
            actor=self.actor,
            swarm_run_id=str(self.swarm_run_id),
        )
        return result
