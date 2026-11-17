"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing_extensions import TypedDict

from app.orchestration.schema.types.orchestration_types import (
    ExecutionTimeoutMs,
    Int64,
)
from app.shared.ingredient_element.orchestration.principal_enums import PrincipalKindEnum
from app.shared.ingredient_element.orchestration.profile_enums import CliEngineEnum


class ExecutionPreferenceDict(TypedDict, total=True, closed=True):
    """Source wire fields for a reusable CLI execution preference."""

    cliEngine: str
    preferredModel: str
    preferredReasoning: str | None
    capabilities: list[str]
    rolePromptDigestHex: str | None


class ExecutionPreferenceResultDict(TypedDict, total=True, closed=True):
    """Typed Profile result fields retaining the validated CLI enum."""

    cliEngine: CliEngineEnum
    preferredModel: str
    preferredReasoning: str | None
    capabilities: list[str]
    rolePromptDigestHex: str | None


class PrincipalIdentityDict(TypedDict, total=True, closed=True):
    """Source wire fields for a principal identity."""

    kind: str
    id: str


class PrincipalIdentityResultDict(TypedDict, total=True, closed=True):
    """Typed result fields retaining the validated principal enum."""

    kind: PrincipalKindEnum
    id: str


class ExecutionPermissionsDict(TypedDict, total=True, closed=True):
    """Source wire fields for execution permission flags."""

    allowWorkspaceWrite: bool
    allowLocalShell: bool
    allowNetwork: bool


class ExecutionTimeoutsDict(TypedDict, total=True, closed=True):
    """Source wire fields for execution timeouts."""

    startupTimeoutMs: ExecutionTimeoutMs
    executionTimeoutMs: ExecutionTimeoutMs
    terminationGraceMs: ExecutionTimeoutMs


class McpGrantDict(TypedDict, total=True, closed=True):
    """Source wire fields for secret-free MCP grant metadata."""

    tokenId: str
    issuedAtMs: Int64
    expiresAtMs: Int64
