"""Orchestration API caller inheriting BaseCalling."""

from typing import override

import httpx

from app.shared.api_calling_box.base_calling import BaseCalling
from app.shared.diagnostics.request_trace import FailureScenario, RequestTrace
from app.shared.exception import OrchestrationExcept


class OrchestrationCalling(BaseCalling):
    """HTTP caller for the upstream Orchestration service."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        trace: RequestTrace | None = None,
        failure_scenario: FailureScenario | None = None,
        *,
        authorization: str | None = None,
    ) -> None:
        """Initialize the orchestration API caller.

        Args:
            client: Shared asynchronous HTTP client.
            base_url: Root URL for the upstream Orchestration API.
            trace: Optional request-scoped trace recorder.
            failure_scenario: Optional development failure injection.
            authorization: Optional request-scoped bearer authorization value.
        Return:
            None.
        """
        super().__init__(
            client,
            base_url,
            "orchestration",
            trace,
            failure_scenario,
            authorization=authorization,
        )

    def with_trace(
        self,
        trace: RequestTrace,
        failure_scenario: FailureScenario | None = None,
    ) -> OrchestrationCalling:
        """Create a request-traced Orchestration caller sharing this client and base URL.

        Args:
            trace: Request-scoped trace recorder.
            failure_scenario: Optional development failure injection scenario.
        Return:
            Configured OrchestrationCalling bound to the trace.
        """
        caller = OrchestrationCalling(
            client=self._client,
            base_url=self._base_url,
            trace=trace,
            failure_scenario=failure_scenario,
            authorization=self._authorization,
        )
        return caller

    @override
    def _build_upstream_exception(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool,
    ) -> OrchestrationExcept:
        """Construct an OrchestrationExcept for upstream Orchestration failures.

        Args:
            status_code: Public HTTP status code to emit.
            code: Stable machine-readable error code.
            message: Sanitized error explanation.
            retryable: Whether callers may retry the failed request.
        Return:
            Structured OrchestrationExcept instance.
        """
        result = OrchestrationExcept(
            status_code=status_code,
            code=code,
            message=message,
            retryable=retryable,
        )
        return result
