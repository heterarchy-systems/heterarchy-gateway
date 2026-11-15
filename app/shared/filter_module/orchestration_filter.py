"""Pydantic filter schema for orchestration resources."""

from typing import Annotated

from pydantic import Field

from app.shared.filter_module.base_filter import BaseDateFilter
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStatus,
)


class OrchestrationFilter(BaseDateFilter):
    """Represent optional orchestration-list criteria."""

    workflow_name: Annotated[
        str | None,
        Field(description="Optional workflow name to match.", max_length=100),
    ] = None
    status: Annotated[
        OrchestrationStatus | None,
        Field(description="Optional orchestration status to match."),
    ] = None
