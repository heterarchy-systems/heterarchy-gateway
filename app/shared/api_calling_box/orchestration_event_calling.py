"""Request-owned transport for the Orchestration workspace event stream."""

from contextlib import AsyncExitStack
from uuid import UUID

import httpx

from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeCacheControlEnum,
    RealtimeContentEncodingEnum,
    RealtimeHeaderNameEnum,
    RealtimeMediaTypeEnum,
    RealtimeSourceReadTimeoutSecondsEnum,
)


class OrchestrationEventCalling:
    """Open one bounded, request-owned Orchestration SSE connection."""

    def __init__(
        self,
        base_url: str,
        authorization: str | None,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None,
    ) -> None:
        """Bind the origin, caller credential, runtime bound, and test transport.

        Args:
            base_url: Validated Orchestration origin without an API prefix.
            authorization: Request-scoped bearer value for Orchestration.
            timeout_seconds: Runtime bound for connection, write, and pool phases.
            transport: Optional transport used by loopback contract tests.
        Return:
            None.
        """
        self._base_url = base_url.rstrip("/")
        self._authorization = authorization
        self._timeout_seconds = timeout_seconds
        self._transport = transport
        self._resources = AsyncExitStack()
        self._opened = False

    @staticmethod
    def _build_request_headers(
        authorization: str | None,
        last_event_id: str | None,
        session_id: str | None,
    ) -> httpx.Headers:
        """Build caller-owned headers for one workspace subscription.

        Args:
            authorization: Request-scoped bearer value for Orchestration.
            last_event_id: Optional source resume cursor to forward unchanged.
            session_id: Optional source workspace-read selector to forward unchanged.
        Return:
            Headers isolated to this event-stream request.
        """
        fixed_headers = (
            (RealtimeHeaderNameEnum.ACCEPT.value, RealtimeMediaTypeEnum.EVENT_STREAM.value),
            (
                RealtimeHeaderNameEnum.ACCEPT_ENCODING.value,
                RealtimeContentEncodingEnum.IDENTITY.value,
            ),
            (
                RealtimeHeaderNameEnum.CACHE_CONTROL.value,
                RealtimeCacheControlEnum.NO_CACHE.value,
            ),
        )
        headers = httpx.Headers(fixed_headers)
        optional_headers = (
            (RealtimeHeaderNameEnum.AUTHORIZATION, authorization),
            (RealtimeHeaderNameEnum.LAST_EVENT_ID, last_event_id),
            (RealtimeHeaderNameEnum.SESSION_ID, session_id),
        )
        for name, value in optional_headers:
            if value is not None:
                headers[name.value] = value
        result = headers
        return result

    async def open_events(
        self,
        workspace_id: UUID,
        last_event_id: str | None,
        session_id: str | None,
    ) -> httpx.Response:
        """Open the source response before the Gateway starts SSE headers.

        Args:
            workspace_id: Workspace scope selected by the Gateway route.
            last_event_id: Optional source cursor selected by the caller.
            session_id: Optional source workspace-read selector.
        Return:
            Open upstream response whose body is consumed by the Gateway stream.
        """
        if self._opened:
            raise RuntimeError("Orchestration event caller can open only one stream")
        self._opened = True
        timeout = httpx.Timeout(
            connect=self._timeout_seconds,
            read=RealtimeSourceReadTimeoutSecondsEnum.IDLE_TIMEOUT_SECONDS,
            write=self._timeout_seconds,
            pool=self._timeout_seconds,
        )
        limits = httpx.Limits(max_connections=1, max_keepalive_connections=0)
        client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            transport=self._transport,
            trust_env=False,
            follow_redirects=False,
        )
        try:
            await self._resources.enter_async_context(client)
            request = client.build_request(
                "GET",
                f"{self._base_url}/v1/workspaces/{workspace_id}/events",
                headers=self._build_request_headers(
                    authorization=self._authorization,
                    last_event_id=last_event_id,
                    session_id=session_id,
                ),
            )
            response = await client.send(request, stream=True, auth=None)
            self._resources.push_async_callback(response.aclose)
        except BaseException:
            await self.aclose()
            raise
        result = response
        return result

    async def aclose(self) -> None:
        """Close the active source response and its dedicated HTTP client once.

        Args:
            None.
        Return:
            None.
        """
        await self._resources.aclose()
