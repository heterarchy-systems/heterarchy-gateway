"""Incrementally parse bounded source SSE frames into immutable DTOs."""

from app.orchestration.application.inner_dto.realtime_inner_dto import (
    OrchestrationRealtimeEventDto,
    OrchestrationResyncNoticeDto,
    RealtimeLagDetailsDto,
    RealtimeLagReasonDto,
    RealtimeSseFrameDto,
)
from app.orchestration.schema.realtime.orchestration_realtime_event_schema import (
    OrchestrationRealtimeEvent,
    OrchestrationResyncNoticeEvent,
    RealtimeLagReasonSchema,
)
from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeCursorComponentDigitsEnum,
    RealtimeEventKindEnum,
    RealtimeFrameByteLimitEnum,
    RealtimeResyncRetryMsEnum,
    RealtimeResyncUnitReasonEnum,
    RealtimeRetryDigitLimitEnum,
    RealtimeSourceChunkByteLimitEnum,
    RealtimeSseEventNameEnum,
    RealtimeSseFrameKindEnum,
)
from app.shared.types.base_types import JsonValue
from app.shared.types.json_contract import decode_json


def parse_event_cursor(value: str) -> tuple[int, int]:
    """Parse the source epoch and sequence cursor without signed coercion.

    Args:
        value: Source SSE id using its epoch and sequence decimal form.
    Return:
        Nonnegative unsigned cursor components.
    """
    components = value.split(":")
    if len(components) != 2:
        raise ValueError("Realtime SSE cursor must contain one colon")
    if any(
        not component
        or len(component) > RealtimeCursorComponentDigitsEnum.MAX_DIGITS
        or not component.isascii()
        or not component.isdecimal()
        for component in components
    ):
        raise ValueError("Realtime SSE cursor contains invalid unsigned decimal values")
    result = int(components[0]), int(components[1])
    if result[0] > (1 << 64) - 1 or result[1] > (1 << 64) - 1:
        raise ValueError("Realtime SSE cursor exceeds unsigned 64-bit range")
    return result


class RealtimeSseFrameParser:
    """Maintain one bounded incremental SSE frame parser."""

    def __init__(self) -> None:
        """Create an empty frame parser.

        Args:
            None.
        Return:
            None.
        """
        self._buffer = bytearray()
        self._frame_size = 0
        self._event_name: str | None = None
        self._cursor: str | None = None
        self._retry_value: str | None = None
        self._data_lines: list[bytes] = []
        self._comment_lines: list[str] = []

    def _reset_frame(self) -> None:
        """Clear accumulated fields after a complete frame boundary.

        Args:
            None.
        Return:
            None.
        """
        self._frame_size = 0
        self._event_name = None
        self._cursor = None
        self._retry_value = None
        self._data_lines.clear()
        self._comment_lines.clear()

    def _consume_line(self, line: bytes) -> RealtimeSseFrameDto | None:
        """Accumulate one UTF-8 SSE line and dispatch a blank boundary.

        Args:
            line: One line without its LF terminator.
        Return:
            A validated frame at blank boundaries, or None.
        """
        self._frame_size += len(line) + 1
        if self._frame_size > RealtimeFrameByteLimitEnum.MAX_BYTES:
            raise ValueError("Realtime SSE frame exceeded its byte limit")
        line = line.removesuffix(b"\r")
        match line:
            case b"":
                frame = self._complete_frame()
                self._reset_frame()
                return frame
            case value if value.startswith(b":"):
                comment = value[1:].removeprefix(b" ").decode("utf-8", errors="strict")
                self._comment_lines.append(comment)
                return None
            case _:
                pass
        field, separator, value = line.partition(b":")
        if separator and value.startswith(b" "):
            value = value[1:]
        field_name = field.decode("ascii", errors="strict")
        match field_name:
            case "data":
                self._data_lines.append(value)
            case "event":
                self._event_name = value.decode("utf-8", errors="strict")
            case "id":
                self._cursor = value.decode("utf-8", errors="strict")
            case "retry":
                self._retry_value = value.decode("ascii", errors="strict")
            case _:
                return None
        return None

    def _consume_complete_line(self, line: bytes) -> list[RealtimeSseFrameDto]:
        """Return frames completed by one terminated line.

        Args:
            line: One line without its LF terminator.
        Return:
            Zero or one completed frames.
        """
        frame = self._consume_line(line=line)
        result = [] if frame is None else [frame]
        return result

    def _append_partial_line(self, part: bytes) -> None:
        """Accumulate an incomplete line after enforcing its byte bound.

        Args:
            part: Un-terminated suffix from the latest source chunk.
        Return:
            None.
        """
        if self._frame_size + len(self._buffer) + len(part) > RealtimeFrameByteLimitEnum.MAX_BYTES:
            raise ValueError("Realtime SSE frame exceeded its byte limit")
        self._buffer.extend(part)

    def _complete_frame(self) -> RealtimeSseFrameDto | None:
        """Validate and materialize one completed SSE event or comment.

        Args:
            None.
        Return:
            Typed event, resync, or keepalive frame.
        """
        if not self._data_lines:
            if self._comment_lines:
                frame = RealtimeSseFrameDto(
                    kind=RealtimeSseFrameKindEnum.COMMENT,
                    event_name=None,
                    cursor=None,
                    sequence=None,
                    retry_ms=None,
                    comment="\n".join(self._comment_lines),
                    event=None,
                    resync=None,
                )
                return frame
            return None
        event_name = RealtimeSseEventNameEnum(self._event_name)
        data_value = decode_json(payload=b"\n".join(self._data_lines))
        retry_ms = self._parse_retry()
        match event_name:
            case RealtimeSseEventNameEnum.STATE_CHANGED:
                result = self._event_frame(value=data_value, retry_ms=retry_ms)
            case RealtimeSseEventNameEnum.RESYNC_REQUIRED:
                result = self._resync_frame(value=data_value, retry_ms=retry_ms)
        return result

    def _parse_retry(self) -> int | None:
        """Parse an optional decimal SSE retry hint into the source bound.

        Args:
            None.
        Return:
            Retry delay in milliseconds, or None when no retry field exists.
        """
        if self._retry_value is None:
            return None
        invalid_retry = (
            not self._retry_value
            or len(self._retry_value) > RealtimeRetryDigitLimitEnum.MAX_DIGITS
            or not self._retry_value.isascii()
            or not self._retry_value.isdecimal()
        )
        result = int(self._retry_value)
        if invalid_retry or result > (1 << 32) - 1:
            raise ValueError("Realtime SSE retry hint is not an unsigned decimal")
        return result

    def _event_frame(
        self,
        value: JsonValue,
        retry_ms: int | None,
    ) -> RealtimeSseFrameDto:
        """Validate a state change and bind its id cursor.

        Args:
            value: Decoded source event JSON object.
            retry_ms: Optional source retry hint.
        Return:
            Validated event frame retaining the source payload fields.
        """
        schema = OrchestrationRealtimeEvent.model_validate(value)
        if self._cursor is None or retry_ms is not None:
            raise ValueError("Realtime state-change event has invalid cursor or retry fields")
        cursor_epoch, cursor_sequence = parse_event_cursor(value=self._cursor)
        if (cursor_epoch, cursor_sequence) != (schema.epoch, schema.sequence):
            raise ValueError("Realtime SSE id does not match the event watermark")
        event = OrchestrationRealtimeEventDto(
            epoch=schema.epoch,
            sequence=schema.sequence,
            kind=RealtimeEventKindEnum(schema.kind),
            resource_id=schema.resource_id,
            resource_revision=schema.resource_revision,
            workspace_id=schema.workspace_id,
            occurred_at_ms=schema.occurred_at_ms,
        )
        cursor = f"{event.epoch}:{event.sequence}"
        result = RealtimeSseFrameDto(
            kind=RealtimeSseFrameKindEnum.EVENT,
            event_name=RealtimeSseEventNameEnum.STATE_CHANGED,
            cursor=cursor,
            sequence=event.sequence,
            retry_ms=None,
            comment=None,
            event=event,
            resync=None,
        )
        return result

    def _resync_frame(
        self,
        value: JsonValue,
        retry_ms: int | None,
    ) -> RealtimeSseFrameDto:
        """Validate the source terminal resynchronization notice.

        Args:
            value: Decoded source resync JSON object.
            retry_ms: Optional source reconnect hint.
        Return:
            Validated terminal resync frame without a cursor.
        """
        schema = OrchestrationResyncNoticeEvent.model_validate(value)
        if self._cursor is not None or retry_ms != RealtimeResyncRetryMsEnum.RETRY_MS:
            raise ValueError("Realtime resync notice has invalid cursor or retry fields")
        reason = schema.reason
        match reason:
            case RealtimeLagReasonSchema():
                resync_reason = RealtimeLagReasonDto(
                    lag=RealtimeLagDetailsDto(missed_events=reason.lag.missed_events)
                )
            case _:
                resync_reason = RealtimeResyncUnitReasonEnum(reason)
        notice = OrchestrationResyncNoticeDto(
            reason=resync_reason,
            current_epoch=schema.current_epoch,
            last_delivered_sequence=schema.last_delivered_sequence,
        )
        result = RealtimeSseFrameDto(
            kind=RealtimeSseFrameKindEnum.RESYNC,
            event_name=RealtimeSseEventNameEnum.RESYNC_REQUIRED,
            cursor=None,
            sequence=None,
            retry_ms=retry_ms,
            comment=None,
            event=None,
            resync=notice,
        )
        return result

    def feed(self, chunk: bytes) -> list[RealtimeSseFrameDto]:
        """Parse bounded SSE lines from one upstream byte chunk.

        Args:
            chunk: Raw upstream bytes read under the source identity encoding.
        Return:
            Validated frames completed by this chunk.
        """
        if len(chunk) > RealtimeSourceChunkByteLimitEnum.MAX_BYTES:
            raise ValueError("Realtime SSE source chunk exceeded its byte limit")
        frames: list[RealtimeSseFrameDto] = []
        parts = chunk.split(b"\n")
        for index, part in enumerate(parts):
            if index < len(parts) - 1:
                line = bytes(self._buffer) + part
                self._buffer.clear()
                frames.extend(self._consume_complete_line(line=line))
                continue
            self._append_partial_line(part=part)
        return frames

    def finish(self) -> list[RealtimeSseFrameDto]:
        """Reject a truncated final frame without advancing its cursor.

        Args:
            None.
        Return:
            No frames because only blank-line-terminated source frames dispatch.
        """
        has_unterminated_frame = bool(
            self._buffer or self._frame_size or self._data_lines or self._comment_lines
        )
        if has_unterminated_frame:
            raise ValueError("Realtime SSE stream ended inside a frame")
        result: list[RealtimeSseFrameDto] = []
        return result
