"""Shared StrEnum ingredient definitions for Gateway request diagnostics."""

from enum import StrEnum


class FailureScenario(StrEnum):
    FORGE_TIMEOUT = "forge_timeout"
    FORGE_500 = "forge_500"
    ORCHESTRATION_UNAVAILABLE = "orchestration_unavailable"
    INVALID_JSON = "invalid_json"
    SLOW_FORGE_3S = "slow_forge_3s"


class ContractName(StrEnum):
    FORGE = "forge"
    ORCHESTRATION = "orchestration"
