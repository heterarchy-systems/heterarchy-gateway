from datetime import date

import pytest
from pydantic import ValidationError

from app.shared.filter_module.forge_filter import ForgeFilter
from app.shared.filter_module.mixed_module_filter import MixedModuleFilter
from app.shared.filter_module.orchestration_filter import OrchestrationFilter
from app.shared.ingredient_element.orchestration.orchestration_status_enum import (
    OrchestrationStatus,
)


def test_query_filters_serialize_and_reject_invalid_date_bounds() -> None:
    filter_cases: dict[str, tuple[ForgeFilter | OrchestrationFilter, dict[str, str]]] = {
        "forge_omits_none": (
            ForgeFilter(name="", created_after=date(2026, 9, 28), created_before=None),
            {"name": "", "created_after": "2026-09-28"},
        ),
        "orchestration_serializes_enum": (
            OrchestrationFilter(workflow_name="nightly-build", status=OrchestrationStatus.RUNNING),
            {"workflow_name": "nightly-build", "status": "running"},
        ),
    }

    for filter_model, expected_params in filter_cases.values():
        assert filter_model.to_query_params() == expected_params

    with pytest.raises(ValidationError):
        ForgeFilter(created_after=date(2026, 10, 10), created_before=date(2026, 10, 1))


def test_mixed_filter_matches_configured_predicates() -> None:
    filters = MixedModuleFilter(
        forge_name="example",
        task_status=OrchestrationStatus.RUNNING,
        created_after=date(2026, 1, 1),
        created_before=date(2026, 12, 31),
    )
    predicate_cases: dict[str, tuple[str, OrchestrationStatus, date, bool]] = {
        "all_match": ("Example Forge", OrchestrationStatus.RUNNING, date(2026, 9, 28), True),
        "name_mismatch": ("Other", OrchestrationStatus.RUNNING, date(2026, 9, 28), False),
        "status_mismatch": ("Example Forge", OrchestrationStatus.FAILED, date(2026, 9, 28), False),
        "date_out_of_range": (
            "Example Forge",
            OrchestrationStatus.RUNNING,
            date(2027, 1, 1),
            False,
        ),
    }

    for forge_name, task_status, created_date, expected in predicate_cases.values():
        assert filters.matches(forge_name, task_status, created_date) is expected

    assert MixedModuleFilter().matches("Any Forge", OrchestrationStatus.QUEUED, date(2026, 5, 1))
