"""Immutable Forge Swarm settlement and purge result DTOs."""

from dataclasses import dataclass
from uuid import UUID

from app.forge.application.inner_dto.forge_swarm_command_dto import (
    ForgeSwarmTargetDto,
    target_dto,
)
from app.forge.application.inner_dto.types.forge_swarm_types import (
    ForgeSwarmPurgeResponseDict,
    ForgeSwarmSettledEffectFactResponseDict,
    ForgeSwarmSettledOutboxEntryResponseDict,
    ForgeSwarmSettlementGetResponseDict,
    ForgeSwarmSettlementReceiptResponseDict,
    ForgeSwarmSettleResponseDict,
)
from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmSettledEffectFactResult,
    ForgeSwarmSettledOutboxEntryResult,
    ForgeSwarmSettlementGetResult,
    ForgeSwarmSettlementReceiptResult,
    ForgeSwarmSettleResult,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeResult,
)
from app.shared.ingredient_element.forge.forge_enums import SettlementJournalStateEnum


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
            target=target_dto(target=response.target),
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
        result: ForgeSwarmSettlementReceiptResponseDict = ForgeSwarmSettlementReceiptResponseDict(
            settlement_id=self.settlement_id,
            swarm_run_id=self.swarm_run_id,
            target=self.target.to_dict(),
            state=self.state,
            settled_at_ms=self.settled_at_ms,
            baseline_commit_oid=self.baseline_commit_oid,
            converged_commit_oid=self.converged_commit_oid,
            baseline_tree_blake3=self.baseline_tree_blake3,
            settled_tree_blake3=self.settled_tree_blake3,
            converged_diff_digest=self.converged_diff_digest,
            settled_file_count=self.settled_file_count,
            upserted_paths=list(self.upserted_paths),
            deleted_paths=list(self.deleted_paths),
        )
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
        result: ForgeSwarmSettleResponseDict = ForgeSwarmSettleResponseDict(
            receipt=self.receipt.to_dict(),
            outbox_sequence=self.outbox_sequence,
        )
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
        result: ForgeSwarmSettledEffectFactResponseDict = ForgeSwarmSettledEffectFactResponseDict(
            kind="swarm_settled",
            settlement_id=self.settlement_id,
            workspace_id=self.workspace_id,
            activity_id=self.activity_id,
            swarm_run_id=self.swarm_run_id,
            settled_file_count=self.settled_file_count,
            settled_tree_digest=self.settled_tree_digest,
            converged_diff_digest=self.converged_diff_digest,
            coordinator_agent_id=self.coordinator_agent_id,
            coordinator_session_id=self.coordinator_session_id,
            settled_at_ms=self.settled_at_ms,
        )
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
        result: ForgeSwarmSettledOutboxEntryResponseDict = ForgeSwarmSettledOutboxEntryResponseDict(
            sequence=self.sequence,
            migration_id=self.migration_id,
            destination_id=self.destination_id,
            workspace_id=self.workspace_id,
            fact=self.fact.to_dict(),
        )
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
        result: ForgeSwarmSettlementGetResponseDict = ForgeSwarmSettlementGetResponseDict(
            workspace_id=self.workspace_id,
            swarm_run_id=self.swarm_run_id,
            receipt=receipt,
            outbox_entry=outbox_entry,
        )
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
        result: ForgeSwarmPurgeResponseDict = ForgeSwarmPurgeResponseDict(
            workspace_id=self.workspace_id,
            swarm_run_id=self.swarm_run_id,
            purged=self.purged,
        )
        return result
