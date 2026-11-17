"""Strict common request and success envelope schemas for Forge commands."""

from typing import Annotated, Literal

from pydantic import BeforeValidator, ConfigDict, Field, TypeAdapter

from app.forge.application.inner_dto.forge_envelope_dto import ForgeCommandEnvelopeDto
from app.forge.schema.types.forge_types import (
    ForgeCommandOp,
    ForgePrincipalKind,
    ForgeUUID,
    Int64,
)
from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum
from app.shared.types.base_types import JsonValue

_JSON_VALUE_ADAPTER = TypeAdapter(JsonValue, config=ConfigDict(strict=True, allow_inf_nan=False))


def _require_true(value: JsonValue) -> Literal[True]:
    """Reject non-boolean values before the success literal discriminator."""
    if type(value) is not bool or value is not True:
        raise ValueError("Forge success discriminator must be boolean true")
    result: Literal[True] = True
    return result


def _require_false(value: JsonValue) -> Literal[False]:
    """Reject non-boolean values before the failure literal discriminator."""
    if type(value) is not bool or value is not False:
        raise ValueError("Forge failure discriminator must be boolean false")
    result: Literal[False] = False
    return result


type ForgeApiVersion = Annotated[int, Field(strict=True, ge=1, le=1)]
type ForgeSuccessFlag = Annotated[Literal[True], BeforeValidator(_require_true)]
type ForgeFailureFlag = Annotated[Literal[False], BeforeValidator(_require_false)]


class ForgeLocator(StrictSchemaModel):
    """Validated locator fields shared by Forge workspace operations."""

    location_id: Annotated[ForgeUUID, Field(description="Forge Location identity.")]
    expected_revision: Annotated[
        Int64,
        Field(description="Observed Location revision used to resolve the locator."),
    ]
    relative_root: Annotated[
        str,
        Field(description="Relative workspace root resolved beneath the Location."),
    ]


class ForgeWorkspaceScope(StrictSchemaModel):
    """Resolved Workspace revision and its Source Location locator."""

    workspace_id: Annotated[ForgeUUID, Field(description="Forge Workspace identity.")]
    workspace_revision: Annotated[
        Int64,
        Field(description="Observed Workspace revision."),
    ]
    locator: Annotated[ForgeLocator, Field(description="Source Location locator.")]


class ForgePrincipal(StrictSchemaModel):
    """Authenticated principal identity without bearer credential material."""

    kind: Annotated[
        ForgePrincipalKind,
        Field(description="Principal identity kind asserted by the caller."),
    ]
    token_id: Annotated[
        ForgeUUID | None,
        Field(description="Direct token identity when kind is direct_token."),
    ]
    grant_id: Annotated[
        ForgeUUID | None,
        Field(description="OAuth grant identity when kind is oauth_grant."),
    ]


class ForgeSessionActor(StrictSchemaModel):
    """Caller session and principal identity bound to a Workspace."""

    session_id: Annotated[ForgeUUID, Field(description="Forge Agent session identity.")]
    principal: Annotated[ForgePrincipal, Field(description="Authenticated principal identity.")]
    workspace_id: Annotated[ForgeUUID, Field(description="Workspace identity bound to the actor.")]


class ForgeCommandRequest[PayloadSchema: StrictSchemaModel](StrictSchemaModel):
    """Versioned public request envelope for a single Forge command route."""

    forge_api: Annotated[ForgeApiVersion, Field(description="Forge command API version.")]
    request_id: Annotated[ForgeUUID, Field(description="Caller-supplied Forge command identity.")]
    op: Annotated[
        ForgeCommandOp,
        Field(description="Forge command operation selected by this route."),
    ]
    payload: Annotated[PayloadSchema, Field(description="Strict operation payload.")]

    def to_inner_dto[PayloadDictT](self, payload: PayloadDictT) -> ForgeCommandEnvelopeDto:
        """Build the immutable versioned command envelope for the caller.

        Args:
            payload: Operation payload returned by its closed typed DTO.
        Return:
            Immutable Forge command envelope DTO.
        """
        payload_value = _JSON_VALUE_ADAPTER.validate_python(payload, strict=True)
        result = ForgeCommandEnvelopeDto(
            forge_api=self.forge_api,
            request_id=self.request_id,
            op=ForgeCommandOpEnum(self.op),
            payload=payload_value,
        )
        return result


class ForgeSuccessEnvelope[ResultSchema](StrictSchemaModel):
    """Successful versioned Forge reply with a typed operation result."""

    forge_api: Annotated[ForgeApiVersion, Field(description="Forge command API version.")]
    request_id: Annotated[ForgeUUID, Field(description="Request identity echoed by Forge.")]
    ok: Annotated[ForgeSuccessFlag, Field(description="Forge command succeeded.")]
    result: Annotated[ResultSchema, Field(description="Operation-specific result payload.")]


type ForgeSourceSuccessEnvelope = ForgeSuccessEnvelope[JsonValue]
