"""Parse JSON UUID and enum strings while retaining strict model field policies."""

from enum import StrEnum
from typing import Annotated
from uuid import UUID

from pydantic import BeforeValidator, JsonValue, TypeAdapter

_UUID_ADAPTER = TypeAdapter(UUID)


def parse_wire_uuid(value: UUID | JsonValue) -> UUID:
    """Parse a UUID string at a JSON boundary or retain an already typed UUID.

    Args:
        value: A UUID instance or a JSON scalar supplied by the caller.
    Return:
        A parsed UUID with all UUID versions and the nil identity preserved.
    """
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise ValueError("UUID fields require a UUID string")
    result = _UUID_ADAPTER.validate_python(value)
    return result


def parse_wire_enum[EnumT: StrEnum](
    enum_type: type[EnumT],
    value: EnumT | JsonValue,
) -> EnumT:
    """Parse a declared string enum without coercing other JSON primitive types.

    Args:
        enum_type: Concrete vocabulary owned by the relevant feature.
        value: A string enum member or a JSON value supplied by the caller.
    Return:
        The member matching the exact declared wire value.
    """
    if not isinstance(value, str):
        raise ValueError("Enum fields require a declared string value")
    result = enum_type(value)
    return result


type WireUUID = Annotated[UUID, BeforeValidator(parse_wire_uuid)]
