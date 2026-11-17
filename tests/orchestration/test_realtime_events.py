"""Dictionary-grouped SSE cursor, frame, and workspace-route contracts."""

import asyncio
from collections.abc import AsyncIterator, Callable
from uuid import UUID

import httpx
import pytest
from starlette.requests import ClientDisconnect

from app.orchestration.application.inner_dto.realtime_inner_dto import RealtimeSseFrameDto
from app.orchestration.realtime import realtime_sse
from app.orchestration.realtime.realtime_frame_parser import RealtimeSseFrameParser
from app.orchestration.realtime.realtime_sse import open_realtime_stream
from app.orchestration.schema.types.realtime_types import RealtimeAsgiMessage
from app.shared.api_calling_box.orchestration_event_calling import (
    OrchestrationEventCalling,
)
from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeFrameByteLimitEnum,
    RealtimeQueueByteCapacityEnum,
    RealtimeQueueEventCapacityEnum,
)
from app.shared.types.base_types import JsonObject
from app.shared.types.json_contract import encode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder

_WORKSPACE_ID = "10000000-0000-0000-0000-000000000001"
_SESSION_ID = "20000000-0000-0000-0000-000000000002"
_EVENT_PATH = f"/orchestrations/workspaces/{_WORKSPACE_ID}/events"
_UPSTREAM_EVENT_PATH = f"/v1/workspaces/{_WORKSPACE_ID}/events"
_EVENT_DATA: JsonObject = {
    "epoch": 7,
    "sequence": 9,
    "kind": "team_changed",
    "resourceId": "30000000-0000-0000-0000-000000000003",
    "resourceRevision": 4,
    "workspaceId": _WORKSPACE_ID,
    "occurredAtMs": 1_700_000_000_000,
}
_RESYNC_DATA: JsonObject = {
    "reason": {"lag": {"missedEvents": 4}},
    "currentEpoch": 7,
    "lastDeliveredSequence": 9,
}


def _admission_handler(
    status_code: int,
    payload: JsonObject,
    headers: dict[str, str],
    observed: list[httpx.Request] | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    """Build one response handler for a source cursor-admission case.

    Args:
        status_code: Expected source admission status.
        payload: Source-owned typed error body.
        headers: Source headers including optional retry guidance.
    Return:
        Mock handler returning the selected source response.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if observed is not None:
            observed.append(request)
        response = httpx.Response(
            status_code,
            headers=headers,
            json=payload,
            request=request,
        )
        return response

    return handler


class _TrackedEventStream(httpx.AsyncByteStream):
    """One upstream body recording whether the caller closed it."""

    def __init__(self, body: bytes) -> None:
        self._body = body
        self.started = False
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield the single source byte body.

        Args:
            None.
        Return:
            Asynchronous upstream chunks.
        """
        self.started = True
        yield self._body

    async def aclose(self) -> None:
        """Record response ownership cleanup.

        Args:
            None.
        Return:
            None.
        """
        self.closed = True


class _BlockingEventStream(httpx.AsyncByteStream):
    """Hold the source reader open after one complete source event."""

    def __init__(self, event_body: bytes) -> None:
        self._event_body = event_body
        self.waiting_for_source = asyncio.Event()
        self.cancelled = False
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield one complete event and wait for the source connection to close.

        Args:
            None.
        Return:
            First event bytes before a blocked live read.
        """
        yield self._event_body
        self.waiting_for_source.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def aclose(self) -> None:
        """Record source response cleanup.

        Args:
            None.
        Return:
            None.
        """
        self.closed = True


def _sse_body() -> bytes:
    event = (
        b"id: 7:9\nevent: state_changed\ndata:"
        + encode_json(_EVENT_DATA)
        + b"\n\n:keep-alive\n\nevent: resync_required\nretry: 2000\ndata:"
        + encode_json(_RESYNC_DATA)
        + b"\n\n"
    )
    result = event
    return result


def _source_event_frame(sequence: int) -> bytes:
    """Encode one small source event for streaming ownership tests.

    Args:
        sequence: Source sequence assigned to the test event.
    Return:
        One complete state_changed SSE frame.
    """
    event = {
        **_EVENT_DATA,
        "sequence": sequence,
        "resourceRevision": sequence,
    }
    result = (
        f"id: 7:{sequence}\nevent: state_changed\ndata:".encode("ascii")
        + encode_json(event)
        + b"\n\n"
    )
    return result


def _parsed_event_frame(
    sequence: int,
    workspace_id: str | None = _WORKSPACE_ID,
    epoch: int = 7,
) -> RealtimeSseFrameDto:
    """Parse one source event for explicit relay ordering cases.

    Args:
        sequence: Source sequence assigned to the event.
        workspace_id: Source Workspace projection, or null.
        epoch: Source hub epoch.
    Return:
        Complete typed SSE event frame with a matching cursor.
    """
    event = {
        **_EVENT_DATA,
        "epoch": epoch,
        "sequence": sequence,
        "resourceRevision": sequence,
        "workspaceId": workspace_id,
    }
    parser = RealtimeSseFrameParser()
    frames = parser.feed(
        f"id: {epoch}:{sequence}\nevent: state_changed\ndata:".encode("ascii")
        + encode_json(event)
        + b"\n\n"
    )
    if len(frames) != 1:
        raise AssertionError("Expected one complete source event frame")
    result = frames[0]
    return result


def test_frame_parser_preserves_source_event_resync_and_sse_cursor() -> None:
    wire = _sse_body()
    parser = RealtimeSseFrameParser()
    frames = parser.feed(wire[:19]) + parser.feed(wire[19:])

    assert len(frames) == 3
    event = frames[0].to_dict()
    assert event["cursor"] == "7:9"
    assert event["event"] == _EVENT_DATA
    assert event["eventName"] == "state_changed"
    heartbeat = frames[1].to_dict()
    assert heartbeat["comment"] == "keep-alive"
    resync = frames[2].to_dict()
    assert resync["cursor"] is None
    assert resync["eventName"] == "resync_required"
    assert resync["retryMs"] == 2000
    assert resync["resync"] == _RESYNC_DATA


def test_frame_parser_rejects_bad_cursor_unknown_kind_and_oversized_frame() -> None:
    cases: dict[str, bytes] = {
        "missing id": (b"event: state_changed\ndata:" + encode_json(_EVENT_DATA) + b"\n\n"),
        "wrong id": (b"id: 7:8\nevent: state_changed\ndata:" + encode_json(_EVENT_DATA) + b"\n\n"),
        "unknown kind": (
            b"id: 7:9\nevent: state_changed\ndata:"
            + encode_json({**_EVENT_DATA, "kind": "invented"})
            + b"\n\n"
        ),
        "unrecognized event": (b"event: invented\ndata:" + encode_json(_EVENT_DATA) + b"\n\n"),
        "oversized source frame": (b"data:" + b"x" * 16_384),
    }
    for wire in cases.values():
        with pytest.raises(ValueError):
            RealtimeSseFrameParser().feed(wire)
    truncated = RealtimeSseFrameParser()
    incomplete = b"id: 7:9\nevent: state_changed\ndata:" + encode_json(_EVENT_DATA) + b"\n"
    assert truncated.feed(incomplete) == []
    with pytest.raises(ValueError, match="ended inside a frame"):
        truncated.finish()


def test_realtime_relay_enforces_resume_epoch_scope_order_and_dedupe() -> None:
    async def exercise() -> None:
        event_frame = _parsed_event_frame(6)
        caller = OrchestrationEventCalling(
            "http://orchestration.example.test",
            None,
            5.0,
            httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
        )
        relay = realtime_sse.RealtimeStreamRelay(
            caller,
            httpx.Response(200, content=b""),
            UUID(_WORKSPACE_ID),
            (7, 5),
        )
        assert relay._queue.maxsize == RealtimeQueueEventCapacityEnum.MAX_EVENTS
        assert (
            relay._queue.maxsize * RealtimeFrameByteLimitEnum.MAX_BYTES
            == RealtimeQueueByteCapacityEnum.MAX_BYTES
        )
        assert relay._accept_source_frame(_parsed_event_frame(2)) is False
        assert relay._accept_source_frame(event_frame) is True
        assert relay._accept_source_frame(event_frame) is False
        assert relay._accept_source_frame(_parsed_event_frame(11)) is True
        assert relay._last_delivered_sequence == 0
        with pytest.raises(ValueError, match="Workspace"):
            relay._accept_source_frame(_parsed_event_frame(12, workspace_id=None))
        with pytest.raises(ValueError, match="epoch"):
            relay._accept_source_frame(_parsed_event_frame(12, epoch=8))
        await relay.aclose()

        ordered_caller = OrchestrationEventCalling(
            "http://orchestration.example.test",
            None,
            5.0,
            httpx.MockTransport(lambda request: httpx.Response(200, request=request)),
        )
        ordered = realtime_sse.RealtimeStreamRelay(
            ordered_caller,
            httpx.Response(200, content=b""),
            UUID(_WORKSPACE_ID),
            None,
        )
        assert ordered._accept_source_frame(_parsed_event_frame(2)) is True
        with pytest.raises(ValueError, match="backwards"):
            ordered._accept_source_frame(_parsed_event_frame(1))
        await ordered.aclose()

    asyncio.run(exercise())


def test_workspace_sse_route_forwards_cursors_and_preserves_frames() -> None:
    captured: list[httpx.Request] = []
    stream = _TrackedEventStream(_sse_body())

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            status_code=200,
            headers={"content-type": "text/event-stream"},
            stream=stream,
            request=request,
        )

    with (
        GatewayTestClientBuilder().with_handler(handler).build_client() as client,
        client.stream(
            "GET",
            _EVENT_PATH,
            headers={
                "Authorization": "Bearer event-token",
                "Last-Event-ID": "007:0008",
                "X-Orchestration-Session-Id": _SESSION_ID,
            },
        ) as response,
    ):
        assert response.status_code == 200
        body = response.read()

    assert len(captured) == 1
    request = captured[0]
    assert request.url.path == _UPSTREAM_EVENT_PATH
    assert request.headers["authorization"] == "Bearer event-token"
    assert request.headers["last-event-id"] == "007:0008"
    assert request.headers["x-orchestration-session-id"] == _SESSION_ID
    assert request.headers["accept-encoding"] == "identity"
    assert b"id: 7:9\n" in body
    assert b"event: state_changed\n" in body
    assert b"event: resync_required\nretry: 2000\n" in body
    assert _EVENT_DATA["kind"].encode() in body
    assert stream.closed


def test_workspace_path_rejects_nil_and_noncanonical_ids_before_upstream() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            500, json={"code": "unexpected", "message": "sent", "retryable": False}
        )

    paths: dict[str, str] = {
        "nil workspace": "/orchestrations/workspaces/00000000-0000-0000-0000-000000000000/events",
        "noncanonical workspace": (
            "/orchestrations/workspaces/10000000-0000-0000-0000-00000000000A/events"
        ),
    }
    for path in paths.values():
        with GatewayTestClientBuilder().with_handler(handler).build_client() as client:
            response = client.get(path, headers={"Authorization": "Bearer event-token"})
        assert response.status_code == 422
    assert captured == []


def test_admission_errors_keep_status_body_and_retry_after() -> None:
    error_cases: dict[str, tuple[int, JsonObject, str | None, str | None]] = {
        "invalid cursor": (
            400,
            {"code": "INVALID_CURSOR", "message": "Malformed cursor", "retryable": False},
            None,
            "bad-cursor",
        ),
        "resync required": (
            409,
            {"code": "RESYNC_REQUIRED", "message": "Cursor expired", "retryable": True},
            None,
            "4:8",
        ),
        "subscriber bound": (
            503,
            {
                "code": "REALTIME_SUBSCRIBER_LIMIT",
                "message": "Retry later",
                "retryable": True,
            },
            "2",
            None,
        ),
    }
    for status_code, payload, retry_after, cursor in error_cases.values():
        headers = {"content-type": "application/json"}
        if retry_after is not None:
            headers["retry-after"] = retry_after
        captured: list[httpx.Request] = []
        handler = _admission_handler(status_code, payload, headers, captured)
        request_headers = {"Authorization": "Bearer event-token"}
        if cursor is not None:
            request_headers["Last-Event-ID"] = cursor
        with GatewayTestClientBuilder().with_handler(handler).build_client() as client:
            response = client.get(_EVENT_PATH, headers=request_headers)

        assert response.status_code == status_code
        assert response.json() == payload
        assert response.headers.get("retry-after") == retry_after
        assert len(captured) == 1
        assert captured[0].headers.get("last-event-id") == cursor


def test_compressed_upstream_stream_is_rejected_before_streaming() -> None:
    stream = _TrackedEventStream(_sse_body())

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "text/event-stream",
                "content-encoding": "gzip",
            },
            stream=stream,
            request=request,
        )

    with GatewayTestClientBuilder().with_handler(handler).build_client() as client:
        response = client.get(_EVENT_PATH, headers={"Authorization": "Bearer event-token"})

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_unsupported_content_encoding"
    assert response.json()["workspace_id"] == _WORKSPACE_ID
    assert not stream.started
    assert stream.closed


def test_encoded_source_admission_error_is_rejected_before_body_read() -> None:
    stream = _TrackedEventStream(
        encode_json(
            {
                "code": "INVALID_CURSOR",
                "message": "Malformed cursor",
                "retryable": False,
            }
        )
    )

    def handler(request: httpx.Request) -> httpx.Response:
        response = httpx.Response(
            400,
            headers={
                "content-type": "application/json",
                "content-encoding": "gzip",
            },
            stream=stream,
            request=request,
        )
        return response

    with GatewayTestClientBuilder().with_handler(handler).build_client() as client:
        response = client.get(
            _EVENT_PATH,
            headers={
                "Authorization": "Bearer event-token",
                "Last-Event-ID": "bad-cursor",
            },
        )

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_unsupported_content_encoding"
    assert not stream.started
    assert stream.closed


def test_asgi_send_timeout_closes_open_source_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def verify() -> tuple[bool, bool]:
        first_event = _source_event_frame(9)
        event_body = first_event + b":" + b"x" * (4_096 - len(first_event) - 3) + b"\n\n"
        assert len(event_body) == 4_096
        source_stream = _BlockingEventStream(event_body)

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                stream=source_stream,
                request=request,
            )

        caller = OrchestrationEventCalling(
            "http://orchestration.example.test",
            "Bearer event-token",
            5.0,
            httpx.MockTransport(handler),
        )
        response = await open_realtime_stream(caller, UUID(_WORKSPACE_ID), None, None)
        stream_started = asyncio.Event()

        async def receive() -> RealtimeAsgiMessage:
            await asyncio.Event().wait()
            return {"type": "http.disconnect"}

        send_count = 0

        async def send(message: RealtimeAsgiMessage) -> None:
            nonlocal send_count
            send_count += 1
            if send_count == 1:
                return
            stream_started.set()
            await asyncio.wait_for(source_stream.waiting_for_source.wait(), timeout=1.0)
            await asyncio.Event().wait()

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": _EVENT_PATH,
            "raw_path": _EVENT_PATH.encode(),
            "query_string": b"",
            "headers": [],
            "server": ("127.0.0.1", 7979),
            "client": ("127.0.0.1", 12345),
        }
        monkeypatch.setattr(realtime_sse, "REALTIME_SEND_TIMEOUT_MS", 10)
        with pytest.raises(ClientDisconnect):
            await response(scope, receive, send)
        assert response._relay._last_delivered_sequence == 0
        pending_pumps = tuple(
            task
            for task in asyncio.all_tasks()
            if task.get_name() == "orchestration-realtime-source-pump" and not task.done()
        )
        assert not pending_pumps
        return (
            stream_started.is_set() and source_stream.waiting_for_source.is_set(),
            source_stream.cancelled and source_stream.closed,
        )

    assert asyncio.run(verify()) == (True, True)
