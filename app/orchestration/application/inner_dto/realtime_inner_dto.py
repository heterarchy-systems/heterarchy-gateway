"""Immutable DTOs for source realtime data and SSE transport frames."""

from dataclasses import dataclass
from uuid import UUID

from app.orchestration.application.inner_dto.types.realtime_types import (
    OrchestrationRealtimeEventDict,
    OrchestrationResyncNoticeDict,
    RealtimeLagDetailsDict,
    RealtimeLagReasonDict,
    RealtimeQueuedFrameDict,
    RealtimeSseFrameDict,
)
from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeEventKindEnum,
    RealtimeResyncUnitReasonEnum,
    RealtimeSseEventNameEnum,
    RealtimeSseFrameKindEnum,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class OrchestrationRealtimeEventDto:
    """Validated source event with its seven original JSON fields."""

    epoch: int
    sequence: int
    kind: RealtimeEventKindEnum
    resource_id: UUID
    resource_revision: int
    workspace_id: UUID | None
    occurred_at_ms: int

    def to_dict(self) -> OrchestrationRealtimeEventDict:
        """Serialize the source event body without adding a Gateway field.

        Args:
            None.
        Return:
            Closed seven-field source event mapping.
        """
        result = OrchestrationRealtimeEventDict(
            epoch=self.epoch,
            sequence=self.sequence,
            kind=self.kind.value,
            resourceId=str(self.resource_id),
            resourceRevision=self.resource_revision,
            workspaceId=str(self.workspace_id) if self.workspace_id is not None else None,
            occurredAtMs=self.occurred_at_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class RealtimeLagDetailsDto:
    """Immutable count carried by the source lag resync reason."""

    missed_events: int

    def to_dict(self) -> RealtimeLagDetailsDict:
        """Serialize the source camel-case lag count.

        Args:
            None.
        Return:
            Closed lag detail mapping.
        """
        result = RealtimeLagDetailsDict(missedEvents=self.missed_events)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class RealtimeLagReasonDto:
    """Immutable externally tagged lag reason."""

    lag: RealtimeLagDetailsDto

    def to_dict(self) -> RealtimeLagReasonDict:
        """Serialize the source's externally tagged lag variant.

        Args:
            None.
        Return:
            Closed externally tagged lag mapping.
        """
        result = RealtimeLagReasonDict(lag=self.lag.to_dict())
        return result


type OrchestrationRealtimeResyncReasonDto = RealtimeLagReasonDto | RealtimeResyncUnitReasonEnum


@dataclass(frozen=True, slots=True, kw_only=True)
class OrchestrationResyncNoticeDto:
    """Validated source terminal notice with no synthetic cursor fields."""

    reason: OrchestrationRealtimeResyncReasonDto
    current_epoch: int
    last_delivered_sequence: int

    def to_dict(self) -> OrchestrationResyncNoticeDict:
        """Serialize the exact source resync notice fields.

        Args:
            None.
        Return:
            Closed source resync notice mapping.
        """
        reason = (
            self.reason.to_dict() if isinstance(self.reason, RealtimeLagReasonDto) else self.reason
        )
        result = OrchestrationResyncNoticeDict(
            reason=reason,
            currentEpoch=self.current_epoch,
            lastDeliveredSequence=self.last_delivered_sequence,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class RealtimeSseFrameDto:
    """Bounded validated frame with a separate source SSE cursor."""

    kind: RealtimeSseFrameKindEnum
    event_name: RealtimeSseEventNameEnum | None
    cursor: str | None
    sequence: int | None
    retry_ms: int | None
    comment: str | None
    event: OrchestrationRealtimeEventDto | None
    resync: OrchestrationResyncNoticeDto | None

    def to_dict(self) -> RealtimeSseFrameDict:
        """Serialize relay metadata and its optional typed source payload.

        Args:
            None.
        Return:
            Closed relay-frame mapping with required nullable fields.
        """
        event = self.event.to_dict() if self.event is not None else None
        resync = self.resync.to_dict() if self.resync is not None else None
        result = RealtimeSseFrameDict(
            kind=self.kind,
            eventName=self.event_name,
            cursor=self.cursor,
            sequence=self.sequence,
            retryMs=self.retry_ms,
            comment=self.comment,
            event=event,
            resync=resync,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class RealtimeQueuedFrameDto:
    """Bounded wire bytes queued between source reader and ASGI sender."""

    kind: RealtimeSseFrameKindEnum
    cursor: str | None
    sequence: int | None
    last_delivered_sequence: int | None
    payload: bytes

    def to_dict(self) -> RealtimeQueuedFrameDict:
        """Serialize the queued wire frame and its delivery cursor.

        Args:
            None.
        Return:
            Closed bounded-queue frame mapping.
        """
        result = RealtimeQueuedFrameDict(
            kind=self.kind,
            cursor=self.cursor,
            sequence=self.sequence,
            lastDeliveredSequence=self.last_delivered_sequence,
            payload=self.payload,
        )
        return result
