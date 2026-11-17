"""Typed query-validation details consumed by FastAPI's standard error handler."""

from typing import Literal

from typing_extensions import TypedDict


class QueryShapeIssue(TypedDict, total=True, closed=True):
    type: Literal["query_shape"]
    loc: tuple[Literal["query"]]
    msg: str
    input: str
