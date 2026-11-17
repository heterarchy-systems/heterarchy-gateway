"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing import Literal, NotRequired
from uuid import UUID

from typing_extensions import TypedDict

from app.forge.application.inner_dto.types.forge_envelope_types import (
    ForgeSessionActorDict,
    ForgeWorkspaceScopeDict,
)
from app.shared.ingredient_element.forge.forge_enums import (
    SettlementJournalStateEnum,
    SwarmWorkspaceModeEnum,
)


class ForgeSwarmStandaloneTargetDict(TypedDict, total=True, closed=True):
    """Standalone target payload sent to Forge."""

    kind: Literal["standalone_swarm"]


class ForgeSwarmDagNodeHybridTargetDict(TypedDict, total=True, closed=True):
    """DAG node hybrid target payload sent to Forge."""

    kind: Literal["dag_node_hybrid"]
    goal_id: str
    dag_revision: int
    node_id: str


ForgeSwarmTargetDict = ForgeSwarmStandaloneTargetDict | ForgeSwarmDagNodeHybridTargetDict


class ForgeSwarmWorkspaceProvisionPayloadDict(TypedDict, total=True, closed=True):
    """Closed request body for `swarm.workspace_provision`."""

    scope: ForgeWorkspaceScopeDict
    actor: ForgeSessionActorDict
    swarm_run_id: str
    member_id: str
    mode: str
    target: ForgeSwarmTargetDict
    candidate_commit_oid: str | None
    observed_at_ms: int


class ForgeSwarmWorkspaceGetPayloadDict(TypedDict, total=True, closed=True):
    """Closed request body for `swarm.workspace_get`."""

    scope: ForgeWorkspaceScopeDict
    swarm_run_id: str
    member_id: str


class ForgeSwarmMemberCapturePayloadDict(TypedDict, total=True, closed=True):
    """Closed request body for `swarm.member_capture`."""

    scope: ForgeWorkspaceScopeDict
    actor: ForgeSessionActorDict
    swarm_run_id: str
    member_id: str
    captured_at_ms: int


class ForgeSwarmConvergenceCandidateDict(TypedDict, total=True, closed=True):
    """Convergence candidate serialized with Serde's omitted optional keys."""

    member_id: str
    expected_output_commit_oid: NotRequired[str]
    expected_diff_digest: NotRequired[str]


class ForgeSwarmConvergePayloadDict(TypedDict, total=True, closed=True):
    """Closed request body for `swarm.converge`."""

    scope: ForgeWorkspaceScopeDict
    actor: ForgeSessionActorDict
    swarm_run_id: str
    candidates: list[ForgeSwarmConvergenceCandidateDict]
    observed_at_ms: int


class ForgeSwarmSettlePayloadDict(TypedDict, total=True, closed=True):
    """Closed request body for `swarm.settle`."""

    scope: ForgeWorkspaceScopeDict
    activity_id: str | None
    actor: ForgeSessionActorDict
    coordinator_agent_id: str
    swarm_run_id: str
    settlement_id: str
    converged_commit_oid: str
    expected_diff_digest: str | None
    settled_at_ms: int


class ForgeSwarmMaterializeHybridPayloadDict(TypedDict, total=True, closed=True):
    """Closed request body for `swarm.materialize_hybrid`."""

    scope: ForgeWorkspaceScopeDict
    activity_id: str
    actor: ForgeSessionActorDict
    swarm_run_id: str
    settlement_id: str
    goal_id: str
    expected_goal_revision: int
    expected_dag_revision: int
    node_id: str
    converged_commit_oid: str
    expected_diff_digest: str | None
    settled_at_ms: int


class ForgeSwarmSettlementGetPayloadDict(TypedDict, total=True, closed=True):
    """Closed request body for `swarm.settlement_get`."""

    scope: ForgeWorkspaceScopeDict
    swarm_run_id: str


class ForgeSwarmPurgePayloadDict(TypedDict, total=True, closed=True):
    """Closed request body for `swarm.purge`."""

    scope: ForgeWorkspaceScopeDict
    actor: ForgeSessionActorDict
    swarm_run_id: str


ForgeSwarmCommandPayloadDict = (
    ForgeSwarmWorkspaceProvisionPayloadDict
    | ForgeSwarmWorkspaceGetPayloadDict
    | ForgeSwarmMemberCapturePayloadDict
    | ForgeSwarmConvergePayloadDict
    | ForgeSwarmSettlePayloadDict
    | ForgeSwarmMaterializeHybridPayloadDict
    | ForgeSwarmSettlementGetPayloadDict
    | ForgeSwarmPurgePayloadDict
)


class ForgeSwarmMemberOutputResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of a captured member output."""

    swarm_run_id: UUID
    member_id: UUID
    mode: SwarmWorkspaceModeEnum
    input_commit_oid: str
    output_commit_oid: str
    initial_tree_blake3: str
    final_tree_blake3: str
    final_file_count: int
    changed_paths: list[str]
    diff_digest: str
    captured_at_ms: int


class ForgeSwarmWorkspaceReceiptResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of a provisioned member workspace."""

    swarm_run_id: UUID
    member_id: UUID
    mode: SwarmWorkspaceModeEnum
    target: ForgeSwarmTargetDict
    worktree_path: str
    provisioned_at_ms: int
    initial_tree_blake3: str
    initial_file_count: int
    input_commit_oid: str
    completed: ForgeSwarmMemberOutputResponseDict | None


class ForgeSwarmWorkspaceGetResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of a Swarm workspace lookup."""

    workspace_id: UUID
    swarm_run_id: UUID
    member_id: UUID
    found: bool
    receipt: ForgeSwarmWorkspaceReceiptResponseDict | None


class ForgeSwarmConvergedResponseDict(TypedDict, total=True, closed=True):
    """Tagged converged result serialized from Forge."""

    status: Literal["converged"]
    swarm_run_id: UUID
    converged_commit_oid: str
    converged_tree_blake3: str
    converged_diff_digest: str
    changed_files: list[str]


class ForgeSwarmConflictResponseDict(TypedDict, total=True, closed=True):
    """Tagged conflict result serialized from Forge."""

    status: Literal["conflict"]
    swarm_run_id: UUID
    conflicting_member_id: UUID
    details: list[str]


ForgeSwarmConvergenceResponseDict = ForgeSwarmConvergedResponseDict | ForgeSwarmConflictResponseDict


class ForgeSwarmSettlementReceiptResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of a Swarm settlement receipt."""

    settlement_id: str
    swarm_run_id: UUID
    target: ForgeSwarmTargetDict
    state: SettlementJournalStateEnum
    settled_at_ms: int
    baseline_commit_oid: str
    converged_commit_oid: str
    baseline_tree_blake3: str
    settled_tree_blake3: str
    converged_diff_digest: str
    settled_file_count: int
    upserted_paths: list[str]
    deleted_paths: list[str]


class ForgeSwarmSettleResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of a Swarm settle operation."""

    receipt: ForgeSwarmSettlementReceiptResponseDict
    outbox_sequence: int | None


class ForgeSwarmSettledEffectFactResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of one Swarm settled effect fact."""

    kind: Literal["swarm_settled"]
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


class ForgeSwarmSettledOutboxEntryResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of a Swarm settlement outbox row."""

    sequence: int
    migration_id: UUID
    destination_id: UUID
    workspace_id: UUID
    fact: ForgeSwarmSettledEffectFactResponseDict


class ForgeSwarmSettlementGetResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of a Swarm settlement lookup."""

    workspace_id: UUID
    swarm_run_id: UUID
    receipt: ForgeSwarmSettlementReceiptResponseDict | None
    outbox_entry: ForgeSwarmSettledOutboxEntryResponseDict | None


class ForgeSwarmPurgeResponseDict(TypedDict, total=True, closed=True):
    """Validated Gateway view of a Swarm purge result."""

    workspace_id: UUID
    swarm_run_id: UUID
    purged: bool
