"""Shared Pydantic bases for query filters."""

from collections.abc import Callable
from datetime import date
from typing import Annotated

from pydantic import ConfigDict, Field, model_validator

from app.shared.base_schema import StrictSchemaModel
from app.shared.filter_module.types.filter_types import FilterQueryParams

_DATE_COMPARATORS: dict[str, Callable[[date, date], bool]] = {
    "created_after": lambda bound, target: target >= bound,
    "created_before": lambda bound, target: target <= bound,
}


class BaseFilter(StrictSchemaModel):
    """Serialize configured filter fields and omit values that are None."""

    # HTTP query parameters always arrive as strings; coerce filter fields on validation.
    model_config = ConfigDict(strict=False)

    def to_query_params(self) -> FilterQueryParams:
        """Serialize configured criteria without unset values.

        Args:
            None.
        Return:
            Query parameters without values that are None.
        """
        raw_params = self.model_dump(mode="json", exclude_none=True)
        result: FilterQueryParams = {key: str(value) for key, value in raw_params.items()}
        return result


class BaseDateFilter(BaseFilter):
    """Shared optional creation-date range criteria."""

    created_after: Annotated[
        date | None,
        Field(description="Include resources created on or after this date."),
    ] = None
    created_before: Annotated[
        date | None,
        Field(description="Include resources created on or before this date."),
    ] = None

    @model_validator(mode="after")
    def validate_date_bounds(self) -> BaseDateFilter:
        """Reject inverted lower and upper creation-date bounds.

        Args:
            None.
        Return:
            Validated filter instance.
        """
        active_bounds = self._active_date_bounds()
        if (
            len(active_bounds) == len(_DATE_COMPARATORS)
            and active_bounds["created_after"] > active_bounds["created_before"]
        ):
            raise ValueError("created_after must not be later than created_before")
        result = self
        return result

    def matches_created_date(self, created_at: date) -> bool:
        """Return whether a creation date satisfies configured date bounds.

        Args:
            created_at: Resource creation date to test.
        Return:
            Whether the date lies within configured bounds.
        """
        active_bounds = self._active_date_bounds()
        result = all(
            _DATE_COMPARATORS[key](bound, created_at) for key, bound in active_bounds.items()
        )
        return result

    def _active_date_bounds(self) -> dict[str, date]:
        """Extract configured non-None date-bound fields via Pydantic exclude_none.

        Args:
            None.
        Return:
            Mapping of active date-bound field names to date values.
        """
        result: dict[str, date] = {
            key: value
            for key, value in self.model_dump(exclude_none=True).items()
            if key in _DATE_COMPARATORS and isinstance(value, date)
        }
        return result
