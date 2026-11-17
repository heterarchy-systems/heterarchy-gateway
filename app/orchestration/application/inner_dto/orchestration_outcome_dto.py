"""Immutable HTTP response carriers for Orchestration contracts."""

from dataclasses import dataclass

from app.orchestration.application.inner_dto.types.orchestration_outcome_types import (
    OrchestrationBackendErrorDict,
    OrchestrationOutcomeDict,
)
from app.shared.ingredient_element.gateway.upstream_reply_enums import UpstreamReplyKind


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
