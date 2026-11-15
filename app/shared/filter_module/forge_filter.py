"""Pydantic filter schema for forge resources."""

from typing import Annotated

from pydantic import Field

from app.shared.filter_module.base_filter import BaseDateFilter


class ForgeFilter(BaseDateFilter):
    """Represent optional forge-list criteria."""

    name: Annotated[
        str | None,
        Field(description="Optional forge name to match.", max_length=100),
    ] = None
