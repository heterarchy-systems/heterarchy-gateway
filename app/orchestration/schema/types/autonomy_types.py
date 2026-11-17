"""Bounded primitive aliases used by Autonomy wire schemas."""

from functools import partial
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BeforeValidator, Field

from app.orchestration.schema.types.orchestration_types import (
    Int64,
    TimestampMs,
    UInt32,
    UInt64,
)
from app.shared.ingredient_element.orchestration.autonomy_enums import (
    LaunchUnknownReasonEnum,
)
from app.shared.types.wire_scalar_types import WireUUID, parse_wire_enum


def require_non_nil_snapshot_id(value: UUID) -> UUID:
    """Reject nil identities after parsing the snapshot's wire UUID."""
    if value.int == 0:
        raise ValueError("Snapshot identity must be non-nil")
    return value


type SnapshotUUID = Annotated[WireUUID, AfterValidator(require_non_nil_snapshot_id)]
type DagRevision = Annotated[Int64, Field(ge=1)]
type NonNegativeDagRevision = Annotated[Int64, Field(ge=0)]
type PositiveInt64 = Annotated[Int64, Field(gt=0)]
type SignedInt32 = Annotated[int, Field(ge=-(2**31), le=2**31 - 1)]
type WorkAttempt = UInt32
type UnsignedRevision = UInt64
type UnixTimestampMs = TimestampMs
type LaunchUnknownReason = Annotated[
    LaunchUnknownReasonEnum,
    BeforeValidator(partial(parse_wire_enum, LaunchUnknownReasonEnum)),
]
type Sha256DigestHex = Annotated[
    str,
    Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"),
]
