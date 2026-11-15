# Module settings

Each `{module}_settings.env` file belongs to its corresponding module under `app/shared/settings_modules/`:

| File | Configuration |
| --- | --- |
| `gateway_settings.env` | Gateway runtime resource/simulation policy (`GatewayRuntimeSettings`) and standalone server bind host/port (`GatewayServerSettings`) |
| `forge_settings.env` | Upstream Forge backend base URL (`ForgeSettings`) |
| `orchestration_settings.env` | Upstream Orchestration backend base URL (`OrchestrationSettings`) |

Copy each `*_settings.env.example` to the same filename without `.example`, then edit deployment values.
Actual `*_settings.env` files are private and excluded from Git; never commit secrets.
No field has an automatic default. Missing keys fail validation; nullable values (where allowed) must be explicitly written as `null`.

Each config model reads only its own `{module}_settings.env` file: checkout-local `module_setting_envs/` candidates are followed by `../module_setting_envs/` and `./module_setting_envs/`. Process environment variables always take precedence over env files. Root `.env` is not a fallback for `pydantic-settings` configuration. When running via Docker Compose, `./module_setting_envs` is mounted read-only at `/module_setting_envs`.
