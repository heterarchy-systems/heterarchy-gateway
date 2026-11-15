"""Module identities for environment-backed gateway configuration sources."""

from enum import StrEnum


class SettingsModule(StrEnum):
    """Name the module that owns a settings env file."""

    GATEWAY = "gateway"
    FORGE = "forge"
    ORCHESTRATION = "orchestration"
