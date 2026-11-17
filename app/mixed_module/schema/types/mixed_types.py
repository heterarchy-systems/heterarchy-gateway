"""Closed request-validation types for Mixed public routes."""

from typing import Literal

from typing_extensions import TypedDict


class MixedRequestValidationIssue(TypedDict, total=True, closed=True):
    """Pydantic-compatible issue for a path/body context mismatch."""

    type: Literal["value_error"]
    loc: tuple[str, ...]
    msg: str
    input: str
