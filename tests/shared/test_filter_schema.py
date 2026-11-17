from typing import Annotated

from pydantic import Field

from app.shared.filter_module.base_filter import BaseFilter


class _WireQueryFilter(BaseFilter):
    source_revision: Annotated[
        int | None, Field(alias="sourceRevision", description="Optional source revision.")
    ] = None
    include_done: Annotated[
        bool | None, Field(alias="includeDone", description="Include completed observations.")
    ] = None


def test_query_serialization_preserves_aliases_zero_false_and_omission() -> None:
    cases: dict[str, tuple[_WireQueryFilter, dict[str, str]]] = {
        "explicit_values": (
            _WireQueryFilter(sourceRevision=0, includeDone=False),
            {"sourceRevision": "0", "includeDone": "false"},
        ),
        "omitted_values": (_WireQueryFilter(), {}),
    }
    for filters, expected in cases.values():
        assert filters.to_query_params() == expected
