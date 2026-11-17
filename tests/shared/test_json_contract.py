"""JSON boundary serialization preserves aliases, nulls, roots, and finite values."""

from typing import Annotated
from uuid import UUID

import pytest
from pydantic import BaseModel, Field

from app.shared.base_schema import StrictRootSchemaModel, StrictSchemaModel
from app.shared.types.base_types import JsonValue
from app.shared.types.upstream_payload import model_to_json_value


class _AliasResponse(StrictSchemaModel):
    source_id: Annotated[UUID, Field(alias="sourceId", description="Source identity.")]
    nullable_value: Annotated[
        str | None, Field(alias="nullableValue", description="Explicit nullable value.")
    ]


class _RootResponse(StrictRootSchemaModel[list[str] | None]):
    root: Annotated[list[str] | None, Field(description="Source root value.")]


class _NumberResponse(StrictSchemaModel):
    value: Annotated[float, Field(description="Finite value for JSON serialization.")]


def test_model_json_conversion_preserves_wire_aliases_and_explicit_nulls() -> None:
    identity = UUID("11111111-1111-1111-1111-111111111111")
    cases: dict[str, tuple[BaseModel, JsonValue]] = {
        "aliased_fields": (
            _AliasResponse(sourceId=identity, nullableValue=None),
            {"sourceId": str(identity), "nullableValue": None},
        ),
        "root_list": (_RootResponse(root=["alpha", "beta"]), ["alpha", "beta"]),
        "root_null": (_RootResponse(root=None), None),
    }
    for model, expected in cases.values():
        assert model_to_json_value(model) == expected


def test_model_json_conversion_rejects_nonfinite_values() -> None:
    cases: dict[str, float] = {"nan": float("nan"), "infinity": float("inf")}
    for value in cases.values():
        with pytest.raises(ValueError):
            model_to_json_value(_NumberResponse(value=value))
