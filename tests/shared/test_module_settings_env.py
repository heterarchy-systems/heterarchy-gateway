"""Module env-file routing, isolation, example parity, and precedence contracts."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.shared.ingredient_element.gateway.settings_module_enums import SettingsModule
from app.shared.settings_modules.forge_settings import ForgeSettings
from app.shared.settings_modules.gateway_settings import (
    GatewayRuntimeSettings,
    GatewayServerSettings,
    GatewaySettings,
)
from app.shared.settings_modules.orchestration_settings import OrchestrationSettings
from tests.shared.module_env_builder import MODULE_ENV_PAYLOADS, ModuleEnvWorkspaceBuilder

type SettingsModelClass = (
    type[ForgeSettings]
    | type[OrchestrationSettings]
    | type[GatewayRuntimeSettings]
    | type[GatewayServerSettings]
)

_ENV_DIR = Path(__file__).resolve().parents[2] / "module_setting_envs"


def _parse_example_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, _separator, _value = line.partition("=")
        keys.add(key.strip())
    return keys


def test_module_settings_isolation_and_process_env_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Each module reads only its own env file and process env overrides files."""
    (
        ModuleEnvWorkspaceBuilder(monkeypatch, tmp_path)
        .with_module_env(
            SettingsModule.FORGE,
            MODULE_ENV_PAYLOADS[SettingsModule.FORGE]
            | {
                "GATEWAY_ORCHESTRATION_BASE_URL": "https://wrong-sibling.example.test",
                "GATEWAY_TRACE_CAPACITY": "9999",
            },
        )
        .with_module_env(
            SettingsModule.ORCHESTRATION,
            MODULE_ENV_PAYLOADS[SettingsModule.ORCHESTRATION]
            | {"GATEWAY_FORGE_BASE_URL": "https://wrong-sibling.example.test"},
        )
        .with_module_env(
            SettingsModule.GATEWAY,
            MODULE_ENV_PAYLOADS[SettingsModule.GATEWAY]
            | {"GATEWAY_FORGE_BASE_URL": "https://wrong-sibling.example.test"},
        )
        .with_process_env({"GATEWAY_TRACE_CAPACITY": "900"})
        .apply()
    )

    composed = GatewaySettings.from_env()
    server = GatewayServerSettings()

    assert composed.forge.forge_base_url == "https://forge.example.test/api/v1"
    assert (
        composed.orchestration.orchestration_base_url == "https://orchestration.example.test/api/v1"
    )
    assert composed.runtime.trace_capacity == 900
    assert server.host == "127.0.0.1"
    assert server.port == 8799


def test_legacy_dotenv_and_sibling_files_do_not_satisfy_missing_module_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Root .env and sibling feature files cannot satisfy a missing module file."""
    foreign_payload = (
        MODULE_ENV_PAYLOADS[SettingsModule.FORGE]
        | MODULE_ENV_PAYLOADS[SettingsModule.ORCHESTRATION]
        | MODULE_ENV_PAYLOADS[SettingsModule.GATEWAY]
    )
    (
        ModuleEnvWorkspaceBuilder(monkeypatch, tmp_path)
        .with_legacy_dotenv(foreign_payload)
        .with_module_env(SettingsModule.ORCHESTRATION, foreign_payload)
        .apply()
    )

    monkeypatch.setitem(
        ForgeSettings.model_config,
        "env_file",
        (tmp_path / "module_setting_envs" / "forge_settings.env",),
    )
    monkeypatch.setitem(
        GatewayRuntimeSettings.model_config,
        "env_file",
        (tmp_path / "module_setting_envs" / "gateway_settings.env",),
    )

    for model in (ForgeSettings, GatewayRuntimeSettings):
        with pytest.raises(ValidationError):
            model()


def test_module_env_examples_cover_exact_schema_fields_and_load(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Committed *_settings.env.example templates match their settings schemas exactly."""
    monkeypatch.setattr(os, "environ", {})

    module_models: dict[SettingsModule, tuple[SettingsModelClass, ...]] = {
        SettingsModule.FORGE: (ForgeSettings,),
        SettingsModule.ORCHESTRATION: (OrchestrationSettings,),
        SettingsModule.GATEWAY: (GatewayRuntimeSettings, GatewayServerSettings),
    }

    for module, models in module_models.items():
        example_path = _ENV_DIR / f"{module}_settings.env.example"
        assert example_path.is_file()
        expected_keys: set[str] = set()
        for model in models:
            assert all(
                field.is_required() and field.default_factory is None
                for field in model.model_fields.values()
            )
            expected_keys.update(f"GATEWAY_{name.upper()}" for name in model.model_fields)
            temp_env = tmp_path / f"{module}_settings.env"
            temp_env.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
            monkeypatch.setitem(model.model_config, "env_file", (temp_env,))
            model()

        assert _parse_example_keys(example_path) == expected_keys
