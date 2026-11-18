"""Immutable Forge Swarm result and projection DTOs."""

from dataclasses import dataclass
from uuid import UUID

from app.forge.application.inner_dto.forge_swarm_command_dto import (
    ForgeSwarmTargetDto,
    target_dto,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmConflictResponseDict,
    ForgeSwarmConvergedResponseDict,
    ForgeSwarmMemberOutputResponseDict,
    ForgeSwarmWorkspaceGetResponseDict,
    ForgeSwarmWorkspaceReceiptResponseDict,
)
from app.forge.schema.swarm.capture.forge_swarm_capture_schema import (
    ForgeSwarmMemberOutputResult,
)
from app.forge.schema.swarm.convergence.forge_swarm_convergence_schema import (
    ForgeSwarmConvergedResult,
    ForgeSwarmConvergeResult,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmWorkspaceGetResult,
    ForgeSwarmWorkspaceReceiptResult,
)
from app.shared.ingredient_element.forge.forge_enums import (
    SwarmConvergenceStatusEnum,
    SwarmWorkspaceModeEnum,
)


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
        result: ForgeSwarmMemberOutputResponseDict = ForgeSwarmMemberOutputResponseDict(
            swarm_run_id=self.swarm_run_id,
            member_id=self.member_id,
            mode=self.mode,
            input_commit_oid=self.input_commit_oid,
            output_commit_oid=self.output_commit_oid,
            initial_tree_blake3=self.initial_tree_blake3,
            final_tree_blake3=self.final_tree_blake3,
            final_file_count=self.final_file_count,
            changed_paths=list(self.changed_paths),
            diff_digest=self.diff_digest,
            captured_at_ms=self.captured_at_ms,
        )
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
            target=target_dto(target=response.target),
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
        result: ForgeSwarmWorkspaceReceiptResponseDict = ForgeSwarmWorkspaceReceiptResponseDict(
            swarm_run_id=self.swarm_run_id,
            member_id=self.member_id,
            mode=self.mode,
            target=self.target.to_dict(),
            worktree_path=self.worktree_path,
            provisioned_at_ms=self.provisioned_at_ms,
            initial_tree_blake3=self.initial_tree_blake3,
            initial_file_count=self.initial_file_count,
            input_commit_oid=self.input_commit_oid,
            completed=completed,
        )
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
        result: ForgeSwarmWorkspaceGetResponseDict = ForgeSwarmWorkspaceGetResponseDict(
            workspace_id=self.workspace_id,
            swarm_run_id=self.swarm_run_id,
            member_id=self.member_id,
            found=self.found,
            receipt=receipt,
        )
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
        result: ForgeSwarmConvergedResponseDict = ForgeSwarmConvergedResponseDict(
            status=SwarmConvergenceStatusEnum.CONVERGED.value,
            swarm_run_id=self.swarm_run_id,
            converged_commit_oid=self.converged_commit_oid,
            converged_tree_blake3=self.converged_tree_blake3,
            converged_diff_digest=self.converged_diff_digest,
            changed_files=list(self.changed_files),
        )
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
        result: ForgeSwarmConflictResponseDict = ForgeSwarmConflictResponseDict(
            status=SwarmConvergenceStatusEnum.CONFLICT.value,
            swarm_run_id=self.swarm_run_id,
            conflicting_member_id=self.conflicting_member_id,
            details=list(self.details),
        )
        return result


type ForgeSwarmConvergeInnerDto = ForgeSwarmConvergedInnerDto | ForgeSwarmConflictInnerDto


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
