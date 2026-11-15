"""Shared pydantic-settings loading policy and backend-origin validation."""

from pathlib import Path

import httpx
from pydantic_settings import SettingsConfigDict

from app.shared.ingredient_element.gateway.settings_module_enums import SettingsModule


def settings_model_config(
    env_prefix: str,
    module_name: SettingsModule,
) -> SettingsConfigDict:
    """Build settings config for one module-owned env file and prefix.

    Args:
        env_prefix: Environment variable prefix such as ``GATEWAY_``.
        module_name: Module name without the ``_settings.env`` suffix.
    Return:
        SettingsConfigDict with checkout, parent, and cwd module env candidates.
    """
    filename = f"{module_name}_settings.env"
    env_candidates = (
        Path(__file__).resolve().parents[3] / "module_setting_envs" / filename,
        Path("..") / "module_setting_envs" / filename,
        Path("module_setting_envs") / filename,
    )
    return SettingsConfigDict(
        env_prefix=env_prefix,
        env_file=tuple(dict.fromkeys(env_candidates)),
        env_file_encoding="utf-8",
        env_parse_none_str="null",
        extra="ignore",
        frozen=True,
        hide_input_in_errors=True,
    )


def validate_backend_origin(value: str) -> str:
    """Validate that a configured backend base URL uses HTTP(S) without credentials.

    Args:
        value: Raw configured backend URL.
    Return:
        Validated URL string stripped of trailing slashes.
    """
    normalized = value.strip().rstrip("/")
    origin = httpx.URL(normalized)
    has_credentials = bool(origin.username or origin.password)
    has_query_or_fragment = bool(origin.query or origin.fragment)
    if origin.scheme not in {"http", "https"} or not origin.host:
        raise ValueError("Backend base URL must include an http(s) scheme and host")
    if has_credentials or has_query_or_fragment:
        raise ValueError("Backend base URL must not contain credentials, queries, or fragments")
    return normalized
