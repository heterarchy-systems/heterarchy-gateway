"""Typed serialization helpers for validated upstream JSON payloads."""

from pydantic import BaseModel, JsonValue

from app.shared.types.json_contract import validate_json_value


def model_to_json_value(model: BaseModel) -> JsonValue:
    """Convert a validated boundary model into JSON using its wire aliases.

    Args:
        model: Validated named-field or root boundary model.
    Return:
        Canonical JSON value representation.
    """
    result = validate_json_value(value=model.model_dump(mode="json", by_alias=True))
    return result
