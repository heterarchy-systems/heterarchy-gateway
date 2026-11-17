"""Immutable DTOs for shared Orchestration execution wire values."""

from dataclasses import dataclass
from uuid import UUID

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


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionPreferenceDto:
    """Immutable CLI execution preference value."""

    cli_engine: CliEngineEnum
    preferred_model: str
    preferred_reasoning: str | None
    capabilities: tuple[str, ...]
    role_prompt_digest_hex: str | None

    def to_dict(self) -> ExecutionPreferenceDict:
        """Serialize the execution preference to Orchestration wire names.

        Args:
            None.
        Return:
            Complete execution preference wire dictionary.
        """
        result = ExecutionPreferenceDict(
            cliEngine=self.cli_engine.value,
            preferredModel=self.preferred_model,
            preferredReasoning=self.preferred_reasoning,
            capabilities=list(self.capabilities),
            rolePromptDigestHex=self.role_prompt_digest_hex,
        )
        return result

    def to_schema_dict(self) -> ExecutionPreferenceResultDict:
        """Serialize a validated preference while retaining its enum value.

        Args:
            None.
        Return:
            Complete typed execution preference result.
        """
        result = ExecutionPreferenceResultDict(
            cliEngine=self.cli_engine,
            preferredModel=self.preferred_model,
            preferredReasoning=self.preferred_reasoning,
            capabilities=list(self.capabilities),
            rolePromptDigestHex=self.role_prompt_digest_hex,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class PrincipalIdentityDto:
    """Immutable principal discriminator and identifier."""

    kind: PrincipalKindEnum
    id: str

    def to_dict(self) -> PrincipalIdentityDict:
        """Serialize the principal identity to Orchestration wire names.

        Args:
            None.
        Return:
            Complete principal identity wire dictionary.
        """
        result = PrincipalIdentityDict(kind=self.kind.value, id=self.id)
        return result

    def to_schema_dict(self) -> PrincipalIdentityResultDict:
        """Serialize a validated identity while retaining its principal enum.

        Args:
            None.
        Return:
            Complete typed principal identity result.
        """
        result = PrincipalIdentityResultDict(kind=self.kind, id=self.id)
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionPermissionsDto:
    """Immutable sandbox permission flags."""

    allow_workspace_write: bool
    allow_local_shell: bool
    allow_network: bool

    def to_dict(self) -> ExecutionPermissionsDict:
        """Serialize execution permission flags to Orchestration wire names.

        Args:
            None.
        Return:
            Complete execution permissions wire dictionary.
        """
        result = ExecutionPermissionsDict(
            allowWorkspaceWrite=self.allow_workspace_write,
            allowLocalShell=self.allow_local_shell,
            allowNetwork=self.allow_network,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionTimeoutsDto:
    """Immutable bounded execution timeout values."""

    startup_timeout_ms: ExecutionTimeoutMs
    execution_timeout_ms: ExecutionTimeoutMs
    termination_grace_ms: ExecutionTimeoutMs

    def to_dict(self) -> ExecutionTimeoutsDict:
        """Serialize timeouts to Orchestration wire names.

        Args:
            None.
        Return:
            Complete execution timeouts wire dictionary.
        """
        result = ExecutionTimeoutsDict(
            startupTimeoutMs=self.startup_timeout_ms,
            executionTimeoutMs=self.execution_timeout_ms,
            terminationGraceMs=self.termination_grace_ms,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class McpGrantDto:
    """Immutable secret-free MCP grant metadata."""

    token_id: UUID
    issued_at_ms: Int64
    expires_at_ms: Int64

    def to_dict(self) -> McpGrantDict:
        """Serialize MCP grant metadata to Orchestration wire names.

        Args:
            None.
        Return:
            Complete MCP grant wire dictionary.
        """
        result = McpGrantDict(
            tokenId=str(self.token_id),
            issuedAtMs=self.issued_at_ms,
            expiresAtMs=self.expires_at_ms,
        )
        return result
