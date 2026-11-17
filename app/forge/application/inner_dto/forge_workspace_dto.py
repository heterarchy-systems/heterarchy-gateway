"""Immutable DTO mappings for Forge Location, Workspace, Activity, and DAG commands."""

from dataclasses import dataclass
from uuid import UUID

from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeSessionActorDto,
    ForgeWorkspaceScopeDto,
)
from app.forge.application.inner_dto.types.forge_workspace_types import (
    ForgeActivityListPayloadDict,
    ForgeActivityListResultDict,
    ForgeActivityProjectionDict,
    ForgeActivityScopeDict,
    ForgeDagCurrentFoundResultDict,
    ForgeDagCurrentMissingResultDict,
    ForgeDagEdgeDict,
    ForgeDagLineageDict,
    ForgeDagNodeDict,
    ForgeDagReadCurrentPayloadDict,
    ForgeDagSettlePayloadDict,
    ForgeDagSettleResultDict,
    ForgeLocationEntryDict,
    ForgeLocationListPayloadDict,
    ForgeLocationListResultDict,
    ForgeWorkspaceEntryDict,
    ForgeWorkspaceListPayloadDict,
    ForgeWorkspaceListResultDict,
)
from app.forge.schema.activity.forge_activity_schema import (
    ForgeActivityListPayload,
    ForgeActivityListResult,
    ForgeActivityProjection,
    ForgeActivityScope,
)
from app.forge.schema.dag.forge_dag_schema import (
    ForgeDagCurrentFoundResult,
    ForgeDagEdge,
    ForgeDagLineage,
    ForgeDagNode,
    ForgeDagReadCurrentPayload,
    ForgeDagSettlePayload,
    ForgeDagSettleResult,
)
from app.forge.schema.location.forge_location_schema import (
    ForgeLocationEntry,
    ForgeLocationListResult,
)
from app.forge.schema.types.forge_types import Int64, UInt32, UInt64
from app.forge.schema.workspace.forge_workspace_schema import (
    ForgeWorkspaceEntry,
    ForgeWorkspaceListPayload,
    ForgeWorkspaceListResult,
)
from app.shared.ingredient_element.forge.forge_enums import (
    ActivityLivenessEnum,
    ActivityStateEnum,
    DagLineageKindEnum,
    DagNodeLifecycleEnum,
    DagNodeStatusEnum,
    LocationStateEnum,
    SettlementJournalStateEnum,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeLocationListCommandDto:
    """Immutable empty command payload for location.list."""

    def to_dict(self) -> ForgeLocationListPayloadDict:
        """Serialize the empty strict Source payload.

        Args:
            None.
        Return:
            Empty typed location.list payload.
        """
        result: ForgeLocationListPayloadDict = ForgeLocationListPayloadDict()
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeWorkspaceListCommandDto:
    """Immutable command payload for workspace.list."""

    location_id: UUID
    expected_revision: Int64

    @classmethod
    def from_payload(cls, payload: ForgeWorkspaceListPayload) -> ForgeWorkspaceListCommandDto:
        """Build a Workspace list command from its validated public payload.

        Args:
            payload: Strict workspace.list operation payload.
        Return:
            Immutable workspace.list command DTO.
        """
        result = cls(
            location_id=payload.location_id,
            expected_revision=payload.expected_revision,
        )
        return result

    def to_dict(self) -> ForgeWorkspaceListPayloadDict:
        """Serialize the exact workspace.list Source payload.

        Args:
            None.
        Return:
            Typed workspace.list operation payload.
        """
        result: ForgeWorkspaceListPayloadDict = ForgeWorkspaceListPayloadDict(
            location_id=str(self.location_id),
            expected_revision=self.expected_revision,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeActivityListCommandDto:
    """Immutable command payload for activity.list."""

    locator: str
    workspace_id: UUID
    workspace_revision: Int64
    limit: UInt32

    @classmethod
    def from_payload(cls, payload: ForgeActivityListPayload) -> ForgeActivityListCommandDto:
        """Build an Activity list command from its validated public payload.

        Args:
            payload: Strict activity.list operation payload.
        Return:
            Immutable activity.list command DTO.
        """
        result = cls(
            locator=payload.locator,
            workspace_id=payload.workspace_id,
            workspace_revision=payload.workspace_revision,
            limit=payload.limit,
        )
        return result

    def to_dict(self) -> ForgeActivityListPayloadDict:
        """Serialize the exact activity.list Source payload.

        Args:
            None.
        Return:
            Typed activity.list operation payload.
        """
        result: ForgeActivityListPayloadDict = ForgeActivityListPayloadDict(
            locator=self.locator,
            workspace_id=str(self.workspace_id),
            workspace_revision=self.workspace_revision,
            limit=self.limit,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeDagReadCurrentCommandDto:
    """Immutable command payload for dag.read_current."""

    scope: ForgeWorkspaceScopeDto
    goal_id: UUID

    @classmethod
    def from_payload(
        cls,
        payload: ForgeDagReadCurrentPayload,
        scope: ForgeWorkspaceScopeDto,
    ) -> ForgeDagReadCurrentCommandDto:
        """Build a current DAG read command from its strict input contract.

        Args:
            payload: Strict dag.read_current operation payload.
            scope: Immutable normalized Workspace scope.
        Return:
            Immutable dag.read_current command DTO.
        """
        result = cls(scope=scope, goal_id=payload.goal_id)
        return result

    def to_dict(self) -> ForgeDagReadCurrentPayloadDict:
        """Serialize the exact dag.read_current Source payload.

        Args:
            None.
        Return:
            Typed dag.read_current operation payload.
        """
        result: ForgeDagReadCurrentPayloadDict = ForgeDagReadCurrentPayloadDict(
            scope=self.scope.to_dict(),
            goal_id=str(self.goal_id),
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeDagSettleCommandDto:
    """Immutable command payload for dag.settle."""

    scope: ForgeWorkspaceScopeDto
    activity_id: UUID
    actor: ForgeSessionActorDto
    goal_id: UUID
    expected_goal_revision: Int64
    expected_dag_revision: Int64
    settlement_id: UUID
    observed_at_ms: Int64

    @classmethod
    def from_payload(
        cls,
        payload: ForgeDagSettlePayload,
        scope: ForgeWorkspaceScopeDto,
        actor: ForgeSessionActorDto,
    ) -> ForgeDagSettleCommandDto:
        """Build a DAG settlement command from strict input and actor DTOs.

        Args:
            payload: Strict dag.settle operation payload.
            scope: Immutable normalized Workspace scope.
            actor: Immutable session actor with omitted principal options normalized.
        Return:
            Immutable dag.settle command DTO.
        """
        result = cls(
            scope=scope,
            activity_id=payload.activity_id,
            actor=actor,
            goal_id=payload.goal_id,
            expected_goal_revision=payload.expected_goal_revision,
            expected_dag_revision=payload.expected_dag_revision,
            settlement_id=payload.settlement_id,
            observed_at_ms=payload.observed_at_ms,
        )
        return result

    def to_dict(self) -> ForgeDagSettlePayloadDict:
        """Serialize the exact dag.settle Source payload.

        Args:
            None.
        Return:
            Typed dag.settle operation payload.
        """
        result: ForgeDagSettlePayloadDict = ForgeDagSettlePayloadDict(
            scope=self.scope.to_dict(),
            activity_id=str(self.activity_id),
            actor=self.actor.to_dict(),
            goal_id=str(self.goal_id),
            expected_goal_revision=self.expected_goal_revision,
            expected_dag_revision=self.expected_dag_revision,
            settlement_id=str(self.settlement_id),
            observed_at_ms=self.observed_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeLocationEntryDto:
    """Immutable registered Location result."""

    location_id: UUID
    display_name: str
    revision: Int64
    state: LocationStateEnum

    @classmethod
    def from_schema(cls, entry: ForgeLocationEntry) -> ForgeLocationEntryDto:
        """Convert a validated Location result to its immutable DTO.

        Args:
            entry: Validated Forge Location entry.
        Return:
            Immutable Location result DTO.
        """
        result = cls(
            location_id=entry.location_id,
            display_name=entry.display_name,
            revision=entry.revision,
            state=LocationStateEnum(entry.state),
        )
        return result

    def to_dict(self) -> ForgeLocationEntryDict:
        """Serialize the exact Location result fields.

        Args:
            None.
        Return:
            Typed Location result object.
        """
        result: ForgeLocationEntryDict = ForgeLocationEntryDict(
            location_id=self.location_id,
            display_name=self.display_name,
            revision=self.revision,
            state=self.state,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeLocationListResultDto:
    """Immutable collection returned by location.list."""

    entries: tuple[ForgeLocationEntryDto, ...]

    @classmethod
    def from_schema(cls, result_schema: ForgeLocationListResult) -> ForgeLocationListResultDto:
        """Convert the validated Location result and each nested entry.

        Args:
            result_schema: Validated location.list result payload.
        Return:
            Immutable Location collection DTO.
        """
        entries = tuple(
            ForgeLocationEntryDto.from_schema(entry=entry) for entry in result_schema.entries
        )
        result = cls(entries=entries)
        return result

    def to_dict(self) -> ForgeLocationListResultDict:
        """Serialize the typed location.list result payload.

        Args:
            None.
        Return:
            Typed Location list result.
        """
        result: ForgeLocationListResultDict = ForgeLocationListResultDict(
            entries=[entry.to_dict() for entry in self.entries]
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeWorkspaceEntryDto:
    """Immutable Workspace entry returned by workspace.list."""

    locator: str
    display_name: str
    workspace_id: UUID
    workspace_revision: Int64

    @classmethod
    def from_schema(cls, entry: ForgeWorkspaceEntry) -> ForgeWorkspaceEntryDto:
        """Convert a validated Workspace entry to its immutable DTO.

        Args:
            entry: Validated Forge Workspace entry.
        Return:
            Immutable Workspace entry DTO.
        """
        result = cls(
            locator=entry.locator,
            display_name=entry.display_name,
            workspace_id=entry.workspace_id,
            workspace_revision=entry.workspace_revision,
        )
        return result

    def to_dict(self) -> ForgeWorkspaceEntryDict:
        """Serialize the exact Workspace entry fields.

        Args:
            None.
        Return:
            Typed Workspace entry object.
        """
        result: ForgeWorkspaceEntryDict = ForgeWorkspaceEntryDict(
            locator=self.locator,
            display_name=self.display_name,
            workspace_id=self.workspace_id,
            workspace_revision=self.workspace_revision,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeWorkspaceListResultDto:
    """Immutable collection returned by workspace.list."""

    entries: tuple[ForgeWorkspaceEntryDto, ...]

    @classmethod
    def from_schema(cls, result_schema: ForgeWorkspaceListResult) -> ForgeWorkspaceListResultDto:
        """Convert the validated Workspace result and each nested entry.

        Args:
            result_schema: Validated workspace.list result payload.
        Return:
            Immutable Workspace collection DTO.
        """
        entries = tuple(
            ForgeWorkspaceEntryDto.from_schema(entry=entry) for entry in result_schema.entries
        )
        result = cls(entries=entries)
        return result

    def to_dict(self) -> ForgeWorkspaceListResultDict:
        """Serialize the typed workspace.list result payload.

        Args:
            None.
        Return:
            Typed Workspace list result.
        """
        result: ForgeWorkspaceListResultDict = ForgeWorkspaceListResultDict(
            entries=[entry.to_dict() for entry in self.entries],
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeActivityScopeDto:
    """Immutable Workspace scope echoed by activity.list."""

    workspace_id: UUID
    workspace_revision: Int64
    locator: str

    @classmethod
    def from_schema(cls, scope: ForgeActivityScope) -> ForgeActivityScopeDto:
        """Convert the validated Activity scope to an immutable DTO.

        Args:
            scope: Validated Activity projection scope.
        Return:
            Immutable Activity scope DTO.
        """
        result = cls(
            workspace_id=scope.workspace_id,
            workspace_revision=scope.workspace_revision,
            locator=scope.locator,
        )
        return result

    def to_dict(self) -> ForgeActivityScopeDict:
        """Serialize the Activity scope echo.

        Args:
            None.
        Return:
            Typed Activity scope object.
        """
        result: ForgeActivityScopeDict = ForgeActivityScopeDict(
            workspace_id=self.workspace_id,
            workspace_revision=self.workspace_revision,
            locator=self.locator,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeActivityProjectionDto:
    """Immutable durable Activity projection and lease observation."""

    activity_id: UUID
    workspace_id: UUID
    state: ActivityStateEnum
    liveness: ActivityLivenessEnum
    revision: Int64
    created_at_ms: Int64
    updated_at_ms: Int64
    lease_owner_id: UUID | None
    lease_until_ms: Int64 | None
    lease_revision: Int64

    @classmethod
    def from_schema(cls, activity: ForgeActivityProjection) -> ForgeActivityProjectionDto:
        """Convert a validated Activity projection to its immutable DTO.

        Args:
            activity: Validated Forge Activity projection.
        Return:
            Immutable Activity projection DTO.
        """
        result = cls(
            activity_id=activity.activity_id,
            workspace_id=activity.workspace_id,
            state=ActivityStateEnum(activity.state),
            liveness=ActivityLivenessEnum(activity.liveness),
            revision=activity.revision,
            created_at_ms=activity.created_at_ms,
            updated_at_ms=activity.updated_at_ms,
            lease_owner_id=activity.lease_owner_id,
            lease_until_ms=activity.lease_until_ms,
            lease_revision=activity.lease_revision,
        )
        return result

    def to_dict(self) -> ForgeActivityProjectionDict:
        """Serialize Activity projection with explicit nullable lease fields.

        Args:
            None.
        Return:
            Typed Activity projection object.
        """
        result: ForgeActivityProjectionDict = ForgeActivityProjectionDict(
            activity_id=self.activity_id,
            workspace_id=self.workspace_id,
            state=self.state,
            liveness=self.liveness,
            revision=self.revision,
            created_at_ms=self.created_at_ms,
            updated_at_ms=self.updated_at_ms,
            lease_owner_id=self.lease_owner_id,
            lease_until_ms=self.lease_until_ms,
            lease_revision=self.lease_revision,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeActivityListResultDto:
    """Immutable result returned by activity.list."""

    scope: ForgeActivityScopeDto
    activities: tuple[ForgeActivityProjectionDto, ...]

    @classmethod
    def from_schema(cls, result_schema: ForgeActivityListResult) -> ForgeActivityListResultDto:
        """Convert a validated Activity result and its nested projections.

        Args:
            result_schema: Validated activity.list result payload.
        Return:
            Immutable Activity list result DTO.
        """
        scope = ForgeActivityScopeDto.from_schema(scope=result_schema.scope)
        activities = tuple(
            ForgeActivityProjectionDto.from_schema(activity=activity)
            for activity in result_schema.activities
        )
        result = cls(scope=scope, activities=activities)
        return result

    def to_dict(self) -> ForgeActivityListResultDict:
        """Serialize the typed activity.list result payload.

        Args:
            None.
        Return:
            Typed Activity list result.
        """
        result: ForgeActivityListResultDict = ForgeActivityListResultDict(
            scope=self.scope.to_dict(),
            activities=[activity.to_dict() for activity in self.activities],
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeDagNodeDto:
    """Immutable DAG node definition and readiness projection."""

    node_id: UUID
    ordinal: Int64
    title: str
    objective: str
    acceptance: tuple[str, ...]
    lifecycle: DagNodeLifecycleEnum
    lifecycle_reason: str | None
    status: DagNodeStatusEnum
    waiting_on: tuple[UUID, ...]
    revision: Int64
    evidence_count: UInt64
    created_at_ms: Int64
    updated_at_ms: Int64

    @classmethod
    def from_schema(cls, node: ForgeDagNode) -> ForgeDagNodeDto:
        """Convert a validated DAG node to its immutable DTO.

        Args:
            node: Validated Forge DAG node.
        Return:
            Immutable DAG node DTO.
        """
        result = cls(
            node_id=node.node_id,
            ordinal=node.ordinal,
            title=node.title,
            objective=node.objective,
            acceptance=tuple(node.acceptance),
            lifecycle=DagNodeLifecycleEnum(node.lifecycle),
            lifecycle_reason=node.lifecycle_reason,
            status=DagNodeStatusEnum(node.status),
            waiting_on=tuple(node.waiting_on),
            revision=node.revision,
            evidence_count=node.evidence_count,
            created_at_ms=node.created_at_ms,
            updated_at_ms=node.updated_at_ms,
        )
        return result

    def to_dict(self) -> ForgeDagNodeDict:
        """Serialize exact DAG node projection fields.

        Args:
            None.
        Return:
            Typed DAG node object.
        """
        result: ForgeDagNodeDict = ForgeDagNodeDict(
            node_id=self.node_id,
            ordinal=self.ordinal,
            title=self.title,
            objective=self.objective,
            acceptance=list(self.acceptance),
            lifecycle=self.lifecycle,
            lifecycle_reason=self.lifecycle_reason,
            status=self.status,
            waiting_on=list(self.waiting_on),
            revision=self.revision,
            evidence_count=self.evidence_count,
            created_at_ms=self.created_at_ms,
            updated_at_ms=self.updated_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeDagEdgeDto:
    """Immutable DAG dependency edge."""

    upstream: UUID
    downstream: UUID

    @classmethod
    def from_schema(cls, edge: ForgeDagEdge) -> ForgeDagEdgeDto:
        """Convert a validated DAG edge to its immutable DTO.

        Args:
            edge: Validated Forge DAG edge.
        Return:
            Immutable DAG edge DTO.
        """
        result = cls(upstream=edge.upstream, downstream=edge.downstream)
        return result

    def to_dict(self) -> ForgeDagEdgeDict:
        """Serialize the exact DAG edge fields.

        Args:
            None.
        Return:
            Typed DAG edge object.
        """
        result: ForgeDagEdgeDict = ForgeDagEdgeDict(
            upstream=self.upstream,
            downstream=self.downstream,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeDagLineageDto:
    """Immutable DAG node lineage edge."""

    prior_node_id: UUID
    successor_node_id: UUID
    kind: DagLineageKindEnum

    @classmethod
    def from_schema(cls, lineage: ForgeDagLineage) -> ForgeDagLineageDto:
        """Convert validated node lineage to its immutable DTO.

        Args:
            lineage: Validated Forge DAG lineage edge.
        Return:
            Immutable DAG lineage DTO.
        """
        result = cls(
            prior_node_id=lineage.prior_node_id,
            successor_node_id=lineage.successor_node_id,
            kind=DagLineageKindEnum(lineage.kind),
        )
        return result

    def to_dict(self) -> ForgeDagLineageDict:
        """Serialize exact DAG lineage fields.

        Args:
            None.
        Return:
            Typed DAG lineage object.
        """
        result: ForgeDagLineageDict = ForgeDagLineageDict(
            prior_node_id=self.prior_node_id,
            successor_node_id=self.successor_node_id,
            kind=self.kind,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeDagCurrentFoundResultDto:
    """Immutable found current DAG result."""

    goal_id: UUID
    revision_id: UUID
    base_goal_revision: Int64
    dag_revision: Int64
    parent_revision: Int64 | None
    created_at_ms: Int64
    head_revision: Int64
    head_updated_at_ms: Int64
    node_count: UInt64
    nodes: tuple[ForgeDagNodeDto, ...]
    edges: tuple[ForgeDagEdgeDto, ...]
    lineage: tuple[ForgeDagLineageDto, ...]

    @classmethod
    def from_schema(cls, dag: ForgeDagCurrentFoundResult) -> ForgeDagCurrentFoundResultDto:
        """Convert the validated found DAG result to an immutable DTO.

        Args:
            dag: Validated current DAG result.
        Return:
            Immutable found DAG result DTO.
        """
        result = cls(
            goal_id=dag.goal_id,
            revision_id=dag.revision_id,
            base_goal_revision=dag.base_goal_revision,
            dag_revision=dag.dag_revision,
            parent_revision=dag.parent_revision,
            created_at_ms=dag.created_at_ms,
            head_revision=dag.head_revision,
            head_updated_at_ms=dag.head_updated_at_ms,
            node_count=dag.node_count,
            nodes=tuple(ForgeDagNodeDto.from_schema(node=node) for node in dag.nodes),
            edges=tuple(ForgeDagEdgeDto.from_schema(edge=edge) for edge in dag.edges),
            lineage=tuple(ForgeDagLineageDto.from_schema(lineage=item) for item in dag.lineage),
        )
        return result

    def to_dict(self) -> ForgeDagCurrentFoundResultDict:
        """Serialize the exact found current DAG result.

        Args:
            None.
        Return:
            Typed found current DAG result.
        """
        result: ForgeDagCurrentFoundResultDict = ForgeDagCurrentFoundResultDict(
            found=True,
            goal_id=self.goal_id,
            revision_id=self.revision_id,
            base_goal_revision=self.base_goal_revision,
            dag_revision=self.dag_revision,
            parent_revision=self.parent_revision,
            created_at_ms=self.created_at_ms,
            head_revision=self.head_revision,
            head_updated_at_ms=self.head_updated_at_ms,
            node_count=self.node_count,
            nodes=[node.to_dict() for node in self.nodes],
            edges=[edge.to_dict() for edge in self.edges],
            lineage=[item.to_dict() for item in self.lineage],
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeDagCurrentMissingResultDto:
    """Immutable missing current DAG result."""

    def to_dict(self) -> ForgeDagCurrentMissingResultDict:
        """Serialize the Source result indicating no current DAG exists.

        Args:
            None.
        Return:
            Typed missing current DAG result.
        """
        result: ForgeDagCurrentMissingResultDict = ForgeDagCurrentMissingResultDict(found=False)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ForgeDagSettleResultDto:
    """Immutable DAG settlement receipt."""

    settlement_id: UUID
    goal_id: UUID
    dag_revision: Int64
    state: SettlementJournalStateEnum
    settled_at_ms: Int64
    terminal_sink_node_ids: tuple[UUID, ...]
    baseline_commit_oid: str
    candidate_commit_oid: str
    baseline_tree_blake3: str
    settled_tree_blake3: str
    settled_file_count: UInt64
    upserted_paths: tuple[str, ...]
    deleted_paths: tuple[str, ...]

    @classmethod
    def from_schema(cls, receipt: ForgeDagSettleResult) -> ForgeDagSettleResultDto:
        """Convert the validated DAG settlement receipt to its immutable DTO.

        Args:
            receipt: Validated Forge DAG settlement result.
        Return:
            Immutable DAG settlement receipt DTO.
        """
        result = cls(
            settlement_id=receipt.settlement_id,
            goal_id=receipt.goal_id,
            dag_revision=receipt.dag_revision,
            state=SettlementJournalStateEnum(receipt.state),
            settled_at_ms=receipt.settled_at_ms,
            terminal_sink_node_ids=tuple(receipt.terminal_sink_node_ids),
            baseline_commit_oid=receipt.baseline_commit_oid,
            candidate_commit_oid=receipt.candidate_commit_oid,
            baseline_tree_blake3=receipt.baseline_tree_blake3,
            settled_tree_blake3=receipt.settled_tree_blake3,
            settled_file_count=receipt.settled_file_count,
            upserted_paths=tuple(receipt.upserted_paths),
            deleted_paths=tuple(receipt.deleted_paths),
        )
        return result

    def to_dict(self) -> ForgeDagSettleResultDict:
        """Serialize the exact DAG settlement receipt fields.

        Args:
            None.
        Return:
            Typed DAG settlement result.
        """
        result: ForgeDagSettleResultDict = ForgeDagSettleResultDict(
            settlement_id=self.settlement_id,
            goal_id=self.goal_id,
            dag_revision=self.dag_revision,
            state=self.state,
            settled_at_ms=self.settled_at_ms,
            terminal_sink_node_ids=list(self.terminal_sink_node_ids),
            baseline_commit_oid=self.baseline_commit_oid,
            candidate_commit_oid=self.candidate_commit_oid,
            baseline_tree_blake3=self.baseline_tree_blake3,
            settled_tree_blake3=self.settled_tree_blake3,
            settled_file_count=self.settled_file_count,
            upserted_paths=list(self.upserted_paths),
            deleted_paths=list(self.deleted_paths),
        )
        return result
