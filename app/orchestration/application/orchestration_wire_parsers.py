"""Shared strict wire parsing primitives for Orchestration JSON payloads."""

from collections.abc import Callable
from uuid import UUID

from pydantic import JsonValue

from app.shared.types.base_types import JsonObject
from app.shared.types.wire_scalar_types import parse_wire_uuid

INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1
INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1
UINT8_MAX = 255
UINT32_MAX = 2**32 - 1
UINT64_MAX = 2**64 - 1


def require_wire_object(
    payload: JsonValue,
    required_keys: tuple[str, ...],
    optional_keys: tuple[str, ...] = (),
    *,
    label: str = "Orchestration response",
) -> JsonObject:
    """Require one source JSON object with only the declared wire keys.

    Args:
        payload: JSON value returned by the Orchestration backend.
        required_keys: Keys that the source contract requires.
        optional_keys: Keys the source may omit while serializing None.
        label: Source payload label used in strict parse error messages.
    Return:
        Validated source JSON object retaining its decoded values.
    """
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    allowed_keys = (*required_keys, *optional_keys)
    if any(key not in payload for key in required_keys):
        raise ValueError(f"{label} is missing a required wire key")
    if any(key not in allowed_keys for key in payload):
        raise ValueError(f"{label} contains an unknown wire key")
    result: JsonObject = payload
    return result


def wire_optional[ValueT](
    value: JsonValue | None,
    parser: Callable[[JsonValue], ValueT],
) -> ValueT | None:
    """Normalize a source-nullable or source-omitted value with a strict parser.

    Args:
        value: Decoded JSON value, None literal, or absent field value.
        parser: Strict parser invoked when the value is non-null.
    Return:
        Parsed typed value or None.
    """
    result = None if value is None else parser(value)
    return result


def parse_wire_str(value: JsonValue, *, label: str = "Orchestration field") -> str:
    """Parse one source string without coercing primitives.

    Args:
        value: Decoded JSON field value.
        label: Field label included in validation errors.
    Return:
        Exact source string.
    """
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    result = value
    return result


def parse_wire_bool(value: JsonValue, *, label: str = "Orchestration field") -> bool:
    """Parse one strict source boolean without integer aliases.

    Args:
        value: Decoded JSON field value.
        label: Field label included in validation errors.
    Return:
        Exact source boolean.
    """
    if type(value) is not bool:
        raise ValueError(f"{label} must be a boolean")
    result = value
    return result


def parse_wire_int(
    value: JsonValue,
    *,
    minimum: int = INT64_MIN,
    maximum: int = INT64_MAX,
    label: str = "Orchestration field",
) -> int:
    """Parse one strict source integer inside explicit inclusive bounds.

    Args:
        value: Decoded JSON field value.
        minimum: Inclusive lower integer bound.
        maximum: Inclusive upper integer bound.
        label: Field label included in validation errors.
    Return:
        Validated exact integer.
    """
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer within [{minimum}, {maximum}]")
    result = value
    return result


def parse_wire_array(value: JsonValue, *, label: str = "Orchestration field") -> list[JsonValue]:
    """Parse one source JSON array preserving original item order.

    Args:
        value: Decoded JSON field value.
        label: Field label included in validation errors.
    Return:
        Decoded JSON element list.
    """
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    result: list[JsonValue] = value
    return result


def parse_wire_str_tuple(
    value: JsonValue,
    *,
    label: str = "Orchestration field",
) -> tuple[str, ...]:
    """Parse a strict tuple of source strings without coercing elements.

    Args:
        value: Decoded JSON array value.
        label: Field label included in validation errors.
    Return:
        Immutable tuple of exact source strings.
    """
    items = parse_wire_array(value=value, label=label)
    result = tuple(parse_wire_str(value=item, label=label) for item in items)
    return result


def parse_wire_uuid_tuple(
    value: JsonValue,
    *,
    label: str = "Orchestration field",
) -> tuple[UUID, ...]:
    """Parse a strict tuple of source UUID strings.

    Args:
        value: Decoded JSON array value.
        label: Field label included in validation errors.
    Return:
        Immutable tuple of parsed UUIDs.
    """
    items = parse_wire_array(value=value, label=label)
    result = tuple(parse_wire_uuid(value=item) for item in items)
    return result


def parse_wire_object_items[DtoT](
    value: JsonValue,
    parser: Callable[[JsonValue], DtoT],
    *,
    label: str = "Orchestration field",
) -> tuple[DtoT, ...]:
    """Parse a required source JSON array into immutable leaf DTOs.

    Args:
        value: Decoded JSON array value.
        parser: Leaf object parser returning one immutable DTO.
        label: Field label included in validation errors.
    Return:
        Immutable tuple of parsed DTO items.
    """
    items = parse_wire_array(value=value, label=label)
    result = tuple(parser(item) for item in items)
    return result
