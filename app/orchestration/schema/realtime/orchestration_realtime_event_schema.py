"""Strict wire schemas for Orchestration realtime stream data."""

from functools import partial
from typing import Annotated

from pydantic import BeforeValidator, Field

from app.orchestration.schema.types.orchestration_types import TimestampMs, UInt64
from app.shared.base_schema import StrictRootSchemaModel, StrictSchemaModel
from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeEventKindEnum,
    RealtimeResyncUnitReasonEnum,
)
from app.shared.types.wire_scalar_types import WireUUID, parse_wire_enum

type RealtimeEventKind = Annotated[
    RealtimeEventKindEnum,
    BeforeValidator(partial(parse_wire_enum, RealtimeEventKindEnum)),
]
type RealtimeResyncUnitReason = Annotated[
    RealtimeResyncUnitReasonEnum,
    BeforeValidator(partial(parse_wire_enum, RealtimeResyncUnitReasonEnum)),
]


class OrchestrationRealtimeEvent(StrictSchemaModel):
    """One committed Orchestration observation carried in SSE data."""

    epoch: Annotated[UInt64, Field(description="Realtime hub epoch.", gt=0)]
    sequence: Annotated[UInt64, Field(description="Monotonic event sequence.", gt=0)]
    kind: Annotated[RealtimeEventKind, Field(description="Closed source event kind.")]
    resource_id: Annotated[
        WireUUID,
        Field(alias="resourceId", description="Affected source resource UUID."),
    ]
    resource_revision: Annotated[
        UInt64,
        Field(alias="resourceRevision", description="Resource revision after the commit."),
    ]
    workspace_id: Annotated[
        WireUUID | None,
        Field(alias="workspaceId", description="Workspace scope, or explicit null."),
    ]
    occurred_at_ms: Annotated[
        TimestampMs,
        Field(alias="occurredAtMs", description="Commit timestamp in Unix milliseconds.", gt=0),
    ]


class RealtimeLagDetailsSchema(StrictSchemaModel):
    """Number of live observations skipped before terminal resync."""

    missed_events: Annotated[
        UInt64,
        Field(alias="missedEvents", description="Number of missed live events."),
    ]


class RealtimeLagReasonSchema(StrictSchemaModel):
    """Externally tagged lag reason used by the source resync notice."""

    lag: Annotated[
        RealtimeLagDetailsSchema,
        Field(description="Live channel lag details."),
    ]


type RealtimeResyncReason = Annotated[
    RealtimeLagReasonSchema | RealtimeResyncUnitReason,
    Field(description="Source externally tagged reason for terminal resynchronization."),
]


class OrchestrationResyncNoticeEvent(StrictSchemaModel):
    """Terminal source notice requiring canonical state reload and reconnect."""

    reason: Annotated[
        RealtimeResyncReason,
        Field(description="Source reason for terminating this stream."),
    ]
    current_epoch: Annotated[
        UInt64,
        Field(alias="currentEpoch", description="Current source hub epoch.", gt=0),
    ]
    last_delivered_sequence: Annotated[
        UInt64,
        Field(
            alias="lastDeliveredSequence",
            description="Last event sequence actually delivered, or zero.",
        ),
    ]


class OrchestrationRealtimeData(
    StrictRootSchemaModel[OrchestrationRealtimeEvent | OrchestrationResyncNoticeEvent]
):
    """Union of complete event or resync JSON bodies registered for diagnostics."""
