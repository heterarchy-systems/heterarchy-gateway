"""Typed Forge command failure envelopes and readback identities."""

from typing import Annotated, Literal

from fastapi import status
from pydantic import Field

from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandFailureEnvelopeDto,
    ForgeSwarmSettlementReadbackDto,
    ForgeSwarmWorkspaceReadbackDto,
    ForgeWireErrorDto,
)
from app.forge.schema.envelope.forge_envelope_schema import (
    ForgeApiVersion,
    ForgeFailureFlag,
)
from app.forge.schema.types.forge_types import ForgeErrorCode, ForgeUUID
from app.shared.base_schema import StrictSchemaModel
from app.shared.exception.forge_exception import ForgeErrorResponse
from app.shared.ingredient_element.forge.forge_enums import (
    ForgeErrorCodeEnum,
    ForgeReadbackKindEnum,
)
from app.shared.types.http_types import (
    ResponseModelDefinition,
    ResponseModels,
    build_response_models,
)


class ForgeSwarmWorkspaceReadback(StrictSchemaModel):
    """Durable identity for Swarm workspace readback after unknown outcome."""

    kind: Annotated[
        Literal[ForgeReadbackKindEnum.SWARM_WORKSPACE],
        Field(description="Readback identity kind."),
    ]
    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    member_id: Annotated[ForgeUUID, Field(description="Swarm member identity.")]

    def to_inner_dto(self) -> ForgeSwarmWorkspaceReadbackDto:
        """Build an immutable Swarm workspace readback DTO.

        Args:
            None.
        Return:
            Typed workspace readback identity.
        """
        result = ForgeSwarmWorkspaceReadbackDto(
            workspace_id=self.workspace_id,
            swarm_run_id=self.swarm_run_id,
            member_id=self.member_id,
        )
        return result


class ForgeSwarmSettlementReadback(StrictSchemaModel):
    """Durable identity for Swarm settlement readback after unknown outcome."""

    kind: Annotated[
        Literal[ForgeReadbackKindEnum.SWARM_SETTLEMENT],
        Field(description="Readback identity kind."),
    ]
    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity.")]
    swarm_run_id: Annotated[ForgeUUID, Field(description="Swarm run identity.")]
    settlement_id: Annotated[ForgeUUID, Field(description="Swarm settlement identity.")]

    def to_inner_dto(self) -> ForgeSwarmSettlementReadbackDto:
        """Build an immutable Swarm settlement readback DTO.

        Args:
            None.
        Return:
            Typed settlement readback identity.
        """
        result = ForgeSwarmSettlementReadbackDto(
            workspace_id=self.workspace_id,
            swarm_run_id=self.swarm_run_id,
            settlement_id=self.settlement_id,
        )
        return result


type ForgeReadbackHint = Annotated[
    ForgeSwarmWorkspaceReadback | ForgeSwarmSettlementReadback,
    Field(discriminator="kind"),
]


class ForgeWireError(StrictSchemaModel):
    """Complete sanitized Forge failure details from the Source envelope."""

    code: Annotated[ForgeErrorCode, Field(description="Stable Source error code.")]
    message: Annotated[str, Field(description="Stable sanitized Source message.")]
    category: Annotated[str, Field(description="Source error category.")]
    retryable: Annotated[bool, Field(description="Source retry safety claim.")]
    recovery_action: Annotated[str, Field(description="Source recovery action.")]
    recovery_hint: Annotated[str, Field(description="Source recovery guidance, possibly empty.")]
    readback: Annotated[
        ForgeReadbackHint | None,
        Field(description="Durable operation identity for Source readback, when available."),
    ]

    def to_inner_dto(self) -> ForgeWireErrorDto:
        """Build an immutable typed Forge error DTO.

        Args:
            None.
        Return:
            Typed Forge failure details.
        """
        readback = self.readback.to_inner_dto() if self.readback is not None else None
        result = ForgeWireErrorDto(
            code=ForgeErrorCodeEnum(self.code),
            message=self.message,
            category=self.category,
            retryable=self.retryable,
            recovery_action=self.recovery_action,
            recovery_hint=self.recovery_hint,
            readback=readback,
        )
        return result


class ForgeFailureEnvelope(StrictSchemaModel):
    """Versioned Forge failure response, including its original identity."""

    forge_api: Annotated[ForgeApiVersion, Field(description="Forge command API version.")]
    request_id: Annotated[ForgeUUID, Field(description="Request identity echoed by Forge.")]
    ok: Annotated[ForgeFailureFlag, Field(description="Forge command failed.")]
    error: Annotated[ForgeWireError, Field(description="Sanitized Forge failure details.")]

    def to_inner_dto(self) -> ForgeCommandFailureEnvelopeDto:
        """Build an immutable failure envelope DTO without rewriting identity.

        Args:
            None.
        Return:
            Typed Forge failure envelope.
        """
        result = ForgeCommandFailureEnvelopeDto(
            forge_api=self.forge_api,
            request_id=self.request_id,
            error=self.error.to_inner_dto(),
        )
        return result


FORGE_ERROR_RESPONSES: ResponseModels = build_response_models(
    definitions=(
        ResponseModelDefinition(
            status_code=status.HTTP_202_ACCEPTED,
            model=ForgeFailureEnvelope,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_400_BAD_REQUEST,
            model=ForgeFailureEnvelope,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_409_CONFLICT,
            model=ForgeFailureEnvelope,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_502_BAD_GATEWAY,
            model=ForgeErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            model=ForgeErrorResponse,
        ),
        ResponseModelDefinition(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            model=ForgeFailureEnvelope,
        ),
    )
)
