"""Internal DTOs for Forge application results."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class GetForgeInnerDto:
    """Normalized internal forge representation."""

    id: str
    name: str
    description: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateForgeInnerDto:
    """Normalized internal result for creating a forge."""

    id: str
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UpdateForgeInnerDto:
    """Normalized internal result for updating a forge."""

    id: str
    updated: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteForgeInnerDto:
    """Normalized internal result for deleting a forge."""

    id: str
    deleted: bool
