"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing import Literal
from uuid import UUID

from typing_extensions import TypedDict

from app.forge.application.inner_dto.types.forge_envelope_types import (
    ForgeSessionActorDict,
    ForgeWorkspaceScopeDict,
)
from app.forge.schema.types.forge_types import Int64, UInt32, UInt64
from app.shared.ingredient_element.forge.forge_enums import (
    ActivityLivenessEnum,
    ActivityStateEnum,
    DagLineageKindEnum,
    DagNodeLifecycleEnum,
    DagNodeStatusEnum,
    LocationStateEnum,
    SettlementJournalStateEnum,
)


class ForgeLocationListPayloadDict(TypedDict, total=True, closed=True):
    """Empty location.list Source payload."""


class ForgeWorkspaceListPayloadDict(TypedDict, total=True, closed=True):
    """Source payload for listing Workspaces under one Location revision."""

    location_id: str
    expected_revision: Int64


class ForgeActivityListPayloadDict(TypedDict, total=True, closed=True):
    """Source payload for listing bounded Activity projections."""

    locator: str
    workspace_id: str
    workspace_revision: Int64
    limit: UInt32


class ForgeDagReadCurrentPayloadDict(TypedDict, total=True, closed=True):
    """Source payload for reading the current DAG revision."""

    scope: ForgeWorkspaceScopeDict
    goal_id: str


class ForgeDagSettlePayloadDict(TypedDict, total=True, closed=True):
    """Source payload for settling a DAG revision."""

    scope: ForgeWorkspaceScopeDict
    activity_id: str
    actor: ForgeSessionActorDict
    goal_id: str
    expected_goal_revision: Int64
    expected_dag_revision: Int64
    settlement_id: str
    observed_at_ms: Int64


class ForgeLocationEntryDict(TypedDict, total=True, closed=True):
    """One exact registered Location result."""

    location_id: UUID
    display_name: str
    revision: Int64
    state: LocationStateEnum


class ForgeLocationListResultDict(TypedDict, total=True, closed=True):
    """Location list result envelope payload."""

    entries: list[ForgeLocationEntryDict]


class ForgeWorkspaceEntryDict(TypedDict, total=True, closed=True):
    """One exact Workspace list result."""

    locator: str
    display_name: str
    workspace_id: UUID
    workspace_revision: Int64


class ForgeWorkspaceListResultDict(TypedDict, total=True, closed=True):
    """Workspace list result payload."""

    entries: list[ForgeWorkspaceEntryDict]


class ForgeActivityScopeDict(TypedDict, total=True, closed=True):
    """Workspace scope echoed by an Activity projection query."""

    workspace_id: UUID
    workspace_revision: Int64
    locator: str


class ForgeActivityProjectionDict(TypedDict, total=True, closed=True):
    """One durable Activity projection and its lease state."""

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


class ForgeActivityListResultDict(TypedDict, total=True, closed=True):
    """Activity projection result payload."""

    scope: ForgeActivityScopeDict
    activities: list[ForgeActivityProjectionDict]


class ForgeDagNodeDict(TypedDict, total=True, closed=True):
    """Current DAG node definition and status projection."""

    node_id: UUID
    ordinal: Int64
    title: str
    objective: str
    acceptance: list[str]
    lifecycle: DagNodeLifecycleEnum
    lifecycle_reason: str | None
    status: DagNodeStatusEnum
    waiting_on: list[UUID]
    revision: Int64
    evidence_count: UInt64
    created_at_ms: Int64
    updated_at_ms: Int64


class ForgeDagEdgeDict(TypedDict, total=True, closed=True):
    """Directed dependency edge in a DAG revision."""

    upstream: UUID
    downstream: UUID


class ForgeDagLineageDict(TypedDict, total=True, closed=True):
    """Node succession relation in a DAG revision."""

    prior_node_id: UUID
    successor_node_id: UUID
    kind: DagLineageKindEnum


class ForgeDagCurrentFoundResultDict(TypedDict, total=True, closed=True):
    """Found current DAG result."""

    found: Literal[True]
    goal_id: UUID
    revision_id: UUID
    base_goal_revision: Int64
    dag_revision: Int64
    parent_revision: Int64 | None
    created_at_ms: Int64
    head_revision: Int64
    head_updated_at_ms: Int64
    node_count: UInt64
    nodes: list[ForgeDagNodeDict]
    edges: list[ForgeDagEdgeDict]
    lineage: list[ForgeDagLineageDict]


class ForgeDagCurrentMissingResultDict(TypedDict, total=True, closed=True):
    """Missing current DAG result."""

    found: Literal[False]


type ForgeDagCurrentResultDict = ForgeDagCurrentFoundResultDict | ForgeDagCurrentMissingResultDict


class ForgeDagSettleResultDict(TypedDict, total=True, closed=True):
    """Durable DAG settlement receipt."""

    settlement_id: UUID
    goal_id: UUID
    dag_revision: Int64
    state: SettlementJournalStateEnum
    settled_at_ms: Int64
    terminal_sink_node_ids: list[UUID]
    baseline_commit_oid: str
    candidate_commit_oid: str
    baseline_tree_blake3: str
    settled_tree_blake3: str
    settled_file_count: UInt64
    upserted_paths: list[str]
    deleted_paths: list[str]
