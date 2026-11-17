"""Strict forge swarm convergence schema contracts."""

from typing import Annotated, Literal

from pydantic import Field

from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeCommandRequest,
    ForgeSessionActor,
    ForgeSuccessEnvelope,
    ForgeWorkspaceScope,
)
from app.forge.schema.types.forge_types import ForgeUUID
from app.shared.base_schema import StrictRootSchemaModel, StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import (
    ForgeCommandOpEnum,
    SwarmConvergenceStatusEnum,
)


class ForgeSwarmConvergenceCandidate(StrictSchemaModel):
    """One expected member output considered during convergence."""

    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]
    expected_output_commit_oid: Annotated[
        str | None,
        Field(description="Expected member output commit when the caller has one."),
    ]
    expected_diff_digest: Annotated[
        str | None,
        Field(description="Expected hexadecimal member diff digest when supplied."),
    ]


class ForgeSwarmConvergeRequest(StrictSchemaModel):
    """Converge captured outputs for one Swarm run."""

    scope: Annotated[ForgeWorkspaceScope, Field(description="Revision-pinned Workspace scope.")]
    actor: Annotated[ForgeSessionActor, Field(description="Authenticated Forge session actor.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    candidates: Annotated[
        list[ForgeSwarmConvergenceCandidate],
        Field(description="Member outputs to compare, capped at 64 entries.", max_length=64),
    ]
    observed_at_ms: Annotated[
        int,
        Field(
            description="Observation time in Unix milliseconds.",
            ge=-9_223_372_036_854_775_808,
            le=9_223_372_036_854_775_807,
        ),
    ]


class ForgeSwarmConvergedResult(StrictSchemaModel):
    """Successful convergence result."""

    status: Annotated[
        Literal[SwarmConvergenceStatusEnum.CONVERGED],
        Field(description="Converged result discriminator."),
    ]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    converged_commit_oid: Annotated[str, Field(description="Converged commit identity.")]
    converged_tree_blake3: Annotated[str, Field(description="Converged tree digest.")]
    converged_diff_digest: Annotated[str, Field(description="Converged diff digest.")]
    changed_files: Annotated[list[str], Field(description="Paths changed by convergence.")]


class ForgeSwarmConflictResult(StrictSchemaModel):
    """Conflict result produced by a valid convergence operation."""

    status: Annotated[
        Literal[SwarmConvergenceStatusEnum.CONFLICT],
        Field(description="Conflicting result discriminator."),
    ]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    conflicting_member_id: Annotated[ForgeUUID, Field(description="Member whose output conflicts.")]
    details: Annotated[list[str], Field(description="Source conflict details.")]


ForgeSwarmConvergenceResult = Annotated[
    ForgeSwarmConvergedResult | ForgeSwarmConflictResult,
    Field(description="Tagged convergence success or conflict result."),
]


class ForgeSwarmConvergeResult(StrictRootSchemaModel[ForgeSwarmConvergenceResult]):
    """Response for convergence, whose domain conflict is a successful result."""


class ForgeSwarmConvergeResponse(ForgeSuccessEnvelope[ForgeSwarmConvergeResult]):
    """Successful envelope for a tagged convergence result."""


class ForgeSwarmConvergeCommandRequest(ForgeCommandRequest[ForgeSwarmConvergeRequest]):
    """Versioned convergence request with its route operation fixed."""

    op: Annotated[
        Literal[ForgeCommandOpEnum.SWARM_CONVERGE],
        Field(description="Forge operation selected by this route."),
    ]
