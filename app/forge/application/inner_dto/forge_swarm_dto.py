"""Immutable Forge Swarm command and result DTOs."""

from dataclasses import dataclass
from uuid import UUID

from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeSessionActorDto,
)
from app.forge.application.inner_dto.types.forge_envelope_types import (
    ForgeSessionActorDict,
    ForgeWorkspaceScopeDict,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmConflictResponseDict,
    ForgeSwarmConvergedResponseDict,
    ForgeSwarmConvergenceCandidateDict,
    ForgeSwarmConvergePayloadDict,
    ForgeSwarmMaterializeHybridPayloadDict,
    ForgeSwarmMemberCapturePayloadDict,
    ForgeSwarmMemberOutputResponseDict,
    ForgeSwarmPurgePayloadDict,
    ForgeSwarmPurgeResponseDict,
    ForgeSwarmSettledEffectFactResponseDict,
    ForgeSwarmSettledOutboxEntryResponseDict,
    ForgeSwarmSettlementGetPayloadDict,
    ForgeSwarmSettlementGetResponseDict,
    ForgeSwarmSettlementReceiptResponseDict,
    ForgeSwarmSettlePayloadDict,
    ForgeSwarmSettleResponseDict,
    ForgeSwarmTargetDict,
    ForgeSwarmWorkspaceGetPayloadDict,
    ForgeSwarmWorkspaceGetResponseDict,
    ForgeSwarmWorkspaceProvisionPayloadDict,
    ForgeSwarmWorkspaceReceiptResponseDict,
)
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import (
    ForgeSwarmMemberCaptureRequest,
    ForgeSwarmMemberOutputResult,
)
from app.forge.schema.swarm.convergence.forge_swarm_convergence_schema import (
    ForgeSwarmConvergedResult,
    ForgeSwarmConvergeRequest,
    ForgeSwarmConvergeResult,
)
from app.forge.schema.swarm.identity.forge_swarm_identity_schema import (
    ForgeSwarmStandaloneTarget,
    ForgeSwarmTarget,
)
from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmMaterializeHybridRequest,
    ForgeSwarmSettledEffectFactResult,
    ForgeSwarmSettledOutboxEntryResult,
    ForgeSwarmSettlementGetRequest,
    ForgeSwarmSettlementGetResult,
    ForgeSwarmSettlementReceiptResult,
    ForgeSwarmSettleRequest,
    ForgeSwarmSettleResult,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeRequest,
    ForgeSwarmPurgeResult,
    ForgeSwarmWorkspaceGetRequest,
    ForgeSwarmWorkspaceGetResult,
    ForgeSwarmWorkspaceProvisionRequest,
    ForgeSwarmWorkspaceReceiptResult,
)
from app.shared.ingredient_element.forge.forge_enums import (
    SettlementJournalStateEnum,
    SwarmConvergenceStatusEnum,
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
            result: ForgeSwarmTargetDict = {"kind": self.kind.value}
            return result
        if self.goal_id is None or self.dag_revision is None or self.node_id is None:
            raise ValueError("DAG node hybrid target requires goal, revision, and node identities")
        result = {
            "kind": self.kind.value,
            "goal_id": str(self.goal_id),
            "dag_revision": self.dag_revision,
            "node_id": str(self.node_id),
        }
        return result


def _target_dto(target: ForgeSwarmTarget) -> ForgeSwarmTargetDto:
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
            target=_target_dto(target=request.target),
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
        result: ForgeSwarmWorkspaceProvisionPayloadDict = {
            "scope": self.scope,
            "actor": self.actor,
            "swarm_run_id": str(self.swarm_run_id),
            "member_id": str(self.member_id),
            "mode": self.mode.value,
            "target": self.target.to_dict(),
            "candidate_commit_oid": self.candidate_commit_oid,
            "observed_at_ms": self.observed_at_ms,
        }
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
        result: ForgeSwarmWorkspaceGetPayloadDict = {
            "scope": self.scope,
            "swarm_run_id": str(self.swarm_run_id),
            "member_id": str(self.member_id),
        }
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
        result: ForgeSwarmMemberCapturePayloadDict = {
            "scope": self.scope,
            "actor": self.actor,
            "swarm_run_id": str(self.swarm_run_id),
            "member_id": str(self.member_id),
            "captured_at_ms": self.captured_at_ms,
        }
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
        result: ForgeSwarmConvergenceCandidateDict = {"member_id": str(self.member_id)}
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
        result: ForgeSwarmConvergePayloadDict = {
            "scope": self.scope,
            "actor": self.actor,
            "swarm_run_id": str(self.swarm_run_id),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "observed_at_ms": self.observed_at_ms,
        }
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
        result: ForgeSwarmSettlePayloadDict = {
            "scope": self.scope,
            "activity_id": str(self.activity_id) if self.activity_id is not None else None,
            "actor": self.actor,
            "coordinator_agent_id": str(self.coordinator_agent_id),
            "swarm_run_id": str(self.swarm_run_id),
            "settlement_id": str(self.settlement_id),
            "converged_commit_oid": self.converged_commit_oid,
            "expected_diff_digest": self.expected_diff_digest,
            "settled_at_ms": self.settled_at_ms,
        }
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
        result: ForgeSwarmMaterializeHybridPayloadDict = {
            "scope": self.scope,
            "activity_id": str(self.activity_id),
            "actor": self.actor,
            "swarm_run_id": str(self.swarm_run_id),
            "settlement_id": str(self.settlement_id),
            "goal_id": str(self.goal_id),
            "expected_goal_revision": self.expected_goal_revision,
            "expected_dag_revision": self.expected_dag_revision,
            "node_id": str(self.node_id),
            "converged_commit_oid": self.converged_commit_oid,
            "expected_diff_digest": self.expected_diff_digest,
            "settled_at_ms": self.settled_at_ms,
        }
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
        result: ForgeSwarmSettlementGetPayloadDict = {
            "scope": self.scope,
            "swarm_run_id": str(self.swarm_run_id),
        }
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
        result: ForgeSwarmPurgePayloadDict = {
            "scope": self.scope,
            "actor": self.actor,
            "swarm_run_id": str(self.swarm_run_id),
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmMemberOutputInnerDto:
    """Immutable result DTO for a captured member workspace output."""

    swarm_run_id: UUID
    member_id: UUID
    mode: SwarmWorkspaceModeEnum
    input_commit_oid: str
    output_commit_oid: str
    initial_tree_blake3: str
    final_tree_blake3: str
    final_file_count: int
    changed_paths: tuple[str, ...]
    diff_digest: str
    captured_at_ms: int

    @classmethod
    def from_schema(
        cls,
        response: ForgeSwarmMemberOutputResult,
    ) -> ForgeSwarmMemberOutputInnerDto:
        """Capture one validated output schema as an immutable result DTO.

        Args:
            response: Validated Gateway output response schema.
        Return:
            Immutable result DTO.
        """
        result = cls(
            swarm_run_id=response.swarm_run_id,
            member_id=response.member_id,
            mode=SwarmWorkspaceModeEnum(response.mode),
            input_commit_oid=response.input_commit_oid,
            output_commit_oid=response.output_commit_oid,
            initial_tree_blake3=response.initial_tree_blake3,
            final_tree_blake3=response.final_tree_blake3,
            final_file_count=response.final_file_count,
            changed_paths=tuple(response.changed_paths),
            diff_digest=response.diff_digest,
            captured_at_ms=response.captured_at_ms,
        )
        return result

    def to_dict(self) -> ForgeSwarmMemberOutputResponseDict:
        """Serialize the validated output result using typed fields.

        Args:
            None.
        Return:
            Complete member output response dictionary.
        """
        result: ForgeSwarmMemberOutputResponseDict = {
            "swarm_run_id": self.swarm_run_id,
            "member_id": self.member_id,
            "mode": self.mode,
            "input_commit_oid": self.input_commit_oid,
            "output_commit_oid": self.output_commit_oid,
            "initial_tree_blake3": self.initial_tree_blake3,
            "final_tree_blake3": self.final_tree_blake3,
            "final_file_count": self.final_file_count,
            "changed_paths": list(self.changed_paths),
            "diff_digest": self.diff_digest,
            "captured_at_ms": self.captured_at_ms,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmWorkspaceReceiptInnerDto:
    """Immutable result DTO for a provisioned member workspace."""

    swarm_run_id: UUID
    member_id: UUID
    mode: SwarmWorkspaceModeEnum
    target: ForgeSwarmTargetDto
    worktree_path: str
    provisioned_at_ms: int
    initial_tree_blake3: str
    initial_file_count: int
    input_commit_oid: str
    completed: ForgeSwarmMemberOutputInnerDto | None

    @classmethod
    def from_schema(
        cls,
        response: ForgeSwarmWorkspaceReceiptResult,
    ) -> ForgeSwarmWorkspaceReceiptInnerDto:
        """Capture one validated workspace receipt schema.

        Args:
            response: Validated Gateway workspace receipt schema.
        Return:
            Immutable result DTO.
        """
        completed = response.completed
        completed_dto = (
            ForgeSwarmMemberOutputInnerDto.from_schema(response=completed)
            if completed is not None
            else None
        )
        result = cls(
            swarm_run_id=response.swarm_run_id,
            member_id=response.member_id,
            mode=SwarmWorkspaceModeEnum(response.mode),
            target=_target_dto(target=response.target),
            worktree_path=response.worktree_path,
            provisioned_at_ms=response.provisioned_at_ms,
            initial_tree_blake3=response.initial_tree_blake3,
            initial_file_count=response.initial_file_count,
            input_commit_oid=response.input_commit_oid,
            completed=completed_dto,
        )
        return result

    def to_dict(self) -> ForgeSwarmWorkspaceReceiptResponseDict:
        """Serialize the provisioned workspace result with nullable fields.

        Args:
            None.
        Return:
            Complete workspace receipt response dictionary.
        """
        completed = self.completed
        if completed is not None:
            completed = completed.to_dict()
        result: ForgeSwarmWorkspaceReceiptResponseDict = {
            "swarm_run_id": self.swarm_run_id,
            "member_id": self.member_id,
            "mode": self.mode,
            "target": self.target.to_dict(),
            "worktree_path": self.worktree_path,
            "provisioned_at_ms": self.provisioned_at_ms,
            "initial_tree_blake3": self.initial_tree_blake3,
            "initial_file_count": self.initial_file_count,
            "input_commit_oid": self.input_commit_oid,
            "completed": completed,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmWorkspaceGetInnerDto:
    """Immutable result DTO for a Swarm workspace lookup."""

    workspace_id: UUID
    swarm_run_id: UUID
    member_id: UUID
    found: bool
    receipt: ForgeSwarmWorkspaceReceiptInnerDto | None

    @classmethod
    def from_schema(
        cls,
        response: ForgeSwarmWorkspaceGetResult,
    ) -> ForgeSwarmWorkspaceGetInnerDto:
        """Capture one validated workspace lookup schema.

        Args:
            response: Validated Gateway workspace lookup schema.
        Return:
            Immutable result DTO.
        """
        receipt = response.receipt
        receipt_dto = (
            ForgeSwarmWorkspaceReceiptInnerDto.from_schema(response=receipt)
            if receipt is not None
            else None
        )
        result = cls(
            workspace_id=response.workspace_id,
            swarm_run_id=response.swarm_run_id,
            member_id=response.member_id,
            found=response.found,
            receipt=receipt_dto,
        )
        return result

    def to_dict(self) -> ForgeSwarmWorkspaceGetResponseDict:
        """Serialize the workspace lookup with its source presence flag.

        Args:
            None.
        Return:
            Complete workspace lookup response dictionary.
        """
        receipt = self.receipt
        if receipt is not None:
            receipt = receipt.to_dict()
        result: ForgeSwarmWorkspaceGetResponseDict = {
            "workspace_id": self.workspace_id,
            "swarm_run_id": self.swarm_run_id,
            "member_id": self.member_id,
            "found": self.found,
            "receipt": receipt,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmConvergedInnerDto:
    """Immutable result DTO for a successful Swarm convergence."""

    swarm_run_id: UUID
    converged_commit_oid: str
    converged_tree_blake3: str
    converged_diff_digest: str
    changed_files: tuple[str, ...]

    def to_dict(self) -> ForgeSwarmConvergedResponseDict:
        """Serialize the tagged successful convergence result.

        Args:
            None.
        Return:
            Closed converged result dictionary.
        """
        result: ForgeSwarmConvergedResponseDict = {
            "status": SwarmConvergenceStatusEnum.CONVERGED.value,
            "swarm_run_id": self.swarm_run_id,
            "converged_commit_oid": self.converged_commit_oid,
            "converged_tree_blake3": self.converged_tree_blake3,
            "converged_diff_digest": self.converged_diff_digest,
            "changed_files": list(self.changed_files),
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmConflictInnerDto:
    """Immutable result DTO for a valid Swarm convergence conflict."""

    swarm_run_id: UUID
    conflicting_member_id: UUID
    details: tuple[str, ...]

    def to_dict(self) -> ForgeSwarmConflictResponseDict:
        """Serialize the tagged conflict result.

        Args:
            None.
        Return:
            Closed conflict result dictionary.
        """
        result: ForgeSwarmConflictResponseDict = {
            "status": SwarmConvergenceStatusEnum.CONFLICT.value,
            "swarm_run_id": self.swarm_run_id,
            "conflicting_member_id": self.conflicting_member_id,
            "details": list(self.details),
        }
        return result


ForgeSwarmConvergeInnerDto = ForgeSwarmConvergedInnerDto | ForgeSwarmConflictInnerDto


def converge_inner_dto(response: ForgeSwarmConvergeResult) -> ForgeSwarmConvergeInnerDto:
    """Map the validated convergence branch to its immutable result DTO.

    Args:
        response: Validated tagged Forge convergence result.
    Return:
        Immutable converged or conflict result DTO.
    """
    if isinstance(response.root, ForgeSwarmConvergedResult):
        result: ForgeSwarmConvergeInnerDto = ForgeSwarmConvergedInnerDto(
            swarm_run_id=response.root.swarm_run_id,
            converged_commit_oid=response.root.converged_commit_oid,
            converged_tree_blake3=response.root.converged_tree_blake3,
            converged_diff_digest=response.root.converged_diff_digest,
            changed_files=tuple(response.root.changed_files),
        )
        return result
    result = ForgeSwarmConflictInnerDto(
        swarm_run_id=response.root.swarm_run_id,
        conflicting_member_id=response.root.conflicting_member_id,
        details=tuple(response.root.details),
    )
    return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmSettlementReceiptInnerDto:
    """Immutable result DTO for a Swarm settlement receipt."""

    settlement_id: str
    swarm_run_id: UUID
    target: ForgeSwarmTargetDto
    state: SettlementJournalStateEnum
    settled_at_ms: int
    baseline_commit_oid: str
    converged_commit_oid: str
    baseline_tree_blake3: str
    settled_tree_blake3: str
    converged_diff_digest: str
    settled_file_count: int
    upserted_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]

    @classmethod
    def from_schema(
        cls,
        response: ForgeSwarmSettlementReceiptResult,
    ) -> ForgeSwarmSettlementReceiptInnerDto:
        """Capture one validated settlement receipt schema.

        Args:
            response: Validated Gateway settlement receipt schema.
        Return:
            Immutable result DTO.
        """
        result = cls(
            settlement_id=response.settlement_id,
            swarm_run_id=response.swarm_run_id,
            target=_target_dto(target=response.target),
            state=SettlementJournalStateEnum(response.state),
            settled_at_ms=response.settled_at_ms,
            baseline_commit_oid=response.baseline_commit_oid,
            converged_commit_oid=response.converged_commit_oid,
            baseline_tree_blake3=response.baseline_tree_blake3,
            settled_tree_blake3=response.settled_tree_blake3,
            converged_diff_digest=response.converged_diff_digest,
            settled_file_count=response.settled_file_count,
            upserted_paths=tuple(response.upserted_paths),
            deleted_paths=tuple(response.deleted_paths),
        )
        return result

    def to_dict(self) -> ForgeSwarmSettlementReceiptResponseDict:
        """Serialize every settlement receipt field to its typed response.

        Args:
            None.
        Return:
            Complete settlement receipt response dictionary.
        """
        result: ForgeSwarmSettlementReceiptResponseDict = {
            "settlement_id": self.settlement_id,
            "swarm_run_id": self.swarm_run_id,
            "target": self.target.to_dict(),
            "state": self.state,
            "settled_at_ms": self.settled_at_ms,
            "baseline_commit_oid": self.baseline_commit_oid,
            "converged_commit_oid": self.converged_commit_oid,
            "baseline_tree_blake3": self.baseline_tree_blake3,
            "settled_tree_blake3": self.settled_tree_blake3,
            "converged_diff_digest": self.converged_diff_digest,
            "settled_file_count": self.settled_file_count,
            "upserted_paths": list(self.upserted_paths),
            "deleted_paths": list(self.deleted_paths),
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmSettleInnerDto:
    """Immutable result DTO for a Swarm settlement operation."""

    receipt: ForgeSwarmSettlementReceiptInnerDto
    outbox_sequence: int | None

    @classmethod
    def from_schema(cls, response: ForgeSwarmSettleResult) -> ForgeSwarmSettleInnerDto:
        """Capture one validated settlement operation schema.

        Args:
            response: Validated Gateway settlement response schema.
        Return:
            Immutable result DTO.
        """
        result = cls(
            receipt=ForgeSwarmSettlementReceiptInnerDto.from_schema(response=response.receipt),
            outbox_sequence=response.outbox_sequence,
        )
        return result

    def to_dict(self) -> ForgeSwarmSettleResponseDict:
        """Serialize settlement receipt and nullable outbox sequence.

        Args:
            None.
        Return:
            Complete settlement result response dictionary.
        """
        result: ForgeSwarmSettleResponseDict = {
            "receipt": self.receipt.to_dict(),
            "outbox_sequence": self.outbox_sequence,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmSettledEffectFactInnerDto:
    """Immutable result DTO for the Swarm settled effect fact."""

    settlement_id: UUID
    workspace_id: UUID
    activity_id: UUID | None
    swarm_run_id: UUID
    settled_file_count: int
    settled_tree_digest: str
    converged_diff_digest: str
    coordinator_agent_id: UUID
    coordinator_session_id: UUID | None
    settled_at_ms: int

    @classmethod
    def from_schema(
        cls,
        response: ForgeSwarmSettledEffectFactResult,
    ) -> ForgeSwarmSettledEffectFactInnerDto:
        """Capture one validated Swarm effect fact schema.

        Args:
            response: Validated Gateway effect fact schema.
        Return:
            Immutable result DTO.
        """
        result = cls(
            settlement_id=response.settlement_id,
            workspace_id=response.workspace_id,
            activity_id=response.activity_id,
            swarm_run_id=response.swarm_run_id,
            settled_file_count=response.settled_file_count,
            settled_tree_digest=response.settled_tree_digest,
            converged_diff_digest=response.converged_diff_digest,
            coordinator_agent_id=response.coordinator_agent_id,
            coordinator_session_id=response.coordinator_session_id,
            settled_at_ms=response.settled_at_ms,
        )
        return result

    def to_dict(self) -> ForgeSwarmSettledEffectFactResponseDict:
        """Serialize the kind-six Swarm settled fact.

        Args:
            None.
        Return:
            Complete effect fact response dictionary.
        """
        result: ForgeSwarmSettledEffectFactResponseDict = {
            "kind": "swarm_settled",
            "settlement_id": self.settlement_id,
            "workspace_id": self.workspace_id,
            "activity_id": self.activity_id,
            "swarm_run_id": self.swarm_run_id,
            "settled_file_count": self.settled_file_count,
            "settled_tree_digest": self.settled_tree_digest,
            "converged_diff_digest": self.converged_diff_digest,
            "coordinator_agent_id": self.coordinator_agent_id,
            "coordinator_session_id": self.coordinator_session_id,
            "settled_at_ms": self.settled_at_ms,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmSettledOutboxEntryInnerDto:
    """Immutable result DTO for a Swarm settlement outbox row."""

    sequence: int
    migration_id: UUID
    destination_id: UUID
    workspace_id: UUID
    fact: ForgeSwarmSettledEffectFactInnerDto

    @classmethod
    def from_schema(
        cls,
        response: ForgeSwarmSettledOutboxEntryResult,
    ) -> ForgeSwarmSettledOutboxEntryInnerDto:
        """Capture one validated outbox entry schema.

        Args:
            response: Validated Gateway outbox entry schema.
        Return:
            Immutable result DTO.
        """
        result = cls(
            sequence=response.sequence,
            migration_id=response.migration_id,
            destination_id=response.destination_id,
            workspace_id=response.workspace_id,
            fact=ForgeSwarmSettledEffectFactInnerDto.from_schema(response=response.fact),
        )
        return result

    def to_dict(self) -> ForgeSwarmSettledOutboxEntryResponseDict:
        """Serialize the outbox identity and typed effect fact.

        Args:
            None.
        Return:
            Complete outbox entry response dictionary.
        """
        result: ForgeSwarmSettledOutboxEntryResponseDict = {
            "sequence": self.sequence,
            "migration_id": self.migration_id,
            "destination_id": self.destination_id,
            "workspace_id": self.workspace_id,
            "fact": self.fact.to_dict(),
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmSettlementGetInnerDto:
    """Immutable result DTO for a Swarm settlement lookup."""

    workspace_id: UUID
    swarm_run_id: UUID
    receipt: ForgeSwarmSettlementReceiptInnerDto | None
    outbox_entry: ForgeSwarmSettledOutboxEntryInnerDto | None

    @classmethod
    def from_schema(
        cls,
        response: ForgeSwarmSettlementGetResult,
    ) -> ForgeSwarmSettlementGetInnerDto:
        """Capture one validated settlement lookup schema.

        Args:
            response: Validated Gateway settlement lookup schema.
        Return:
            Immutable result DTO.
        """
        receipt = response.receipt
        receipt_dto = (
            ForgeSwarmSettlementReceiptInnerDto.from_schema(response=receipt)
            if receipt is not None
            else None
        )
        outbox_entry = response.outbox_entry
        outbox_dto = (
            ForgeSwarmSettledOutboxEntryInnerDto.from_schema(response=outbox_entry)
            if outbox_entry is not None
            else None
        )
        result = cls(
            workspace_id=response.workspace_id,
            swarm_run_id=response.swarm_run_id,
            receipt=receipt_dto,
            outbox_entry=outbox_dto,
        )
        return result

    def to_dict(self) -> ForgeSwarmSettlementGetResponseDict:
        """Serialize the settlement lookup with both nullable projections.

        Args:
            None.
        Return:
            Complete settlement lookup response dictionary.
        """
        receipt = self.receipt
        if receipt is not None:
            receipt = receipt.to_dict()
        outbox_entry = self.outbox_entry
        if outbox_entry is not None:
            outbox_entry = outbox_entry.to_dict()
        result: ForgeSwarmSettlementGetResponseDict = {
            "workspace_id": self.workspace_id,
            "swarm_run_id": self.swarm_run_id,
            "receipt": receipt,
            "outbox_entry": outbox_entry,
        }
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeSwarmPurgeInnerDto:
    """Immutable result DTO for a Swarm purge."""

    workspace_id: UUID
    swarm_run_id: UUID
    purged: bool

    @classmethod
    def from_schema(cls, response: ForgeSwarmPurgeResult) -> ForgeSwarmPurgeInnerDto:
        """Capture one validated Swarm purge schema.

        Args:
            response: Validated Gateway purge response schema.
        Return:
            Immutable result DTO.
        """
        result = cls(
            workspace_id=response.workspace_id,
            swarm_run_id=response.swarm_run_id,
            purged=response.purged,
        )
        return result

    def to_dict(self) -> ForgeSwarmPurgeResponseDict:
        """Serialize the Swarm purge result.

        Args:
            None.
        Return:
            Complete purge response dictionary.
        """
        result: ForgeSwarmPurgeResponseDict = {
            "workspace_id": self.workspace_id,
            "swarm_run_id": self.swarm_run_id,
            "purged": self.purged,
        }
        return result
