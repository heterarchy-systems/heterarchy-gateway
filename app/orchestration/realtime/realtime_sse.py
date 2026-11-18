"""Relay OrchestrationRealtimeEvent using cursor, last_delivered_sequence, resync_required, and Last-Event-ID."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import override
from uuid import UUID

import httpx
from fastapi import status
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.orchestration.application.inner_dto.realtime_inner_dto import (
    OrchestrationRealtimeEventDto,
    RealtimeQueuedFrameDto,
    RealtimeSseFrameDto,
)
from app.orchestration.exceptions.orchestration_exceptions import (
    OrchestrationBackendErrorResponse,
)
from app.orchestration.exceptions.realtime_exceptions import (
    OrchestrationRealtimeAdmissionError,
)
from app.orchestration.realtime.realtime_frame_parser import (
    RealtimeSseFrameParser,
    encode_sse_frame,
    parse_event_cursor,
)
from app.orchestration.schema.types.realtime_types import (
    RealtimeAsgiMessage,
    RealtimeAsgiSend,
)
from app.shared.api_calling_box.orchestration_event_calling import (
    OrchestrationEventCalling,
)
from app.shared.exception import OrchestrationExcept
from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeAdmissionErrorByteLimitEnum,
    RealtimeCacheControlEnum,
    RealtimeContentEncodingEnum,
    RealtimeEventDispositionEnum,
    RealtimeFrameByteLimitEnum,
    RealtimeHeaderNameEnum,
    RealtimeMediaTypeEnum,
    RealtimeProxyBufferingEnum,
    RealtimeQueueByteCapacityEnum,
    RealtimeQueueEventCapacityEnum,
    RealtimeSendTimeoutMsEnum,
    RealtimeSourceChunkByteLimitEnum,
    RealtimeSseFrameKindEnum,
)
from app.shared.types.json_contract import decode_json

REALTIME_SEND_TIMEOUT_MS = RealtimeSendTimeoutMsEnum.TIMEOUT_MS


async def _cancel_and_join_task(task: asyncio.Task[None] | None) -> None:
    """Cancel and join the one request-owned upstream reader task.

    Args:
        task: Source reader task owned by the realtime relay.
    Return:
        None after the task has completed or propagated caller cancellation.
    """
    if task is None:
        return
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        current = asyncio.current_task()
        if current is not None and current.cancelling() > 0:
            raise


class SendTimeoutStreamingResponse(StreamingResponse):
    """Apply a bounded deadline to every ASGI response send."""

    def __init__(self, relay: RealtimeStreamRelay) -> None:
        """Bind the response body to its relay resource owner.

        Args:
            relay: Request-scoped producer, queue, and source response owner.
        Return:
            None.
        """
        self._relay = relay
        self._body = relay.stream()
        super().__init__(
            self._body,
            status_code=status.HTTP_200_OK,
            headers=httpx.Headers(
                (
                    (
                        RealtimeHeaderNameEnum.CACHE_CONTROL.value,
                        RealtimeCacheControlEnum.NO_CACHE.value,
                    ),
                    (
                        RealtimeHeaderNameEnum.X_ACCEL_BUFFERING.value,
                        RealtimeProxyBufferingEnum.DISABLED.value,
                    ),
                )
            ),
            media_type=RealtimeMediaTypeEnum.EVENT_STREAM.value,
        )

    @override
    async def stream_response(self, send: RealtimeAsgiSend) -> None:
        """Send headers and every body frame under the configured deadline.

        Args:
            send: ASGI send callable owned by Starlette.
        Return:
            None.
        """

        async def send_with_deadline(message: RealtimeAsgiMessage) -> None:
            """Bound one downstream ASGI send, including a blocked body frame.

            Args:
                message: ASGI response message from StreamingResponse.
            Return:
                None.
            """
            await asyncio.wait_for(send(message), timeout=REALTIME_SEND_TIMEOUT_MS / 1000)

        try:
            await super().stream_response(send=send_with_deadline)
        finally:
            try:
                await self._relay.aclose()
            finally:
                await self._body.aclose()


class RealtimeStreamRelay:
    """Own bounded source ordering, producer work, and downstream watermarks."""

    def __init__(
        self,
        calling: OrchestrationEventCalling,
        response: httpx.Response,
        workspace_id: UUID,
        resume_cursor: tuple[int, int] | None,
    ) -> None:
        """Bind the source response and its workspace and resume fences.

        Args:
            calling: Caller responsible for closing the upstream client.
            response: Successful identity-encoded upstream stream.
            workspace_id: Workspace whose observations are allowed downstream.
            resume_cursor: Parsed epoch and sequence supplied in Last-Event-ID.
        Return:
            None.
        """
        self._calling = calling
        self._response = response
        self._workspace_id = workspace_id
        self._resume_cursor = resume_cursor
        self._source_epoch = resume_cursor[0] if resume_cursor is not None else None
        self._last_source_sequence = 0
        self._last_source_cursor: str | None = None
        self._last_source_event: OrchestrationRealtimeEventDto | None = None
        self._last_delivered_sequence = 0
        self._queue: asyncio.Queue[RealtimeQueuedFrameDto] = asyncio.Queue(maxsize=64)
        if self._queue.maxsize != RealtimeQueueEventCapacityEnum.MAX_EVENTS:
            raise RuntimeError("Realtime event queue capacity no longer matches its contract")
        if (
            RealtimeQueueEventCapacityEnum.MAX_EVENTS * RealtimeFrameByteLimitEnum.MAX_BYTES
            != RealtimeQueueByteCapacityEnum.MAX_BYTES
        ):
            raise RuntimeError("Realtime event frame bounds exceed the queue byte budget")
        self._pump_task: asyncio.Task[None] | None = None
        self._failure: Exception | None = None
        self._closed = False

    @staticmethod
    def _end_frame() -> RealtimeQueuedFrameDto:
        """Create the internal end marker for a completed source pump.

        Args:
            None.
        Return:
            Empty bounded-queue control frame.
        """
        result = RealtimeQueuedFrameDto(
            kind=RealtimeSseFrameKindEnum.END,
            cursor=None,
            sequence=None,
            last_delivered_sequence=None,
            payload=b"",
        )
        return result

    def _queue_frame(self, frame: RealtimeSseFrameDto) -> RealtimeQueuedFrameDto:
        """Encode a validated frame and retain its source watermark metadata.

        Args:
            frame: Parsed source event, resync, or comment frame.
        Return:
            One bounded queue DTO retaining the exact wire payload.
        """
        notice = frame.resync
        source_watermark = notice.last_delivered_sequence if notice is not None else None
        result = RealtimeQueuedFrameDto(
            kind=frame.kind,
            cursor=frame.cursor,
            sequence=frame.sequence,
            last_delivered_sequence=source_watermark,
            payload=encode_sse_frame(frame=frame),
        )
        return result

    def _observe_epoch(self, epoch: int) -> None:
        """Bind the source epoch on first frame and enforce it thereafter.

        Args:
            epoch: Epoch from one validated event or resync notice.
        Return:
            None.
        """
        if self._source_epoch is None:
            self._source_epoch = epoch
        elif self._source_epoch != epoch:
            raise ValueError("Realtime source changed hub epoch inside one stream")

    def _require_workspace_event(self, event: OrchestrationRealtimeEventDto) -> None:
        """Require the source workspace filter to match every event.

        Args:
            event: Validated source event.
        Return:
            None.
        """
        if event.workspace_id != self._workspace_id:
            raise ValueError("Realtime source event escaped the requested Workspace")

    def _event_cursor(
        self,
        frame: RealtimeSseFrameDto,
    ) -> tuple[str, OrchestrationRealtimeEventDto]:
        """Return the event and cursor fields required by the source contract.

        Args:
            frame: Parsed source event frame.
        Return:
            Cursor id and validated source event DTO.
        """
        if frame.cursor is None or frame.event is None:
            raise ValueError("Realtime event frame is missing its cursor or data")
        result = frame.cursor, frame.event
        return result

    def _classify_event(
        self,
        cursor: str,
        event: OrchestrationRealtimeEventDto,
    ) -> RealtimeEventDispositionEnum:
        """Classify duplicates, resume-fenced frames, and new source events.

        Args:
            cursor: Canonical source epoch and sequence cursor.
            event: Validated source event data.
        Return:
            One event-order decision for the relay.
        """
        same_event = (
            event.sequence == self._last_source_sequence
            and cursor == self._last_source_cursor
            and event == self._last_source_event
        )
        behind_resume = self._resume_cursor is not None and event.sequence <= self._resume_cursor[1]
        moved_backwards = (
            self._last_source_cursor is not None
            and event.sequence <= self._last_source_sequence
            and not same_event
        )
        match (same_event, behind_resume, moved_backwards):
            case (True, _, _):
                result = RealtimeEventDispositionEnum.DUPLICATE
            case (False, _, True):
                raise ValueError("Realtime source event sequence moved backwards")
            case (False, True, False):
                result = RealtimeEventDispositionEnum.RESUME_FENCED
            case _:
                result = RealtimeEventDispositionEnum.NEW
        return result

    def _remember_source_event(self, cursor: str, event: OrchestrationRealtimeEventDto) -> None:
        """Advance source-side ordering after a previously unseen cursor.

        Args:
            cursor: Canonical source event cursor.
            event: Source event data bound to that cursor.
        Return:
            None.
        """
        self._last_source_sequence = event.sequence
        self._last_source_cursor = cursor
        self._last_source_event = event

    def _accept_source_event(self, frame: RealtimeSseFrameDto) -> bool:
        """Filter exact replays and validate monotonic scoped source events.

        Args:
            frame: Parsed source event frame.
        Return:
            Whether this frame should enter the downstream queue.
        """
        cursor, event = self._event_cursor(frame=frame)
        self._require_workspace_event(event=event)
        self._observe_epoch(epoch=event.epoch)
        disposition = self._classify_event(cursor=cursor, event=event)
        match disposition:
            case RealtimeEventDispositionEnum.DUPLICATE:
                result = False
            case RealtimeEventDispositionEnum.RESUME_FENCED:
                self._remember_source_event(cursor=cursor, event=event)
                result = False
            case RealtimeEventDispositionEnum.NEW:
                self._remember_source_event(cursor=cursor, event=event)
                result = True
        return result

    def _verify_resync_watermark(self, frame: RealtimeSseFrameDto) -> None:
        """Match a terminal source notice to all source events already received.

        Args:
            frame: Terminal resync frame after prior queued events were sent.
        Return:
            None when source epoch and source delivery watermark agree.
        """
        if frame.resync is None:
            raise ValueError("Realtime resync frame is missing its source notice")
        self._observe_epoch(epoch=frame.resync.current_epoch)
        if frame.resync.last_delivered_sequence != self._last_source_sequence:
            raise ValueError("Realtime resync watermark does not match source event order")

    def _accept_source_frame(self, frame: RealtimeSseFrameDto) -> bool:
        """Validate source event order and retain terminal resync frames.

        Args:
            frame: Parsed event, resync, comment, or end frame.
        Return:
            Whether the frame is part of the source stream.
        """
        match frame.kind:
            case RealtimeSseFrameKindEnum.EVENT:
                result = self._accept_source_event(frame=frame)
            case RealtimeSseFrameKindEnum.RESYNC:
                self._verify_resync_watermark(frame=frame)
                result = True
            case RealtimeSseFrameKindEnum.COMMENT:
                result = True
            case RealtimeSseFrameKindEnum.END:
                result = False
        return result

    def _record_downstream_delivery(self, frame: RealtimeQueuedFrameDto) -> None:
        """Advance the client watermark only after ASGI send has completed.

        Args:
            frame: Encoded source event frame whose send completed.
        Return:
            None.
        """
        if frame.kind is RealtimeSseFrameKindEnum.EVENT:
            if frame.sequence is None:
                raise ValueError("Realtime queued event is missing its sequence")
            self._last_delivered_sequence = frame.sequence

    def _raise_pump_failure(self) -> None:
        """Propagate a source pump failure after its queued prefix is sent.

        Args:
            None.
        Return:
            None when the pump ended normally.
        """
        if self._failure is not None:
            raise self._failure

    async def _pump_source(self) -> None:
        """Read source chunks and backpressure into the bounded frame queue.

        Args:
            None.
        Return:
            None.
        """

        parser = RealtimeSseFrameParser()
        try:
            async for transport_chunk in self._response.aiter_raw():
                chunk_size = RealtimeSourceChunkByteLimitEnum.MAX_BYTES
                for offset in range(0, len(transport_chunk), chunk_size):
                    chunk = transport_chunk[offset : offset + chunk_size]
                    for frame in parser.feed(chunk=chunk):
                        if not self._accept_source_frame(frame=frame):
                            continue
                        queued = self._queue_frame(frame=frame)
                        await self._queue.put(queued)
                        if frame.kind is RealtimeSseFrameKindEnum.RESYNC:
                            await self._queue.put(self._end_frame())
                            return
            for frame in parser.finish():
                queued = self._queue_frame(frame=frame)
                await self._queue.put(queued)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            self._failure = error
        await self._queue.put(self._end_frame())

    async def aclose(self) -> None:
        """Cancel and join the producer before closing the source response.

        Args:
            None.
        Return:
            None.
        """
        if self._closed:
            return
        self._closed = True
        try:
            await _cancel_and_join_task(task=self._pump_task)
        finally:
            await self._calling.aclose()

    async def stream(self) -> AsyncGenerator[bytes]:
        """Relay frames and own producer completion on every cancellation path.

        Args:
            None.
        Return:
            Incremental SSE frames for StreamingResponse.
        """
        self._pump_task = asyncio.create_task(
            self._pump_source(),
            name="orchestration-realtime-source-pump",
        )
        try:
            while True:
                frame = await self._queue.get()
                if frame.kind is RealtimeSseFrameKindEnum.END:
                    self._raise_pump_failure()
                    break
                yield frame.payload
                self._record_downstream_delivery(frame=frame)
        finally:
            await self.aclose()


def _require_identity_encoding(response: httpx.Response, workspace_id: UUID) -> None:
    """Reject compressed streams before their body reader starts.

    Args:
        response: Open upstream response.
        workspace_id: Workspace used to correlate the Gateway failure.
    Return:
        None for the supported identity encoding.
    """
    encoding = (
        response.headers.get(
            RealtimeHeaderNameEnum.CONTENT_ENCODING.value,
            RealtimeContentEncodingEnum.IDENTITY.value,
        )
        .strip()
        .lower()
    )
    if encoding != RealtimeContentEncodingEnum.IDENTITY.value:
        raise OrchestrationExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="orchestration_unsupported_content_encoding",
            message="Upstream orchestration event stream used unsupported content encoding",
            retryable=False,
            workspace_id=workspace_id,
        )


async def _source_admission_error(
    response: httpx.Response,
    workspace_id: UUID,
) -> OrchestrationRealtimeAdmissionError:
    """Read and preserve one bounded typed source admission error.

    Args:
        response: Non-200 upstream subscription response.
        workspace_id: Workspace selected by the Gateway route.
    Return:
        Typed source status and body with optional retry guidance.
    """
    body = bytearray()
    async for chunk in response.aiter_bytes(chunk_size=RealtimeSourceChunkByteLimitEnum.MAX_BYTES):
        if len(body) + len(chunk) > RealtimeAdmissionErrorByteLimitEnum.MAX_BYTES:
            raise OrchestrationExcept(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code="orchestration_realtime_error_too_large",
                message="Upstream orchestration realtime error exceeded its byte limit",
                retryable=False,
                workspace_id=workspace_id,
            )
        body.extend(chunk)
    error = OrchestrationBackendErrorResponse.model_validate(decode_json(payload=bytes(body)))
    error_dto = error.to_inner_dto()
    retry_after = response.headers.get(RealtimeHeaderNameEnum.RETRY_AFTER.value)
    result = OrchestrationRealtimeAdmissionError(
        status_code=response.status_code,
        error=error_dto,
        retry_after=retry_after,
    )
    return result


async def open_realtime_stream(
    calling: OrchestrationEventCalling,
    workspace_id: UUID,
    last_event_id: str | None,
    session_id: str | None,
) -> SendTimeoutStreamingResponse:
    """Open and validate a source SSE response before returning HTTP headers.

    Args:
        calling: Request-owned Orchestration event caller.
        workspace_id: Workspace scope selected by the Gateway route.
        last_event_id: Optional source cursor supplied by the caller.
        session_id: Optional source session-read selector.
    Return:
        Managed streaming response whose owner closes every upstream resource.
    """
    try:
        response = await calling.open_events(
            workspace_id=workspace_id, last_event_id=last_event_id, session_id=session_id
        )
        _require_identity_encoding(response=response, workspace_id=workspace_id)
        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise await _source_admission_error(response=response, workspace_id=workspace_id)
        if response.status_code != status.HTTP_200_OK:
            raise OrchestrationExcept(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code="orchestration_invalid_event_stream_status",
                message="Upstream orchestration returned an unexpected event-stream status",
                retryable=False,
                workspace_id=workspace_id,
            )
        content_type = (
            response.headers.get(RealtimeHeaderNameEnum.CONTENT_TYPE.value, "")
            .split(";", 1)[0]
            .strip()
            .lower()
        )
        if content_type != RealtimeMediaTypeEnum.EVENT_STREAM.value:
            raise OrchestrationExcept(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code="orchestration_invalid_event_stream",
                message="Upstream orchestration did not return an event stream",
                retryable=False,
                workspace_id=workspace_id,
            )
        resume_cursor = (
            parse_event_cursor(value=last_event_id) if last_event_id is not None else None
        )
    except httpx.TimeoutException as error:
        await calling.aclose()
        raise OrchestrationExcept(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            code="orchestration_timeout",
            message="Upstream orchestration event stream timed out before admission",
            retryable=True,
            workspace_id=workspace_id,
        ) from error
    except httpx.HTTPError as error:
        await calling.aclose()
        raise OrchestrationExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="orchestration_transport_error",
            message="Upstream orchestration event stream transport failed",
            retryable=True,
            workspace_id=workspace_id,
        ) from error
    except (ValidationError, ValueError) as error:
        await calling.aclose()
        raise OrchestrationExcept(
            status_code=status.HTTP_502_BAD_GATEWAY,
            code="orchestration_invalid_event_stream_error",
            message="Upstream orchestration returned an invalid event-stream admission error",
            retryable=False,
            workspace_id=workspace_id,
        ) from error
    except BaseException:
        await calling.aclose()
        raise
    relay = RealtimeStreamRelay(
        calling=calling, response=response, workspace_id=workspace_id, resume_cursor=resume_cursor
    )
    result = SendTimeoutStreamingResponse(relay=relay)
    return result
