"""Strict structural helpers for Autonomy source response parsing."""

from pydantic import JsonValue

from app.shared.types.base_types import JsonObject


def require_wire_object(
    payload: JsonValue,
    required_keys: tuple[str, ...],
    optional_keys: tuple[str, ...],
) -> JsonObject:
    """Require one source JSON object with only the declared wire keys.

    Args:
        payload: JSON value returned by the Orchestration backend.
        required_keys: Keys that the source response must include.
        optional_keys: Keys the source may omit while serializing None.
    Return:
        Validated source JSON object retaining its decoded values.
    """
    if not isinstance(payload, dict):
        raise ValueError("Orchestration response must be a JSON object")
    allowed_keys = (*required_keys, *optional_keys)
    if any(key not in payload for key in required_keys):
        raise ValueError("Orchestration response is missing a required wire key")
    if any(key not in allowed_keys for key in payload):
        raise ValueError("Orchestration response contains an unknown wire key")
    result: JsonObject = payload
    return result
