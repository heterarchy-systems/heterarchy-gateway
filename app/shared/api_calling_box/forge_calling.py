"""Forge API caller inheriting BaseCalling."""

from collections.abc import Mapping
from typing import override
from urllib.parse import quote
from uuid import UUID

import httpx

from app.shared.api_calling_box.base_calling import BaseCalling
from app.shared.diagnostics.request_trace import FailureScenario, RequestTrace
from app.shared.exception import ForgeExcept
from app.shared.ingredient_element.forge.forge_enums import ForgeCommandOpEnum
from app.shared.ingredient_element.gateway.request_trace_enums import UpstreamOutcome
from app.shared.types.base_types import JsonValue
from app.shared.types.upstream_exchange import UpstreamJsonExchange


class ForgeCalling(BaseCalling):
    """HTTP caller for the upstream Forge service."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        trace: RequestTrace | None = None,
        failure_scenario: FailureScenario | None = None,
        *,
        authorization: str | None = None,
    ) -> None:
        """Initialize the Forge API caller.

        Args:
            client: Shared asynchronous HTTP client.
            base_url: Root URL for the upstream Forge API.
            trace: Optional request-scoped trace recorder.
            failure_scenario: Optional development failure injection.
            authorization: Optional request-scoped bearer authorization value.
        Return:
            None.
        """
        super().__init__(
            client,
            base_url,
            "forge",
            trace,
            failure_scenario,
            authorization=authorization,
        )

    async def call_command(
        self,
        op: ForgeCommandOpEnum,
        request_id: UUID,
        envelope: Mapping[str, JsonValue],
    ) -> UpstreamJsonExchange:
        """Execute one versioned Forge command and preserve its HTTP status.

        Args:
            op: Closed Forge command operation used in the endpoint path.
            request_id: Caller-supplied request identity to retain on transport failures.
            envelope: Typed Forge command request envelope.
        Return:
            Upstream status and decoded JSON value.
        """
        try:
            result = await self.execute_json_exchange(
                method="POST",
                path=f"/commands/{quote(op.value, safe='')}",
                body=envelope,
            )
        except ForgeExcept as error:
            raise ForgeExcept(
                status_code=error.status_code,
                code=error.code,
                message=error.message,
                retryable=False,
                request_id=request_id,
            ) from error
        return result

    def record_unknown_outcome(self) -> None:
        """Mark the latest Forge exchange as an unresolved admitted command.

        Args:
            None.
        Return:
            None.
        """
        if self._trace is not None:
            self._trace.record_upstream_outcome(
                "forge",
                UpstreamOutcome.UNKNOWN,
                "Forge returned UNKNOWN_OUTCOME; readback is required",
            )

    def with_trace(
        self,
        trace: RequestTrace,
        failure_scenario: FailureScenario | None = None,
    ) -> ForgeCalling:
        """Create a request-traced Forge caller sharing this client and base URL.

        Args:
            trace: Request-scoped trace recorder.
            failure_scenario: Optional development failure injection scenario.
        Return:
            Configured ForgeCalling bound to the trace.
        """
        caller = ForgeCalling(
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
    ) -> ForgeExcept:
        """Construct a ForgeExcept for upstream Forge failures.

        Args:
            status_code: Public HTTP status code to emit.
            code: Stable machine-readable error code.
            message: Sanitized error explanation.
            retryable: Whether callers may retry the failed request.
        Return:
            Structured ForgeExcept instance.
        """
        result = ForgeExcept(
            status_code=status_code,
            code=code,
            message=message,
            retryable=retryable,
        )
        return result
