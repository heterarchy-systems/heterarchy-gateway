import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.bootstrap import create_app
from app.shared.ingredient_element.gateway.settings_module_enums import SettingsModule
from tests.shared.module_env_builder import MODULE_ENV_PAYLOADS, ModuleEnvWorkspaceBuilder


def test_app_boots_across_env_modes_without_gil(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    process_env = (
        MODULE_ENV_PAYLOADS[SettingsModule.FORGE]
        | MODULE_ENV_PAYLOADS[SettingsModule.ORCHESTRATION]
        | MODULE_ENV_PAYLOADS[SettingsModule.GATEWAY]
    )
    boot_modes: dict[str, ModuleEnvWorkspaceBuilder] = {
        "process_env": ModuleEnvWorkspaceBuilder(monkeypatch, tmp_path / "proc").with_process_env(
            process_env,
        ),
        "module_env_files": ModuleEnvWorkspaceBuilder(
            monkeypatch,
            tmp_path / "files",
        ).with_all_modules(),
    }

    assert not sys._is_gil_enabled()
    for builder in boot_modes.values():
        builder.apply()
        if "GATEWAY_FORGE_BASE_URL" not in os.environ:
            assert list((Path.cwd() / "module_setting_envs").glob("*_settings.env"))
        with TestClient(create_app()) as client:
            response = client.get("/healthz")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "alive"
        assert isinstance(payload["request_id"], str)
        assert len(payload["request_id"]) > 0
