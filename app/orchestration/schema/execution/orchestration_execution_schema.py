"""Shared strict Orchestration execution wire schemas."""

from typing import Annotated

from pydantic import Field

from app.orchestration.application.inner_dto.orchestration_execution_dto import (
    ExecutionPermissionsDto,
    ExecutionPreferenceDto,
    ExecutionTimeoutsDto,
    McpGrantDto,
    PrincipalIdentityDto,
)
from app.orchestration.schema.types.orchestration_types import (
    ExecutionPreference,
    ExecutionTimeoutMs,
    Int64,
    McpGrant,
    PrincipalKind,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.orchestration.principal_enums import PrincipalKindEnum
from app.shared.ingredient_element.orchestration.profile_enums import CliEngineEnum


class ExecutionPreferenceSchema(StrictSchemaModel):
    """Reusable Agent Profile CLI execution preference."""

    cli_engine: Annotated[
        ExecutionPreference,
        Field(alias="cliEngine", description="Supported local CLI execution engine."),
    ]
    preferred_model: Annotated[
        str,
        Field(alias="preferredModel", description="Preferred model identifier."),
    ]
    preferred_reasoning: Annotated[
        str | None,
        Field(alias="preferredReasoning", description="Preferred reasoning level or null."),
    ]
    capabilities: Annotated[
        list[str],
        Field(description="Capability labels available to the execution."),
    ]
    role_prompt_digest_hex: Annotated[
        str | None,
        Field(alias="rolePromptDigestHex", description="Role prompt SHA-256 digest or null."),
    ]

    def to_inner_dto(self) -> ExecutionPreferenceDto:
        """Convert the validated preference to its immutable DTO.

        Args:
            None.
        Return:
            Immutable execution preference DTO.
        """
        result = ExecutionPreferenceDto(
            cli_engine=CliEngineEnum(self.cli_engine),
            preferred_model=self.preferred_model,
            preferred_reasoning=self.preferred_reasoning,
            capabilities=tuple(self.capabilities),
            role_prompt_digest_hex=self.role_prompt_digest_hex,
        )
        return result


class PrincipalIdentitySchema(StrictSchemaModel):
    """Three-way principal discriminator used in execution identities."""

    kind: Annotated[PrincipalKind, Field(description="Authenticated principal kind.")]
    id: Annotated[str, Field(description="Principal identifier or empty trusted-stdio value.")]

    def to_inner_dto(self) -> PrincipalIdentityDto:
        """Convert the validated principal identity to its immutable DTO.

        Args:
            None.
        Return:
            Immutable principal identity DTO.
        """
        result = PrincipalIdentityDto(kind=PrincipalKindEnum(self.kind), id=self.id)
        return result


class ExecutionPermissionsSchema(StrictSchemaModel):
    """Explicit sandbox permissions frozen for an execution attempt."""

    allow_workspace_write: Annotated[
        bool,
        Field(alias="allowWorkspaceWrite", description="Allow workspace writes."),
    ]
    allow_local_shell: Annotated[
        bool,
        Field(alias="allowLocalShell", description="Allow local shell access."),
    ]
    allow_network: Annotated[
        bool,
        Field(alias="allowNetwork", description="Allow network access."),
    ]

    def to_inner_dto(self) -> ExecutionPermissionsDto:
        """Convert validated permission flags to their immutable DTO.

        Args:
            None.
        Return:
            Immutable execution permissions DTO.
        """
        result = ExecutionPermissionsDto(
            allow_workspace_write=self.allow_workspace_write,
            allow_local_shell=self.allow_local_shell,
            allow_network=self.allow_network,
        )
        return result


class ExecutionTimeoutsSchema(StrictSchemaModel):
    """Bounded startup, execution and termination timeouts in milliseconds."""

    startup_timeout_ms: Annotated[
        ExecutionTimeoutMs,
        Field(alias="startupTimeoutMs", description="Startup timeout in milliseconds."),
    ]
    execution_timeout_ms: Annotated[
        ExecutionTimeoutMs,
        Field(alias="executionTimeoutMs", description="Execution timeout in milliseconds."),
    ]
    termination_grace_ms: Annotated[
        ExecutionTimeoutMs,
        Field(alias="terminationGraceMs", description="Termination grace in milliseconds."),
    ]

    def to_inner_dto(self) -> ExecutionTimeoutsDto:
        """Convert validated timeout values to their immutable DTO.

        Args:
            None.
        Return:
            Immutable execution timeouts DTO.
        """
        result = ExecutionTimeoutsDto(
            startup_timeout_ms=self.startup_timeout_ms,
            execution_timeout_ms=self.execution_timeout_ms,
            termination_grace_ms=self.termination_grace_ms,
        )
        return result


class McpGrantSchema(StrictSchemaModel):
    """Secret-free MCP token grant metadata frozen in an execution snapshot."""

    token_id: Annotated[McpGrant, Field(alias="tokenId", description="MCP token UUID.")]
    issued_at_ms: Annotated[
        Int64, Field(alias="issuedAtMs", description="Issue time in milliseconds.")
    ]
    expires_at_ms: Annotated[
        Int64,
        Field(alias="expiresAtMs", description="Expiration time in milliseconds."),
    ]

    def to_inner_dto(self) -> McpGrantDto:
        """Convert validated grant metadata to its immutable DTO.

        Args:
            None.
        Return:
            Immutable MCP grant DTO.
        """
        result = McpGrantDto(
            token_id=self.token_id,
            issued_at_ms=self.issued_at_ms,
            expires_at_ms=self.expires_at_ms,
        )
        return result
