"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing_extensions import TypedDict

from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeResyncUnitReasonEnum,
    RealtimeSseEventNameEnum,
    RealtimeSseFrameKindEnum,
)


class OrchestrationRealtimeEventDict(TypedDict, total=True, closed=True):
    """Exact seven-field source event body."""

    epoch: int
    sequence: int
    kind: str
    resourceId: str
    resourceRevision: int
    workspaceId: str | None
    occurredAtMs: int


class RealtimeLagDetailsDict(TypedDict, total=True, closed=True):
    """Lag count nested under the source's external enum tag."""

    missedEvents: int


class RealtimeLagReasonDict(TypedDict, total=True, closed=True):
    """Externally tagged source lag reason."""

    lag: RealtimeLagDetailsDict


type OrchestrationRealtimeResyncReasonDict = RealtimeLagReasonDict | RealtimeResyncUnitReasonEnum


class OrchestrationResyncNoticeDict(TypedDict, total=True, closed=True):
    """Exact source terminal resync data body."""

    reason: OrchestrationRealtimeResyncReasonDict
    currentEpoch: int
    lastDeliveredSequence: int


class RealtimeSseFrameDict(TypedDict, total=True, closed=True):
    """Validated frame and delivery metadata owned by the Gateway relay."""

    kind: RealtimeSseFrameKindEnum
    eventName: RealtimeSseEventNameEnum | None
    cursor: str | None
    sequence: int | None
    retryMs: int | None
    comment: str | None
    event: OrchestrationRealtimeEventDict | None
    resync: OrchestrationResyncNoticeDict | None


class RealtimeQueuedFrameDict(TypedDict, total=True, closed=True):
    """One fully encoded SSE frame with cursor and sequence metadata."""

    kind: RealtimeSseFrameKindEnum
    cursor: str | None
    sequence: int | None
    lastDeliveredSequence: int | None
    payload: bytes
