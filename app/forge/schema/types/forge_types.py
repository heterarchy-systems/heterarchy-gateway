"""Forge wire-type aliases preserving Rust bounds and strict JSON scalars."""

from functools import partial
from typing import Annotated

from pydantic import BeforeValidator, Field

from app.shared.ingredient_element.forge.forge_enums import (
    ActivityLivenessEnum,
    ActivityStateEnum,
    DagLineageKindEnum,
    DagNodeLifecycleEnum,
    DagNodeStatusEnum,
    ForgeCommandOpEnum,
    ForgeErrorCodeEnum,
    ForgePrincipalKindEnum,
    ForgeReadbackKindEnum,
    LocationStateEnum,
    SettlementJournalStateEnum,
    SwarmConvergenceStatusEnum,
    SwarmTargetKindEnum,
    SwarmWorkspaceModeEnum,
)
from app.shared.types.wire_scalar_types import WireUUID, parse_wire_enum

ForgeUUID = WireUUID

type ForgeCommandOp = Annotated[
    ForgeCommandOpEnum,
    BeforeValidator(partial(parse_wire_enum, ForgeCommandOpEnum)),
]
type ForgeErrorCode = Annotated[
    ForgeErrorCodeEnum,
    BeforeValidator(partial(parse_wire_enum, ForgeErrorCodeEnum)),
]
type ForgePrincipalKind = Annotated[
    ForgePrincipalKindEnum,
    BeforeValidator(partial(parse_wire_enum, ForgePrincipalKindEnum)),
]
type ForgeReadbackKind = Annotated[
    ForgeReadbackKindEnum,
    BeforeValidator(partial(parse_wire_enum, ForgeReadbackKindEnum)),
]
type LocationState = Annotated[
    LocationStateEnum,
    BeforeValidator(partial(parse_wire_enum, LocationStateEnum)),
]
type ActivityState = Annotated[
    ActivityStateEnum,
    BeforeValidator(partial(parse_wire_enum, ActivityStateEnum)),
]
type ActivityLiveness = Annotated[
    ActivityLivenessEnum,
    BeforeValidator(partial(parse_wire_enum, ActivityLivenessEnum)),
]
type DagNodeLifecycle = Annotated[
    DagNodeLifecycleEnum,
    BeforeValidator(partial(parse_wire_enum, DagNodeLifecycleEnum)),
]
type DagNodeStatus = Annotated[
    DagNodeStatusEnum,
    BeforeValidator(partial(parse_wire_enum, DagNodeStatusEnum)),
]
type DagLineageKind = Annotated[
    DagLineageKindEnum,
    BeforeValidator(partial(parse_wire_enum, DagLineageKindEnum)),
]
type SwarmWorkspaceMode = Annotated[
    SwarmWorkspaceModeEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmWorkspaceModeEnum)),
]
type SwarmTargetKind = Annotated[
    SwarmTargetKindEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmTargetKindEnum)),
]
type SwarmConvergenceStatus = Annotated[
    SwarmConvergenceStatusEnum,
    BeforeValidator(partial(parse_wire_enum, SwarmConvergenceStatusEnum)),
]
type SettlementJournalState = Annotated[
    SettlementJournalStateEnum,
    BeforeValidator(partial(parse_wire_enum, SettlementJournalStateEnum)),
]

type Int64 = Annotated[int, Field(ge=-(2**63), le=2**63 - 1)]
type UInt32 = Annotated[int, Field(ge=0, le=2**32 - 1)]
type UInt64 = Annotated[int, Field(ge=0, le=2**64 - 1)]
