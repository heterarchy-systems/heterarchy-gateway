"""Typed extractors for validated upstream JSON payloads."""

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum

from app.shared.base_schema import StrictSchemaModel
from app.shared.exception import BaseExcept
from app.shared.types.base_types import JsonObject, JsonValue
from app.shared.types.json_contract import decode_json


def require_str(
    payload: Mapping[str, JsonValue],
    key: str,
    *,
    service: str,
    error_type: type[BaseExcept],
) -> str:
    """Extract a required string field from an upstream JSON object.

    Args:
        payload: Validated upstream JSON mapping.
        key: Required field name.
        service: Service identifier for error metadata.
        error_type: Domain exception class inheriting BaseExcept.
    Return:
        Extracted string value.
    """
    value = payload.get(key)
    if not isinstance(value, str):
        raise error_type(
            502,
            f"{service}_invalid_payload",
            f"Upstream {service} response is missing a string {key}",
            retryable=False,
        )
    return value


def require_optional_str(
    payload: Mapping[str, JsonValue],
    key: str,
    *,
    service: str,
    error_type: type[BaseExcept],
) -> str | None:
    """Extract a required-present optional string field (str or None).

    Args:
        payload: Validated upstream JSON mapping.
        key: Field name that must map to str or None.
        service: Service identifier for error metadata.
        error_type: Domain exception class inheriting BaseExcept.
    Return:
        String value or None.
    """
    if key not in payload:
        raise error_type(
            502,
            f"{service}_invalid_payload",
            f"Upstream {service} response is missing {key}",
            retryable=False,
        )
    value = payload[key]
    if value is not None and not isinstance(value, str):
        raise error_type(
            502,
            f"{service}_invalid_payload",
            f"Upstream {service} field {key} must be a string or null",
            retryable=False,
        )
    return value


def require_bool(
    payload: Mapping[str, JsonValue],
    key: str,
    *,
    service: str,
    error_type: type[BaseExcept],
) -> bool:
    """Extract a required strict boolean field from an upstream JSON object.

    Args:
        payload: Validated upstream JSON mapping.
        key: Required field name.
        service: Service identifier for error metadata.
        error_type: Domain exception class inheriting BaseExcept.
    Return:
        Extracted boolean value.
    """
    value = payload.get(key)
    if type(value) is not bool:
        raise error_type(
            502,
            f"{service}_invalid_payload",
            f"Upstream {service} response is missing a boolean {key}",
            retryable=False,
        )
    return value


def require_iso_datetime(
    payload: Mapping[str, JsonValue],
    key: str,
    *,
    service: str,
    error_type: type[BaseExcept],
) -> datetime:
    """Extract and parse a required ISO-8601 timestamp string.

    Args:
        payload: Validated upstream JSON mapping.
        key: Required timestamp field name.
        service: Service identifier for error metadata.
        error_type: Domain exception class inheriting BaseExcept.
    Return:
        Parsed datetime instance.
    """
    raw_value = require_str(payload, key, service=service, error_type=error_type)
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError as error:
        raise error_type(
            502,
            f"{service}_invalid_payload",
            f"Upstream {service} field {key} is not a valid ISO-8601 timestamp",
            retryable=False,
        ) from error


def require_optional_object(
    payload: Mapping[str, JsonValue],
    key: str,
    *,
    service: str,
    error_type: type[BaseExcept],
) -> JsonObject | None:
    """Extract an optional JSON object field (dict or None when omitted/null).

    Args:
        payload: Validated upstream JSON mapping.
        key: Optional object field name.
        service: Service identifier for error metadata.
        error_type: Domain exception class inheriting BaseExcept.
    Return:
        JSON object dictionary or None.
    """
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise error_type(
            502,
            f"{service}_invalid_payload",
            f"Upstream {service} field {key} must be a JSON object or null",
            retryable=False,
        )
    return {inner_key: inner_value for inner_key, inner_value in value.items()}


def require_enum[EnumT: StrEnum](
    payload: Mapping[str, JsonValue],
    key: str,
    enum_cls: type[EnumT],
    *,
    service: str,
    error_type: type[BaseExcept],
) -> EnumT:
    """Extract a required StrEnum member from an upstream JSON object.

    Args:
        payload: Validated upstream JSON mapping.
        key: Required enum field name.
        enum_cls: Target StrEnum class.
        service: Service identifier for error metadata.
        error_type: Domain exception class inheriting BaseExcept.
    Return:
        Validated StrEnum member.
    """
    raw_value = require_str(payload, key, service=service, error_type=error_type)
    try:
        return enum_cls(raw_value)
    except ValueError as error:
        raise error_type(
            502,
            f"{service}_invalid_payload",
            f"Upstream {service} field {key} has unsupported value",
            retryable=False,
        ) from error


def require_object_items(
    payload: Mapping[str, JsonValue],
    *,
    service: str,
    error_type: type[BaseExcept],
) -> list[JsonObject]:
    """Extract a required array of JSON objects under the upstream 'items' key.

    Args:
        payload: Validated upstream JSON mapping.
        service: Service identifier for error metadata.
        error_type: Domain exception class inheriting BaseExcept.
    Return:
        List of validated JSON object dictionaries.
    """
    items = payload.get("items")
    if not isinstance(items, list):
        raise error_type(
            502,
            f"{service}_invalid_payload",
            f"Upstream {service} response is missing an items array",
            retryable=False,
        )
    validated: list[JsonObject] = []
    for item in items:
        if not isinstance(item, dict):
            raise error_type(
                502,
                f"{service}_invalid_payload",
                f"Upstream {service} items entries must be JSON objects",
                retryable=False,
            )
        validated.append({key: value for key, value in item.items()})
    return validated


def model_to_json_value(model: StrictSchemaModel) -> JsonValue:
    """Serialize a strict schema model into a typed JsonValue without Any.

    Args:
        model: Validated StrictSchemaModel instance.
    Return:
        Canonical JsonValue representation.
    """
    return decode_json(model.model_dump_json().encode("utf-8"))


def model_to_patch_object(model: StrictSchemaModel) -> JsonObject:
    """Serialize explicitly provided fields of a strict model into a JSON object.

    Args:
        model: Partial-update StrictSchemaModel instance.
    Return:
        JSON object containing only fields explicitly supplied by the caller.
    """
    decoded = decode_json(model.model_dump_json(exclude_unset=True).encode("utf-8"))
    if not isinstance(decoded, dict):
        raise ValueError("Serialized schema model must encode to a JSON object")
    return {key: value for key, value in decoded.items()}
