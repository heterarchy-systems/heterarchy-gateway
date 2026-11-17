"""Request-owned Orchestration event transport contract tests."""

from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import pytest

from app.shared.api_calling_box.orchestration_event_calling import (
    OrchestrationEventCalling,
)

_WORKSPACE_ID = "10000000-0000-0000-0000-000000000001"


class _TrackedEventStream(httpx.AsyncByteStream):
    """One response stream that records whether its owner closed it."""

    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield one event frame if the response body is consumed.

        Args:
            None.
        Return:
            Asynchronous event-stream bytes.
        """
        yield b":keep-alive\n\n"

    async def aclose(self) -> None:
        """Record the response stream close.

        Args:
            None.
        Return:
            None.
        """
        self.closed = True


@pytest.mark.asyncio
async def test_event_transport_forwards_scope_and_owns_close_lifecycle() -> None:
    requests: list[httpx.Request] = []
    stream = _TrackedEventStream()

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=stream,
            request=request,
        )

    caller = OrchestrationEventCalling(
        "http://orchestration.example.test",
        "Bearer event-token",
        10.0,
        httpx.MockTransport(handler),
    )
    response = await caller.open_events(
        UUID(_WORKSPACE_ID),
        "123:45",
        "20000000-0000-0000-0000-000000000002",
    )

    assert response.status_code == 200
    assert response.is_closed is False
    assert len(requests) == 1
    request = requests[0]
    assert request.url.path == f"/v1/workspaces/{_WORKSPACE_ID}/events"
    assert request.headers["authorization"] == "Bearer event-token"
    assert request.headers["last-event-id"] == "123:45"
    assert request.headers["x-orchestration-session-id"] == ("20000000-0000-0000-0000-000000000002")
    assert request.headers["accept"] == "text/event-stream"
    assert request.headers["accept-encoding"] == "identity"

    await caller.aclose()
    await caller.aclose()
    assert response.is_closed is True
    assert stream.closed is True


@pytest.mark.asyncio
async def test_event_transport_closes_its_client_when_open_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("unavailable", request=request)

    caller = OrchestrationEventCalling(
        "http://orchestration.example.test",
        None,
        10.0,
        httpx.MockTransport(handler),
    )

    with pytest.raises(httpx.ConnectError):
        await caller.open_events(
            UUID(_WORKSPACE_ID),
            None,
            None,
        )

    await caller.aclose()
