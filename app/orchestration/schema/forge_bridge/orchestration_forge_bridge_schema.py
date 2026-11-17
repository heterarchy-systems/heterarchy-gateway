"""Strict request and response contracts for East-West bridge calls."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from app.orchestration.application.inner_dto.forge_bridge_inner_dto import (
    ForgeConvergeSwarmCommandDto,
    ForgeSettleSwarmCommandDto,
    ForgeSettleSwarmOutboxOptionsDto,
    SyncAutonomyOutboxCommandDto,
)
from app.orchestration.schema.swarm.orchestration_swarm_state_schema import (
    SwarmConvergenceGateSchema,
    SwarmRunSchema,
)
from app.orchestration.schema.types.orchestration_types import Int64, UInt32, UInt64
from app.orchestration.schema.types.swarm_types import NonNilSwarmUUID, SwarmUUID
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.orchestration.forge_bridge_enums import (
    ForgeBridgeFieldEnum,
)


class ForgeConvergeSwarmRequest(StrictSchemaModel):
    """Request Forge candidate convergence through Orchestration."""

    request_id: Annotated[
        NonNilSwarmUUID,
        Field(alias=ForgeBridgeFieldEnum.REQUEST_ID.value, description="Stable convergence UUID."),
    ]
    session_id: Annotated[
        NonNilSwarmUUID,
        Field(alias=ForgeBridgeFieldEnum.SESSION_ID.value, description="Forge session UUID."),
    ]
    candidate_member_ids: Annotated[
        list[NonNilSwarmUUID],
        Field(
            alias=ForgeBridgeFieldEnum.CANDIDATE_MEMBER_IDS.value,
            description="Explicit candidate member IDs, or an empty list for source selection.",
        ),
    ]
    stage_candidate_only: Annotated[
        bool,
        Field(
            alias=ForgeBridgeFieldEnum.STAGE_CANDIDATE_ONLY.value,
            description="Stage CandidateReady without attempting immediate automatic settlement.",
        ),
    ]

    def to_inner_dto(self) -> ForgeConvergeSwarmCommandDto:
        """Convert the strict request to its immutable command DTO.

        Args:
            None.
        Return:
            Immutable Forge converge command.
        """
        result = ForgeConvergeSwarmCommandDto(
            request_id=self.request_id,
            session_id=self.session_id,
            candidate_member_ids=tuple(self.candidate_member_ids),
            stage_candidate_only=self.stage_candidate_only,
        )
        return result


class ForgeConvergeSwarmResponse(StrictSchemaModel):
    """Forge convergence projection and optional verified acceptance gate."""

    run: Annotated[SwarmRunSchema, Field(description="Canonical converged Swarm run.")]
    changed_files: Annotated[
        list[str],
        Field(alias=ForgeBridgeFieldEnum.CHANGED_FILES.value, description="Changed paths."),
    ]
    gate: Annotated[
        SwarmConvergenceGateSchema | None,
        Field(alias=ForgeBridgeFieldEnum.GATE.value, description="Verified gate, or null."),
    ]


class ForgeSettleSwarmRequest(StrictSchemaModel):
    """Request cross-backend Forge settlement through Orchestration."""

    request_id: Annotated[
        NonNilSwarmUUID,
        Field(alias=ForgeBridgeFieldEnum.REQUEST_ID.value, description="Stable settlement UUID."),
    ]
    session_id: Annotated[
        NonNilSwarmUUID,
        Field(alias=ForgeBridgeFieldEnum.SESSION_ID.value, description="Forge session UUID."),
    ]
    activity_id: Annotated[
        NonNilSwarmUUID | None,
        Field(alias=ForgeBridgeFieldEnum.ACTIVITY_ID.value, description="Activity UUID, or null."),
    ]
    coordinator_agent_id: Annotated[
        NonNilSwarmUUID,
        Field(
            alias=ForgeBridgeFieldEnum.COORDINATOR_AGENT_ID.value,
            description="Coordinator agent UUID.",
        ),
    ]
    outbox_migration_id: Annotated[
        NonNilSwarmUUID | None,
        Field(
            alias=ForgeBridgeFieldEnum.OUTBOX_MIGRATION_ID.value,
            description="Outbox migration UUID, or null.",
        ),
    ]
    outbox_after_sequence: Annotated[
        UInt64 | None,
        Field(
            alias=ForgeBridgeFieldEnum.OUTBOX_AFTER_SEQUENCE.value,
            description="Exclusive outbox cursor, or null for the source origin.",
        ),
    ]
    purge_ephemeral: Annotated[
        bool,
        Field(
            alias=ForgeBridgeFieldEnum.PURGE_EPHEMERAL.value,
            description="Whether source may purge ephemeral Swarm worktrees.",
        ),
    ]

    def to_inner_dto(self) -> ForgeSettleSwarmCommandDto:
        """Convert the strict request to its immutable settlement DTO.

        Args:
            None.
        Return:
            Immutable Forge settlement command.
        """
        result = ForgeSettleSwarmCommandDto(
            request_id=self.request_id,
            session_id=self.session_id,
            activity_id=self.activity_id,
            coordinator_agent_id=self.coordinator_agent_id,
            outbox_options=ForgeSettleSwarmOutboxOptionsDto(
                migration_id=self.outbox_migration_id,
                after_sequence=self.outbox_after_sequence,
            ),
            purge_ephemeral=self.purge_ephemeral,
        )
        return result


class SyncAutonomyOutboxRequest(StrictSchemaModel):
    """Read one bounded Forge outbox page and reconcile its facts."""

    migration_id: Annotated[
        NonNilSwarmUUID,
        Field(alias=ForgeBridgeFieldEnum.MIGRATION_ID.value, description="Migration UUID."),
    ]
    after_sequence: Annotated[
        UInt64,
        Field(
            alias=ForgeBridgeFieldEnum.AFTER_SEQUENCE.value,
            description="Exclusive sequence cursor.",
        ),
    ]
    limit: Annotated[
        UInt32 | None,
        Field(
            alias=ForgeBridgeFieldEnum.LIMIT.value,
            description="Page size from 1 to 64, or null.",
            ge=1,
            le=64,
        ),
    ]

    def to_inner_dto(self) -> SyncAutonomyOutboxCommandDto:
        """Convert the strict request to its immutable sync cursor DTO.

        Args:
            None.
        Return:
            Immutable autonomy outbox sync command.
        """
        result = SyncAutonomyOutboxCommandDto(
            migration_id=self.migration_id,
            after_sequence=self.after_sequence,
            limit=self.limit,
        )
        return result


class ForgeSettleSwarmResponse(StrictSchemaModel):
    """Settled run and optional outbox reconciliation receipt."""

    run: Annotated[SwarmRunSchema, Field(description="Canonical settled Swarm run.")]
    gate: Annotated[
        SwarmConvergenceGateSchema,
        Field(alias=ForgeBridgeFieldEnum.GATE.value, description="Verified settle gate."),
    ]
    settlement_id: Annotated[
        SwarmUUID,
        Field(alias=ForgeBridgeFieldEnum.SETTLEMENT_ID.value, description="Settlement UUID."),
    ]
    settled_file_count: Annotated[
        UInt64,
        Field(
            alias=ForgeBridgeFieldEnum.SETTLED_FILE_COUNT.value,
            description="Number of files settled by Forge.",
        ),
    ]
    settled_at_ms: Annotated[
        Int64,
        Field(alias=ForgeBridgeFieldEnum.SETTLED_AT_MS.value, description="Settlement time."),
    ]
    outbox_sequence: Annotated[
        UInt64 | None,
        Field(
            alias=ForgeBridgeFieldEnum.OUTBOX_SEQUENCE.value,
            description="Committed outbox sequence, or null.",
        ),
    ]
    outbox_sync: Annotated[
        SyncAutonomyOutboxResponse | None,
        Field(alias=ForgeBridgeFieldEnum.OUTBOX_SYNC.value, description="Sync outcome, or null."),
    ]
    purged_ephemeral: Annotated[
        bool,
        Field(
            alias=ForgeBridgeFieldEnum.PURGED_EPHEMERAL.value,
            description="Whether ephemeral worktrees were purged.",
        ),
    ]


class SyncAutonomyOutboxResponse(StrictSchemaModel):
    """Bounded autonomy outbox projection summary."""

    applied_count: Annotated[
        UInt64,
        Field(alias=ForgeBridgeFieldEnum.APPLIED_COUNT.value, description="Applied fact count."),
    ]
    dag_settled_count: Annotated[
        UInt64,
        Field(
            alias=ForgeBridgeFieldEnum.DAG_SETTLED_COUNT.value,
            description="New DAG settlement fact count.",
        ),
    ]
    swarm_settled_count: Annotated[
        UInt64,
        Field(
            alias=ForgeBridgeFieldEnum.SWARM_SETTLED_COUNT.value,
            description="New Swarm settlement fact count.",
        ),
    ]
    last_sequence: Annotated[
        UInt64,
        Field(alias=ForgeBridgeFieldEnum.LAST_SEQUENCE.value, description="Final source cursor."),
    ]
