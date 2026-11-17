"""Shared Pydantic bases for query filters."""

from typing import ClassVar

from pydantic import ConfigDict

from app.shared.base_schema import StrictSchemaModel, _register_query_filter_base
from app.shared.filter_module.types.filter_types import FilterQueryParams
from app.shared.types.base_types import JsonValue


def _query_value(value: JsonValue) -> str:
    """Render a JSON scalar using the corresponding HTTP query spelling."""
    if isinstance(value, bool):
        result = "true" if value else "false"
    else:
        result = str(value)
    return result


class BaseFilter(StrictSchemaModel):
    """Serialize configured filter fields and omit values that are None."""

    _ALLOW_QUERY_OMISSION: ClassVar[bool] = True

    # HTTP query parameters always arrive as strings; coerce filter fields on validation.
    model_config = ConfigDict(strict=False)

    def to_query_params(self) -> FilterQueryParams:
        """Serialize configured criteria without unset values.

        Args:
            None.
        Return:
            Query parameters without values that are None.
        """
        raw_params = self.model_dump(mode="json", by_alias=True, exclude_none=True)
        result: FilterQueryParams = {
            key: _query_value(value=value) for key, value in raw_params.items()
        }
        return result


_register_query_filter_base(model=BaseFilter, allows_omission=BaseFilter._ALLOW_QUERY_OMISSION)
