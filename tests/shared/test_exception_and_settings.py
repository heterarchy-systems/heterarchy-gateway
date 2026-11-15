from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import httpx
import pytest
from pydantic import Field, ValidationError

from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.base_schema import StrictSchemaModel
from app.shared.exception import (
    ForgeErrorResponse,
    ForgeExcept,
    OrchestrationErrorResponse,
    OrchestrationExcept,
)
from app.shared.settings_modules.forge_settings import ForgeSettings
from app.shared.settings_modules.gateway_settings import (
    GatewayRuntimeSettings,
    GatewayServerSettings,
    GatewaySettings,
)
from app.shared.settings_modules.orchestration_settings import OrchestrationSettings
from tests.shared.gateway_test_builder import GatewaySettingsBuilder


def test_settings_boundaries_reject_missing_and_invalid_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for env_key in (
        "GATEWAY_FORGE_BASE_URL",
        "GATEWAY_ORCHESTRATION_BASE_URL",
        "GATEWAY_FAILURE_SIMULATION_ENABLED",
        "GATEWAY_HTTP_TIMEOUT_SECONDS",
        "GATEWAY_MAX_CONNECTIONS",
        "GATEWAY_MAX_KEEPALIVE_CONNECTIONS",
        "GATEWAY_TRACE_CAPACITY",
        "GATEWAY_HOST",
        "GATEWAY_PORT",
    ):
        monkeypatch.delenv(env_key, raising=False)

    invalid_cases: dict[
        str,
        Callable[
            [],
            ForgeSettings
            | OrchestrationSettings
            | GatewayRuntimeSettings
            | GatewayServerSettings
            | GatewaySettings,
        ],
    ] = {
        "missing_forge": lambda: ForgeSettings(_env_file=None),
        "missing_orchestration": lambda: OrchestrationSettings(_env_file=None),
        "missing_runtime": lambda: GatewayRuntimeSettings(_env_file=None),
        "missing_server": lambda: GatewayServerSettings(_env_file=None),
        "empty_composed": lambda: GatewaySettings.model_validate({}),
        "forge_credentials_url": lambda: (
            GatewaySettingsBuilder()
            .with_forge_base_url("https://user:pass@forge.example.test/api/v1")
            .build()
        ),
        "orchestration_bad_scheme": lambda: (
            GatewaySettingsBuilder()
            .with_orchestration_base_url("ftp://orchestration.example.test/api/v1")
            .build()
        ),
        "keepalive_exceeds_pool": lambda: (
            GatewaySettingsBuilder()
            .with_connection_pool(max_connections=10, max_keepalive=20)
            .build()
        ),
        "blank_server_host": lambda: GatewaySettingsBuilder().with_host("   ").build_server(),
    }

    for builder in invalid_cases.values():
        with pytest.raises(ValidationError):
            builder()


@pytest.mark.asyncio
async def test_exception_contracts_and_calling_box_error_mapping() -> None:
    for model in (ForgeErrorResponse, OrchestrationErrorResponse):
        with pytest.raises(ValidationError):
            model.model_validate({"code": "fail", "message": "failed", "retryable": False})

    correlation_id = UUID("11111111-1111-1111-1111-111111111111")
    forge_error = ForgeExcept(
        502,
        "forge_down",
        "Forge failed",
        retryable=True,
        request_id=correlation_id,
    ).to_forge_error_response()
    orch_error = OrchestrationExcept(
        502,
        "orch_down",
        "Orchestration failed",
        retryable=False,
        workspace_id=correlation_id,
    ).to_orchestration_error_response()
    assert forge_error.request_id == correlation_id
    assert orch_error.workspace_id == correlation_id

    forge_responses: dict[str, httpx.Response] = {
        "/forges/missing": httpx.Response(404, json={"detail": "missing"}),
        "/forges/other": httpx.Response(500, json={"message": "boom"}),
    }

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: forge_responses[req.url.path]),
        timeout=httpx.Timeout(5.0),
    ) as forge_client:
        forge_calling = ForgeCalling(forge_client, "https://forge.example.test")
        forge_cases: dict[str, tuple[int, bool]] = {
            "missing": (404, False),
            "other": (502, True),
        }
        for forge_id, (expected_status, expected_retryable) in forge_cases.items():
            with pytest.raises(ForgeExcept) as exc_info:
                await forge_calling.fetch_forge(forge_id)
            assert exc_info.value.status_code == expected_status
            assert exc_info.value.retryable is expected_retryable

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _req: httpx.Response(200, content=b"{invalid json")),
        timeout=httpx.Timeout(5.0),
    ) as orch_client:
        orch_calling = OrchestrationCalling(orch_client, "https://orch.example.test")
        with pytest.raises(OrchestrationExcept) as invalid_json_exc:
            await orch_calling.fetch_task("task-1")
        assert invalid_json_exc.value.status_code == 502
        assert not invalid_json_exc.value.retryable


def test_strict_schema_model_parses_json_datetime_and_rejects_default_factory() -> None:
    class TimedSchema(StrictSchemaModel):
        created_at: datetime

    parsed = TimedSchema.model_validate_json('{"created_at":"2026-09-28T09:30:00Z"}')
    assert parsed.created_at == datetime(2026, 9, 28, 9, 30, 0, tzinfo=UTC)

    with pytest.raises(TypeError):

        class InvalidFactorySchema(StrictSchemaModel):
            items: list[str] = Field(default_factory=list)
