"""Immutable gateway runtime, server, and composed settings modules."""

from typing import Annotated

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.gateway.settings_module_enums import SettingsModule
from app.shared.settings_modules.base_settings import settings_model_config
from app.shared.settings_modules.forge_settings import ForgeSettings
from app.shared.settings_modules.orchestration_settings import OrchestrationSettings


class GatewayRuntimeSettings(BaseSettings):
    """Gateway HTTP pool, diagnostics, and simulation policy from gateway_settings.env."""

    model_config = settings_model_config(
        env_prefix="GATEWAY_",
        module_name=SettingsModule.GATEWAY,
    )

    failure_simulation_enabled: Annotated[
        bool,
        Field(description="Allow X-BFF-Failure simulation headers when explicitly enabled."),
    ]
    http_timeout_seconds: Annotated[
        float,
        Field(description="Default outbound HTTP request timeout in seconds.", gt=0.0, le=120.0),
    ]
    max_connections: Annotated[
        int,
        Field(description="Maximum pooled outbound HTTP connections.", ge=1, le=1000),
    ]
    max_keepalive_connections: Annotated[
        int,
        Field(description="Maximum kept-alive outbound HTTP connections.", ge=0, le=500),
    ]
    trace_capacity: Annotated[
        int,
        Field(description="Maximum retained in-memory diagnostic trace snapshots.", ge=1, le=10000),
    ]

    @model_validator(mode="after")
    def validate_gateway_connection_pool(self) -> GatewayRuntimeSettings:
        """Verify that keepalive connections never exceed total pooled connections.

        Args:
            None.
        Return:
            Validated GatewayRuntimeSettings instance.
        """
        if self.max_keepalive_connections > self.max_connections:
            raise ValueError("max_keepalive_connections cannot exceed max_connections")
        result = self
        return result


class GatewayServerSettings(BaseSettings):
    """Standalone uvicorn bind address loaded from gateway_settings.env."""

    model_config = settings_model_config(
        env_prefix="GATEWAY_",
        module_name=SettingsModule.GATEWAY,
    )

    host: Annotated[
        str,
        Field(description="Bind host for standalone uvicorn execution."),
    ]
    port: Annotated[
        int,
        Field(description="Bind port for standalone uvicorn execution.", ge=1, le=65535),
    ]

    @field_validator("host")
    @classmethod
    def validate_gateway_server_host(cls, value: str) -> str:
        """Ensure the configured uvicorn bind host is non-empty.

        Args:
            value: Raw host value from settings or environment.
        Return:
            Stripped non-empty host string.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("Gateway bind host must not be blank")
        return normalized


class GatewaySettings(StrictSchemaModel):
    """Composed immutable BFF configuration combining module settings."""

    forge: Annotated[
        ForgeSettings,
        Field(description="Forge backend configuration."),
    ]
    orchestration: Annotated[
        OrchestrationSettings,
        Field(description="Orchestration backend configuration."),
    ]
    runtime: Annotated[
        GatewayRuntimeSettings,
        Field(description="Gateway HTTP pool, diagnostics, and simulation policy."),
    ]

    @classmethod
    def from_env(cls) -> GatewaySettings:
        """Load each module settings class from its own module env source and process env.

        Args:
            None.
        Return:
            Validated GatewaySettings instance combining all module settings.
        """
        result = cls(
            forge=ForgeSettings(),
            orchestration=OrchestrationSettings(),
            runtime=GatewayRuntimeSettings(),
        )
        return result
