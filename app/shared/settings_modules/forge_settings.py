"""Immutable Forge module configuration read from forge_settings.env."""

from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

from app.shared.ingredient_element.gateway.settings_module_enums import SettingsModule
from app.shared.settings_modules.base_settings import (
    settings_model_config,
    validate_backend_origin,
)


class ForgeSettings(BaseSettings):
    """Forge upstream settings with explicit required fields."""

    model_config = settings_model_config(
        env_prefix="GATEWAY_",
        module_name=SettingsModule.FORGE,
    )

    forge_base_url: Annotated[
        str,
        Field(description="Base URL for the upstream Forge backend."),
    ]

    @field_validator("forge_base_url")
    @classmethod
    def validate_forge_base_url(cls, value: str) -> str:
        """Normalize and validate the upstream Forge base URL.

        Args:
            value: Raw Forge base URL from settings or environment.
        Return:
            Validated normalized URL string.
        """
        result = validate_backend_origin(value)
        return result
