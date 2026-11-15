"""Thin entrypoint exposing the gateway FastAPI factory."""

import uvicorn

from app.bootstrap import create_app
from app.shared.settings_modules.gateway_settings import GatewayServerSettings

__all__ = ["create_app", "run"]


def run() -> None:
    """Run the gateway with uvicorn using explicit GatewayServerSettings.

    Args:
        None.
    Return:
        None.
    """
    server_settings = GatewayServerSettings()
    uvicorn.run(
        "app.bootstrap:create_app",
        factory=True,
        host=server_settings.host,
        port=server_settings.port,
    )


if __name__ == "__main__":
    run()
