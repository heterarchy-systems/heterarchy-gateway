"""Strict forge swarm settlement schema contracts."""

from typing import Annotated, Literal

from pydantic import Field

from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeCommandRequest,
    ForgeSessionActor,
    ForgeSuccessEnvelope,
    ForgeWorkspaceScope,
)
from app.forge.schema.swarm.identity.forge_swarm_identity_schema import (
    ForgeSwarmTarget,
)
from app.forge.schema.types.forge_types import ForgeUUID, SettlementJournalState
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import (
    ForgeCommandOpEnum,
)


class ForgeSwarmSettlementReceiptResult(StrictSchemaModel):
    """Durable receipt for a committed Swarm settlement."""

    settlement_id: Annotated[str, Field(description="Settlement identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    target: Annotated[ForgeSwarmTarget, Field(description="Settlement target.")]
    state: Annotated[SettlementJournalState, Field(description="Settlement journal state.")]
    settled_at_ms: Annotated[
        int,
        Field(
            description="Settlement time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]
    baseline_commit_oid: Annotated[str, Field(description="Baseline commit identity.")]
    converged_commit_oid: Annotated[str, Field(description="Converged commit identity.")]
    baseline_tree_blake3: Annotated[str, Field(description="Baseline tree digest.")]
    settled_tree_blake3: Annotated[str, Field(description="Settled tree digest.")]
    converged_diff_digest: Annotated[str, Field(description="Converged diff digest.")]
    settled_file_count: Annotated[
        int,
        Field(description="Number of settled files.", ge=0, le=18_446_744_073_709_551_615),
    ]
    upserted_paths: Annotated[list[str], Field(description="Paths written by settlement.")]
    deleted_paths: Annotated[list[str], Field(description="Paths deleted by settlement.")]


class ForgeSwarmSettledEffectFactResult(StrictSchemaModel):
    """Kind-six Swarm settled effect fact carried by an outbox entry."""

    kind: Annotated[Literal["swarm_settled"], Field(description="Effect fact kind discriminator.")]
    settlement_id: Annotated[ForgeUUID, Field(description="Settlement identity.")]
    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    activity_id: Annotated[
        ForgeUUID | None, Field(description="Associated Activity identity when present.")
    ]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    settled_file_count: Annotated[
        int,
        Field(description="Number of settled files.", ge=0, le=18_446_744_073_709_551_615),
    ]
    settled_tree_digest: Annotated[str, Field(description="Hexadecimal settled tree digest.")]
    converged_diff_digest: Annotated[str, Field(description="Hexadecimal converged diff digest.")]
    coordinator_agent_id: Annotated[ForgeUUID, Field(description="Coordinator Agent identity.")]
    coordinator_session_id: Annotated[
        ForgeUUID | None,
        Field(description="Coordinator Session identity when available."),
    ]
    settled_at_ms: Annotated[
        int,
        Field(
            description="Settlement time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]


class ForgeSwarmSettledOutboxEntryResult(StrictSchemaModel):
    """Effect fact outbox row created for a Swarm settlement."""

    sequence: Annotated[
        int, Field(description="Monotonic outbox sequence.", ge=0, le=18_446_744_073_709_551_615)
    ]
    migration_id: Annotated[ForgeUUID, Field(description="Migration identity.")]
    destination_id: Annotated[ForgeUUID, Field(description="Destination identity.")]
    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    fact: Annotated[
        ForgeSwarmSettledEffectFactResult,
        Field(description="Typed Swarm settled effect fact."),
    ]


class ForgeSwarmSettleRequest(StrictSchemaModel):
    """Settle one converged Swarm run."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    activity_id: Annotated[
        ForgeUUID | None, Field(description="Activity identity when settlement is attributed.")
    ]
    actor: Annotated[ForgeSessionActor, Field(description="Authenticated Forge session actor.")]
    coordinator_agent_id: Annotated[ForgeUUID, Field(description="Coordinator Agent identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    settlement_id: Annotated[ForgeUUID, Field(description="Stable settlement request identity.")]
    converged_commit_oid: Annotated[str, Field(description="Converged commit identity.")]
    expected_diff_digest: Annotated[
        str | None, Field(description="Expected hexadecimal diff digest.")
    ]
    settled_at_ms: Annotated[
        int,
        Field(
            description="Settlement time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]


class ForgeSwarmSettleResult(StrictSchemaModel):
    """Settlement receipt and optional durable outbox sequence."""

    receipt: Annotated[
        ForgeSwarmSettlementReceiptResult, Field(description="Committed settlement receipt.")
    ]
    outbox_sequence: Annotated[
        int | None,
        Field(
            description="Outbox sequence, omitted by Forge when no entry was emitted.",
            ge=0,
            le=18_446_744_073_709_551_615,
        ),
    ]


class ForgeSwarmMaterializeHybridRequest(StrictSchemaModel):
    """Materialize a Swarm settlement into one fenced DAG node."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    activity_id: Annotated[ForgeUUID, Field(description="Activity identity owning the DAG effect.")]
    actor: Annotated[ForgeSessionActor, Field(description="Authenticated Forge session actor.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    settlement_id: Annotated[ForgeUUID, Field(description="Stable settlement request identity.")]
    goal_id: Annotated[ForgeUUID, Field(description="Goal identity receiving the output.")]
    expected_goal_revision: Annotated[
        int,
        Field(description="Expected Goal revision.", ge=0, le=9_223_372_036_854_775_807),
    ]
    expected_dag_revision: Annotated[
        int,
        Field(description="Expected DAG revision.", ge=0, le=9_223_372_036_854_775_807),
    ]
    node_id: Annotated[ForgeUUID, Field(description="DAG node receiving the output.")]
    converged_commit_oid: Annotated[str, Field(description="Converged commit identity.")]
    expected_diff_digest: Annotated[
        str | None, Field(description="Expected hexadecimal diff digest.")
    ]
    settled_at_ms: Annotated[
        int,
        Field(
            description="Settlement time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]


class ForgeSwarmMaterializeHybridResult(ForgeSwarmSettlementReceiptResult):
    """Response for materializing a settlement into a DAG node."""


class ForgeSwarmSettlementGetRequest(StrictSchemaModel):
    """Read the durable Swarm settlement and outbox projection."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]


class ForgeSwarmSettlementGetResult(StrictSchemaModel):
    """Settlement and outbox lookup with source-presence normalization."""

    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    receipt: Annotated[
        ForgeSwarmSettlementReceiptResult | None,
        Field(description="Settlement receipt, omitted by Forge when absent."),
    ]
    outbox_entry: Annotated[
        ForgeSwarmSettledOutboxEntryResult | None,
        Field(description="Outbox entry, omitted by Forge when absent."),
    ]


class ForgeSwarmSettleResponse(ForgeSuccessEnvelope[ForgeSwarmSettleResult]):
    """Successful envelope for settling one Swarm run."""


class ForgeSwarmMaterializeHybridResponse(ForgeSuccessEnvelope[ForgeSwarmMaterializeHybridResult]):
    """Successful envelope for hybrid DAG materialization."""


class ForgeSwarmSettlementGetResponse(ForgeSuccessEnvelope[ForgeSwarmSettlementGetResult]):
    """Successful envelope for reading Swarm settlement state."""


class ForgeSwarmSettleCommandRequest(ForgeCommandRequest[ForgeSwarmSettleRequest]):
    """Versioned settlement request with its route operation fixed."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.SWARM_SETTLE],
        Field(description="Forge operation selected by this route."),
    ]


class ForgeSwarmMaterializeHybridCommandRequest(
    ForgeCommandRequest[ForgeSwarmMaterializeHybridRequest]
):
    """Versioned hybrid materialization request with route operation fixed."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.SWARM_MATERIALIZE_HYBRID],
        Field(description="Forge operation selected by this route."),
    ]


class ForgeSwarmSettlementGetCommandRequest(ForgeCommandRequest[ForgeSwarmSettlementGetRequest]):
    """Versioned settlement lookup request with its route operation fixed."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.SWARM_SETTLEMENT_GET],
        Field(description="Forge operation selected by this route."),
    ]
