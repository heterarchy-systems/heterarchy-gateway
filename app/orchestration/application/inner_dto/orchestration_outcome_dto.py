"""Immutable HTTP response carriers for Orchestration contracts."""

from dataclasses import dataclass

from typing_extensions import TypedDict

from app.shared.ingredient_element.gateway.upstream_reply_enums import UpstreamReplyKind


class OrchestrationBackendErrorDict(TypedDict, total=True, closed=True):
    code: str
    message: str
    retryable: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class OrchestrationBackendErrorDto:
    code: str
    message: str
    retryable: bool

    def to_dict(self) -> OrchestrationBackendErrorDict:
        """Serialize the backend error without adding Gateway transport fields.

        Args:
            None.
        Return:
            Complete backend-owned error response.
        """
        result = OrchestrationBackendErrorDict(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
        )
        return result


class OrchestrationOutcomeDict[ResultDictT](TypedDict, total=True, closed=True):
    status_code: int
    body_kind: UpstreamReplyKind
    response: ResultDictT | OrchestrationBackendErrorDict


@dataclass(frozen=True, slots=True, kw_only=True)
class OrchestrationOutcomeDto[ResultDictT]:
    status_code: int
    body_kind: UpstreamReplyKind
    response: ResultDictT | OrchestrationBackendErrorDict

    def to_dict(self) -> OrchestrationOutcomeDict[ResultDictT]:
        """Expose typed response data for final HTTP-boundary validation.

        Args:
            None.
        Return:
            Status and the exact result or backend-error body.
        """
        result = OrchestrationOutcomeDict[ResultDictT](
            status_code=self.status_code,
            body_kind=self.body_kind,
            response=self.response,
        )
        return result
