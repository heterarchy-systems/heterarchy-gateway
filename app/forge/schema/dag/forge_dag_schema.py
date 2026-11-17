"""Strict forge dag schema contracts."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeCommandRequest,
    ForgeSessionActor,
    ForgeSuccessEnvelope,
    ForgeWorkspaceScope,
)
from app.forge.schema.types.forge_types import (
    DagLineageKind,
    DagNodeLifecycle,
    DagNodeStatus,
    ForgeUUID,
    Int64,
    SettlementJournalState,
    UInt64,
)
from app.shared.base_schema import StrictRootSchemaModel, StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum
from app.shared.types.base_types import JsonValue


class ForgeDagReadCurrentPayload(StrictSchemaModel):
    """Strict payload for the current stored DAG revision query."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    goal_id: Annotated[ForgeUUID, Field(description="Goal identity owning the DAG.")]


class ForgeDagNode(StrictSchemaModel):
    """Current DAG node definition and readiness projection."""

    node_id: Annotated[ForgeUUID, Field(description="DAG node identity.")]
    ordinal: Annotated[Int64, Field(description="Stable node order in the DAG revision.")]
    title: Annotated[str, Field(description="Node title.")]
    objective: Annotated[str, Field(description="Node objective.")]
    acceptance: Annotated[list[str], Field(description="Node acceptance criteria.")]
    lifecycle: Annotated[DagNodeLifecycle, Field(description="Durable node lifecycle.")]
    lifecycle_reason: Annotated[
        str | None,
        Field(description="Durable reason when lifecycle carries one, otherwise null."),
    ]
    status: Annotated[DagNodeStatus, Field(description="Projected node readiness.")]
    waiting_on: Annotated[
        list[ForgeUUID], Field(description="Upstream node identities still pending.")
    ]
    revision: Annotated[Int64, Field(description="Current node revision.")]
    evidence_count: Annotated[UInt64, Field(description="Evidence records attached to the node.")]
    created_at_ms: Annotated[Int64, Field(description="Node creation time in Unix milliseconds.")]
    updated_at_ms: Annotated[Int64, Field(description="Node update time in Unix milliseconds.")]


class ForgeDagEdge(StrictSchemaModel):
    """Directed dependency edge in the current DAG revision."""

    upstream: Annotated[ForgeUUID, Field(description="Upstream node identity.")]
    downstream: Annotated[ForgeUUID, Field(description="Downstream node identity.")]


class ForgeDagLineage(StrictSchemaModel):
    """Declared node succession relation in the current DAG revision."""

    prior_node_id: Annotated[ForgeUUID, Field(description="Predecessor node identity.")]
    successor_node_id: Annotated[ForgeUUID, Field(description="Successor node identity.")]
    kind: Annotated[DagLineageKind, Field(description="Node succession operation.")]


class _ForgeDagCurrentResultBase(StrictSchemaModel):
    """Require a real JSON boolean before the tagged found discriminator."""

    @model_validator(mode="before")
    @classmethod
    def validate_found_boolean(cls, value: JsonValue) -> JsonValue:
        """Reject integer aliases for the Source found boolean.

        Args:
            value: Unvalidated JSON result input.
        Return:
            Unmodified input with a verified boolean discriminator.
        """
        if isinstance(value, dict) and "found" in value:
            if type(value["found"]) is not bool:
                raise ValueError("DAG found discriminator must be a boolean")
        result = value
        return result


class ForgeDagCurrentFoundResult(_ForgeDagCurrentResultBase):
    """Current DAG revision when Forge has a stored revision."""

    found: Annotated[Literal[True], Field(description="Forge found a stored DAG revision.")]
    goal_id: Annotated[ForgeUUID, Field(description="Goal identity owning this DAG.")]
    revision_id: Annotated[ForgeUUID, Field(description="Stored DAG revision identity.")]
    base_goal_revision: Annotated[Int64, Field(description="Goal revision used as the DAG base.")]
    dag_revision: Annotated[Int64, Field(description="Current DAG revision number.")]
    parent_revision: Annotated[
        Int64 | None,
        Field(description="Parent DAG revision, explicitly null for the initial revision."),
    ]
    created_at_ms: Annotated[Int64, Field(description="DAG creation time in Unix milliseconds.")]
    head_revision: Annotated[Int64, Field(description="Current DAG head revision.")]
    head_updated_at_ms: Annotated[
        Int64, Field(description="DAG head update time in Unix milliseconds.")
    ]
    node_count: Annotated[UInt64, Field(description="Number of nodes in the current DAG.")]
    nodes: Annotated[list[ForgeDagNode], Field(description="Current DAG nodes.")]
    edges: Annotated[list[ForgeDagEdge], Field(description="Current DAG dependency edges.")]
    lineage: Annotated[list[ForgeDagLineage], Field(description="Current DAG node lineage.")]


class ForgeDagCurrentMissingResult(_ForgeDagCurrentResultBase):
    """Current DAG query result when Forge has no stored revision."""

    found: Annotated[Literal[False], Field(description="Forge has no stored DAG revision.")]


type ForgeDagCurrentResultUnion = Annotated[
    ForgeDagCurrentFoundResult | ForgeDagCurrentMissingResult,
    Field(discriminator="found", description="Stored DAG revision presence result."),
]


class ForgeDagCurrentResult(StrictRootSchemaModel[ForgeDagCurrentResultUnion]):
    """Tagged found-or-missing current DAG result."""


class ForgeDagReadCurrentRequest(ForgeCommandRequest[ForgeDagReadCurrentPayload]):
    """Versioned dag.read_current command request."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.DAG_READ_CURRENT],
        Field(description="This route executes dag.read_current."),
    ]


class ForgeDagReadCurrentResponse(ForgeSuccessEnvelope[ForgeDagCurrentResult]):
    """Successful dag.read_current response envelope."""


class ForgeDagSettlePayload(StrictSchemaModel):
    """Strict payload for a revision-checked DAG settlement command."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    activity_id: Annotated[ForgeUUID, Field(description="Activity authorizing DAG settlement.")]
    actor: Annotated[ForgeSessionActor, Field(description="Caller session and principal.")]
    goal_id: Annotated[ForgeUUID, Field(description="Goal identity to settle.")]
    expected_goal_revision: Annotated[Int64, Field(description="Expected current Goal revision.")]
    expected_dag_revision: Annotated[Int64, Field(description="Expected current DAG revision.")]
    settlement_id: Annotated[ForgeUUID, Field(description="Caller-supplied settlement identity.")]
    observed_at_ms: Annotated[
        Int64, Field(description="Caller observation time in Unix milliseconds.")
    ]


class ForgeDagSettleResult(StrictSchemaModel):
    """Durable settlement receipt for one DAG revision."""

    settlement_id: Annotated[ForgeUUID, Field(description="Committed settlement identity.")]
    goal_id: Annotated[ForgeUUID, Field(description="Settled Goal identity.")]
    dag_revision: Annotated[Int64, Field(description="Settled DAG revision number.")]
    state: Annotated[
        SettlementJournalState,
        Field(description="Durable settlement journal state."),
    ]
    settled_at_ms: Annotated[Int64, Field(description="Settlement time in Unix milliseconds.")]
    terminal_sink_node_ids: Annotated[
        list[ForgeUUID],
        Field(description="Terminal DAG nodes included in the settlement."),
    ]
    baseline_commit_oid: Annotated[str, Field(description="Pinned baseline Git commit.")]
    candidate_commit_oid: Annotated[str, Field(description="Candidate Git commit being settled.")]
    baseline_tree_blake3: Annotated[str, Field(description="Pinned baseline tree digest.")]
    settled_tree_blake3: Annotated[str, Field(description="Settled tree digest.")]
    settled_file_count: Annotated[UInt64, Field(description="Number of files in the settled tree.")]
    upserted_paths: Annotated[
        list[str], Field(description="Paths created or updated by settlement.")
    ]
    deleted_paths: Annotated[list[str], Field(description="Paths removed by settlement.")]


class ForgeDagSettleRequest(ForgeCommandRequest[ForgeDagSettlePayload]):
    """Versioned dag.settle command request."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.DAG_SETTLE],
        Field(description="This route executes dag.settle."),
    ]


class ForgeDagSettleResponse(ForgeSuccessEnvelope[ForgeDagSettleResult]):
    """Successful dag.settle response envelope."""
