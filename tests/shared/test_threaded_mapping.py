"""Regression tests for bounded immutable-value mapping."""

from dataclasses import dataclass

import pytest

from app.shared.types.threaded_mapping import threaded_map


@dataclass(frozen=True, slots=True, kw_only=True)
class _ValueDto:
    value: int


def _double_value(value: _ValueDto) -> int:
    return value.value * 2


def _fail_on_five(value: _ValueDto) -> int:
    if value.value == 5:
        raise ValueError("conversion failed")
    return value.value


def test_threaded_map_preserves_order_below_and_at_parallel_threshold() -> None:
    mapping_cases: dict[str, tuple[tuple[_ValueDto, ...], tuple[int, ...]]] = {
        "below_threshold": (
            tuple(_ValueDto(value=index) for index in range(7)),
            (0, 2, 4, 6, 8, 10, 12),
        ),
        "at_threshold": (
            tuple(_ValueDto(value=index) for index in range(8)),
            (0, 2, 4, 6, 8, 10, 12, 14),
        ),
        "large_batch": (
            tuple(_ValueDto(value=index) for index in range(128)),
            tuple(index * 2 for index in range(128)),
        ),
    }

    for values, expected in mapping_cases.values():
        assert threaded_map(_double_value, values) == list(expected)


def test_threaded_map_propagates_parallel_conversion_errors() -> None:
    values = tuple(_ValueDto(value=index) for index in range(8))

    with pytest.raises(ValueError, match="conversion failed"):
        threaded_map(_fail_on_five, values)
