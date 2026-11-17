from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, ClassVar
from uuid import UUID

import pytest
from pydantic import Field, ValidationError

from app.shared.base_schema import StrictRootSchemaModel, StrictSchemaModel
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
        "forge_wrong_api_path": lambda: (
            GatewaySettingsBuilder()
            .with_forge_base_url("https://forge.example.test/api/v2")
            .build()
        ),
        "forge_encoded_api_path": lambda: (
            GatewaySettingsBuilder()
            .with_forge_base_url("https://forge.example.test/api%2Fv1")
            .build()
        ),
        "orchestration_bad_scheme": lambda: (
            GatewaySettingsBuilder()
            .with_orchestration_base_url("ftp://orchestration.example.test/api/v1")
            .build()
        ),
        "orchestration_wrong_api_path": lambda: (
            GatewaySettingsBuilder()
            .with_orchestration_base_url("https://orchestration.example.test/api/v1")
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


def test_exception_response_contracts_preserve_correlations() -> None:
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
    orchestration_error = OrchestrationExcept(
        502,
        "orchestration_down",
        "Orchestration failed",
        retryable=False,
        workspace_id=correlation_id,
    ).to_orchestration_error_response()
    assert forge_error.request_id == correlation_id
    assert orchestration_error.workspace_id == correlation_id


def test_strict_schema_model_parses_json_datetime_and_rejects_default_factory() -> None:
    class TimedSchema(StrictSchemaModel):
        created_at: Annotated[datetime, Field(description="Source creation timestamp.")]

    parsed = TimedSchema.model_validate_json('{"created_at":"2026-09-28T09:30:00Z"}')
    assert parsed.created_at == datetime(2026, 9, 28, 9, 30, 0, tzinfo=UTC)

    with pytest.raises(TypeError):

        class InvalidFactorySchema(StrictSchemaModel):
            items: list[str] = Field(default_factory=list)

    class RequiredNullableSchema(StrictSchemaModel):
        nullable_value: Annotated[str | None, Field(description="Required nullable value.")]

    assert RequiredNullableSchema.model_validate({"nullable_value": None}).nullable_value is None
    with pytest.raises(ValidationError):
        RequiredNullableSchema.model_validate({})

    with pytest.raises(TypeError):

        class InvalidNullableDefaultSchema(StrictSchemaModel):
            nullable_value: Annotated[
                str | None,
                Field(description="Nullable value with a prohibited implicit default."),
            ] = None

    with pytest.raises(TypeError):

        class MarkerCannotBypassDefaultSchema(StrictSchemaModel):
            _ALLOW_QUERY_OMISSION: ClassVar[bool] = True
            nullable_value: Annotated[
                str | None,
                Field(description="Ordinary schema field with a prohibited implicit default."),
            ] = None

    with pytest.raises(TypeError):

        class InvalidRootDefaultSchema(StrictRootSchemaModel[str | None]):
            root: Annotated[str | None, Field(description="Required nullable root value.")] = None
