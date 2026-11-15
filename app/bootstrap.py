"""Gateway composition root wiring Dishka DI, routers, exceptions, and lifespan."""

import sys
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider, setup_dishka
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.forge.routers.forge_router import router as forge_router
from app.forge.schema.get_forge import GetForgeResponse
from app.mixed_module.routers.mixed_module_router import router as mixed_module_router
from app.orchestration.routers.orchestration_router import router as orchestration_router
from app.orchestration.schema.get_orchestration import GetOrchestrationResponse
from app.shared.api_calling_box.base_calling import provide_http_client
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.base_schema import LivenessResponse
from app.shared.diagnostics.diagnostics_router import create_diagnostics_router
from app.shared.diagnostics.request_trace import ContractName, TraceStore
from app.shared.exception import BaseExcept, ForgeExcept, OrchestrationExcept
from app.shared.settings_modules.forge_settings import ForgeSettings
from app.shared.settings_modules.gateway_settings import (
    GatewayRuntimeSettings,
    GatewaySettings,
)
from app.shared.settings_modules.orchestration_settings import OrchestrationSettings


class SharedProvider(Provider):
    """Dishka provider for shared settings, pooled HTTP client, trace store, and callers."""

    def __init__(self, settings: GatewaySettings) -> None:
        """Bind validated gateway configuration into the provider.

        Args:
            settings: Explicit GatewaySettings configuration.
        Return:
            None.
        """
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def provide_settings(self) -> GatewaySettings:
        """Provide immutable composed gateway configuration.

        Args:
            None.
        Return:
            Bound GatewaySettings instance.
        """
        result = self._settings
        return result

    @provide(scope=Scope.APP)
    def provide_forge_settings(self) -> ForgeSettings:
        """Provide immutable Forge module configuration.

        Args:
            None.
        Return:
            Bound ForgeSettings instance.
        """
        result = self._settings.forge
        return result

    @provide(scope=Scope.APP)
    def provide_orchestration_settings(self) -> OrchestrationSettings:
        """Provide immutable Orchestration module configuration.

        Args:
            None.
        Return:
            Bound OrchestrationSettings instance.
        """
        result = self._settings.orchestration
        return result

    @provide(scope=Scope.APP)
    def provide_runtime_settings(self) -> GatewayRuntimeSettings:
        """Provide immutable gateway runtime policy settings.

        Args:
            None.
        Return:
            Bound GatewayRuntimeSettings instance.
        """
        result = self._settings.runtime
        return result

    @provide(scope=Scope.APP)
    async def provide_client(
        self,
        runtime_settings: GatewayRuntimeSettings,
    ) -> AsyncIterator[httpx.AsyncClient]:
        """Provide the bounded asynchronous HTTP client shared across requests.

        Args:
            runtime_settings: Bound GatewayRuntimeSettings supplying timeout and pool bounds.
        Return:
            Async iterator yielding and closing the shared httpx.AsyncClient.
        """
        async for client in provide_http_client(
            runtime_settings.http_timeout_seconds,
            runtime_settings.max_connections,
            runtime_settings.max_keepalive_connections,
        ):
            yield client

    @provide(scope=Scope.APP)
    def provide_trace_store(self, runtime_settings: GatewayRuntimeSettings) -> TraceStore:
        """Provide bounded in-memory request trace storage.

        Args:
            runtime_settings: Bound GatewayRuntimeSettings supplying trace retention capacity.
        Return:
            Initialized TraceStore instance.
        """
        store = TraceStore(capacity=runtime_settings.trace_capacity)
        return store

    @provide(scope=Scope.REQUEST)
    def provide_forge_calling(
        self,
        client: httpx.AsyncClient,
        forge_settings: ForgeSettings,
    ) -> ForgeCalling:
        """Provide a request-scoped Forge upstream caller.

        Args:
            client: Shared bounded asynchronous HTTP client.
            forge_settings: Bound ForgeSettings supplying the Forge base URL.
        Return:
            Configured ForgeCalling instance.
        """
        caller = ForgeCalling(client, forge_settings.forge_base_url)
        return caller

    @provide(scope=Scope.REQUEST)
    def provide_orchestration_calling(
        self,
        client: httpx.AsyncClient,
        orchestration_settings: OrchestrationSettings,
    ) -> OrchestrationCalling:
        """Provide a request-scoped Orchestration upstream caller.

        Args:
            client: Shared bounded asynchronous HTTP client.
            orchestration_settings: Bound OrchestrationSettings supplying the base URL.
        Return:
            Configured OrchestrationCalling instance.
        """
        caller = OrchestrationCalling(client, orchestration_settings.orchestration_base_url)
        return caller


def _assert_no_gil() -> None:
    if sys._is_gil_enabled():
        raise RuntimeError("heterarchy-gateway requires free-threaded Python (no-GIL)")


async def _handle_forge_exception(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, ForgeExcept):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_forge_error_response().model_dump(mode="json"),
    )


async def _handle_orchestration_exception(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, OrchestrationExcept):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_orchestration_error_response().model_dump(mode="json"),
    )


async def _handle_base_exception(_request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, BaseExcept):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_error_response().model_dump(mode="json"),
    )


def create_app(
    settings: GatewaySettings | None = None,
    *,
    container: AsyncContainer | None = None,
) -> FastAPI:
    """Build and wire the FastAPI gateway application with Dishka dependency injection.

    Args:
        settings: Explicit gateway configuration; loaded from env when invoked as uvicorn factory.
        container: Optional pre-built Dishka AsyncContainer for tests or custom bindings.
    Return:
        Configured FastAPI application instance.
    """
    resolved_settings = settings if settings is not None else GatewaySettings.from_env()
    app_container = (
        container
        if container is not None
        else make_async_container(SharedProvider(resolved_settings), FastapiProvider())
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        _assert_no_gil()
        try:
            yield
        finally:
            await app_container.close()

    fastapi_app = FastAPI(title="Heterarchy Gateway BFF", lifespan=lifespan)
    fastapi_app.add_exception_handler(ForgeExcept, _handle_forge_exception)
    fastapi_app.add_exception_handler(OrchestrationExcept, _handle_orchestration_exception)
    fastapi_app.add_exception_handler(BaseExcept, _handle_base_exception)

    @fastapi_app.get("/healthz", response_model=LivenessResponse)
    async def healthz_route() -> LivenessResponse:
        return LivenessResponse(status="alive", request_id=str(uuid4()))

    fastapi_app.include_router(forge_router)
    fastapi_app.include_router(orchestration_router)
    fastapi_app.include_router(mixed_module_router)
    fastapi_app.include_router(
        create_diagnostics_router(
            {
                ContractName.FORGE: GetForgeResponse,
                ContractName.ORCHESTRATION: GetOrchestrationResponse,
            },
        ),
    )
    setup_dishka(app_container, fastapi_app)
    return fastapi_app
