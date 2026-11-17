"""Strict UTF-8 JSON encoding and decoding for typed JSON values."""

from collections.abc import Mapping
from math import isfinite

from pydantic import ConfigDict, JsonValue, TypeAdapter

from app.shared.types.base_types import JsonObject

_JSON_VALUE_ADAPTER = TypeAdapter(
    JsonValue,
    config=ConfigDict(strict=True, allow_inf_nan=False),
)
_MIN_SERIALIZABLE_INTEGER = -(2**63)
_MAX_SERIALIZABLE_INTEGER = 2**64 - 1


def validate_json_value(value: JsonValue | Mapping[str, JsonValue]) -> JsonValue:
    """Validate an in-memory JSON value without a UTF-8 serialization round trip.

    Args:
        value: Decoded JSON value or a typed JSON mapping.
    Return:
        A finite JSON value with its original null and integer values preserved.
    """
    result = _JSON_VALUE_ADAPTER.validate_python(value, strict=True)
    _validate_numbers(value=result, enforce_integer_bounds=False)
    return result


def validate_json_object[ValueT](value: Mapping[str, ValueT]) -> JsonObject:
    """Validate a structural TypedDict before handing it to the JSON transport.

    Args:
        value: String-keyed mapping with statically typed nested values.
    Return:
        A finite JSON object compatible with the transport's recursive JSON type.
    """
    result = _JSON_VALUE_ADAPTER.validate_python(value, strict=True)
    _validate_numbers(value=result, enforce_integer_bounds=True)
    if not isinstance(result, dict):
        raise ValueError("JSON request payload must be an object")
    return result


def encode_json(value: JsonValue | Mapping[str, JsonValue]) -> bytes:
    """Validate a JSON value and encode it as compact UTF-8 JSON bytes.

    Integer values retain the signed-64 through unsigned-64 serialization range.
    Raises:
        ValueError: The value is not finite JSON or contains an out-of-range integer.
    """
    validated = _JSON_VALUE_ADAPTER.validate_python(value, strict=True)
    _validate_numbers(value=validated, enforce_integer_bounds=True)
    return _JSON_VALUE_ADAPTER.dump_json(validated)


def decode_json(payload: bytes) -> JsonValue:
    """Decode UTF-8 JSON bytes into a finite, typed JSON value.

    Raises:
        ValueError: The input is malformed or contains a non-finite number.
    """
    validated = _JSON_VALUE_ADAPTER.validate_json(payload, strict=True)
    _validate_numbers(value=validated, enforce_integer_bounds=False)
    return validated


def _validate_numbers(value: JsonValue, *, enforce_integer_bounds: bool) -> None:
    """Reject non-finite floats and optionally out-of-range serialized integers."""
    match value:
        case int():
            if (
                enforce_integer_bounds
                and not _MIN_SERIALIZABLE_INTEGER <= value <= _MAX_SERIALIZABLE_INTEGER
            ):
                raise ValueError("JSON integer is outside the supported serialization range")
        case float():
            if not isfinite(value):
                raise ValueError("JSON numbers must be finite")
        case list():
            for item in value:
                _validate_numbers(value=item, enforce_integer_bounds=enforce_integer_bounds)
        case dict():
            for item in value.values():
                _validate_numbers(value=item, enforce_integer_bounds=enforce_integer_bounds)
