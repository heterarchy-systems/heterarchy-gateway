"""Closed wire dictionaries owned by the corresponding internal DTOs."""

from typing_extensions import TypedDict

from app.shared.ingredient_element.gateway.upstream_reply_enums import UpstreamReplyKind


class OrchestrationBackendErrorDict(TypedDict, total=True, closed=True):
    code: str
    message: str
    retryable: bool


class OrchestrationOutcomeDict[ResultDictT](TypedDict, total=True, closed=True):
    status_code: int
    body_kind: UpstreamReplyKind
    response: ResultDictT | OrchestrationBackendErrorDict
