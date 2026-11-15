"""Typed builders and mock transport providers for Gateway HTTP route tests."""

from collections.abc import AsyncIterator, Callable
from typing import Self

import httpx
from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from fastapi.testclient import TestClient

from app.bootstrap import SharedProvider, create_app
from app.shared.settings_modules.forge_settings import ForgeSettings
from app.shared.settings_modules.gateway_settings import (
    GatewayRuntimeSettings,
    GatewayServerSettings,
    GatewaySettings,
)
from app.shared.settings_modules.orchestration_settings import OrchestrationSettings
from app.shared.types.base_types import JsonValue

type RequestHandler = Callable[[httpx.Request], httpx.Response]
type RouteResponseTable = dict[tuple[str, str], tuple[int, JsonValue]]


def _default_handler(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(404, json={"detail": "not found"})


class _MockHttpProvider(Provider):
    def __init__(self, handler: RequestHandler) -> None:
        super().__init__()
        self._handler = handler

    @provide(scope=Scope.APP)
    async def provide_client(self) -> AsyncIterator[httpx.AsyncClient]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(self._handler),
            timeout=httpx.Timeout(5.0),
        ) as client:
            yield client


class GatewaySettingsBuilder:
    """Fluent builder producing validated module and composed Gateway settings."""

    def __init__(self) -> None:
        self._forge_base_url = "https://forge.example.test/api/v1"
        self._orchestration_base_url = "https://orchestration.example.test/api/v1"
        self._failure_simulation_enabled = False
        self._http_timeout_seconds = 5.0
        self._max_connections = 20
        self._max_keepalive_connections = 5
        self._trace_capacity = 50
        self._host = "127.0.0.1"
        self._port = 8799

    def with_forge_base_url(self, value: str) -> Self:
        self._forge_base_url = value
        return self

    def with_orchestration_base_url(self, value: str) -> Self:
        self._orchestration_base_url = value
        return self

    def with_failure_simulation(self, *, enabled: bool) -> Self:
        self._failure_simulation_enabled = enabled
        return self

    def with_connection_pool(self, *, max_connections: int, max_keepalive: int) -> Self:
        self._max_connections = max_connections
        self._max_keepalive_connections = max_keepalive
        return self

    def with_host(self, host: str) -> Self:
        self._host = host
        return self

    def build_forge(self) -> ForgeSettings:
        return ForgeSettings(_env_file=None, forge_base_url=self._forge_base_url)

    def build_orchestration(self) -> OrchestrationSettings:
        return OrchestrationSettings(
            _env_file=None,
            orchestration_base_url=self._orchestration_base_url,
        )

    def build_runtime(self) -> GatewayRuntimeSettings:
        return GatewayRuntimeSettings(
            _env_file=None,
            failure_simulation_enabled=self._failure_simulation_enabled,
            http_timeout_seconds=self._http_timeout_seconds,
            max_connections=self._max_connections,
            max_keepalive_connections=self._max_keepalive_connections,
            trace_capacity=self._trace_capacity,
        )

    def build_server(self) -> GatewayServerSettings:
        return GatewayServerSettings(_env_file=None, host=self._host, port=self._port)

    def build(self) -> GatewaySettings:
        return GatewaySettings(
            forge=self.build_forge(),
            orchestration=self.build_orchestration(),
            runtime=self.build_runtime(),
        )


class GatewayTestClientBuilder:
    """Fluent builder assembling Dishka containers and FastAPI TestClients."""

    def __init__(self) -> None:
        self._settings_builder = GatewaySettingsBuilder()
        self._handler: RequestHandler = _default_handler

    def with_failure_simulation(self, *, enabled: bool) -> Self:
        self._settings_builder.with_failure_simulation(enabled=enabled)
        return self

    def with_handler(self, handler: RequestHandler) -> Self:
        self._handler = handler
        return self

    def with_route_table(
        self,
        routes: RouteResponseTable,
        *,
        on_match: Callable[[httpx.Request], None] | None = None,
    ) -> Self:
        def handler(request: httpx.Request) -> httpx.Response:
            matched = routes.get((request.method, request.url.path))
            if matched is None:
                return httpx.Response(404, json={"detail": "not found"})
            if on_match is not None:
                on_match(request)
            status_code, payload = matched
            return httpx.Response(status_code, json=payload)

        self._handler = handler
        return self

    def build_client(self) -> TestClient:
        settings = self._settings_builder.build()
        container = make_async_container(
            SharedProvider(settings),
            _MockHttpProvider(self._handler),
            FastapiProvider(),
        )
        return TestClient(create_app(settings, container=container))
