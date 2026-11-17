"""Validate query key multiplicity without deciding feature value semantics."""

from collections import Counter
from collections.abc import Collection

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.datastructures import QueryParams

from app.shared.filter_module.base_filter import BaseFilter
from app.shared.types.query_types import QueryShapeIssue


def query_shape_matches(
    params: QueryParams,
    required: Collection[str],
    optional: Collection[str],
) -> bool:
    """Check required keys once, optional keys at most once, and reject unknown names.

    Args:
        params: Original HTTP query multimap.
        required: Source wire names that must occur once.
        optional: Source wire names that may be omitted.
    Return:
        Whether the key names and multiplicities match the contract.
    """
    counts = Counter(key for key, _value in params.multi_items())
    if set(counts).difference(required, optional):
        return False
    result = all(counts[key] == 1 for key in required) and all(counts[key] <= 1 for key in optional)
    return result


def checked_query_filter[FilterT: BaseFilter](request: Request, filters: FilterT) -> FilterT:
    """Retain a typed GET filter after validating the original query shape.

    Args:
        request: Request preserving duplicate query parameters.
        filters: Already validated FastAPI query model.
    Return:
        The same typed filter with source key multiplicity verified.
    """
    filter_schema: type[BaseFilter] = filters.__class__
    fields = filter_schema.model_fields
    required = tuple(field.alias or name for name, field in fields.items() if field.is_required())
    optional = tuple(
        field.alias or name for name, field in fields.items() if not field.is_required()
    )
    if not query_shape_matches(params=request.query_params, required=required, optional=optional):
        issue = QueryShapeIssue(
            type="query_shape",
            loc=("query",),
            msg="Query keys must match their required or optional multiplicity",
            input=str(request.query_params),
        )
        raise RequestValidationError([issue])
    result = filters
    return result
