"""Builder and canonical env dictionaries for module_setting_envs tests."""

import os
from pathlib import Path
from typing import Self

import pytest

from app.shared.ingredient_element.gateway.settings_module_enums import SettingsModule

MODULE_ENV_PAYLOADS: dict[SettingsModule, dict[str, str]] = {
    SettingsModule.FORGE: {
        "GATEWAY_FORGE_BASE_URL": "https://forge.example.test/api/v1",
    },
    SettingsModule.ORCHESTRATION: {
        "GATEWAY_ORCHESTRATION_BASE_URL": "https://orchestration.example.test",
    },
    SettingsModule.GATEWAY: {
        "GATEWAY_FAILURE_SIMULATION_ENABLED": "false",
        "GATEWAY_HTTP_TIMEOUT_SECONDS": "10.0",
        "GATEWAY_MAX_CONNECTIONS": "100",
        "GATEWAY_MAX_KEEPALIVE_CONNECTIONS": "20",
        "GATEWAY_TRACE_CAPACITY": "500",
        "GATEWAY_HOST": "127.0.0.1",
        "GATEWAY_PORT": "7979",
    },
}


class ModuleEnvWorkspaceBuilder:
    """Fluent builder constructing isolated module_setting_envs and process env state."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
        self._monkeypatch = monkeypatch
        self._root = root
        self._module_files: dict[SettingsModule, dict[str, str]] = {}
        self._dotenv_values: dict[str, str] | None = None
        self._process_env: dict[str, str] = {}

    def with_module_env(
        self,
        module: SettingsModule,
        values: dict[str, str] | None = None,
    ) -> Self:
        base_values = MODULE_ENV_PAYLOADS[module]
        self._module_files[module] = dict(base_values) if values is None else values
        return self

    def with_all_modules(self) -> Self:
        for module in SettingsModule:
            self.with_module_env(module)
        return self

    def with_legacy_dotenv(self, values: dict[str, str]) -> Self:
        self._dotenv_values = dict(values)
        return self

    def with_process_env(self, values: dict[str, str]) -> Self:
        self._process_env.update(values)
        return self

    def apply(self) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        self._monkeypatch.setattr(os, "environ", {})
        self._monkeypatch.chdir(self._root)
        for module, values in self._module_files.items():
            env_path = self._root / "module_setting_envs" / f"{module}_settings.env"
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text(
                "".join(f"{key}={value}\n" for key, value in values.items()),
                encoding="utf-8",
            )
        if self._dotenv_values is not None:
            (self._root / ".env").write_text(
                "".join(f"{key}={value}\n" for key, value in self._dotenv_values.items()),
                encoding="utf-8",
            )
        for key, value in self._process_env.items():
            self._monkeypatch.setenv(key, value)
        return self._root
