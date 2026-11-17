from collections import OrderedDict
from threading import Lock
from time import perf_counter
from typing import Annotated

from fastapi import status as http_status_codes
from pydantic import Field

from app.shared.base_schema import StrictSchemaModel
from app.shared.ingredient_element.gateway.request_trace_enums import (
    ContractName,
    FailureScenario,
    UpstreamOutcome,
)
from app.shared.types.base_types import JsonValue

__all__ = [
    "ContractIssue",
    "ContractName",
    "ContractValidationResponse",
    "FailureScenario",
    "RequestTrace",
    "TraceEvent",
    "TraceSnapshot",
    "TraceStore",
]


class ContractIssue(StrictSchemaModel):
    loc: Annotated[list[str], Field(description="Path to the invalid field.")]
    message: Annotated[str, Field(description="Validation failure description.")]
    type: Annotated[str, Field(description="Pydantic validation error type.")]


class ContractValidationResponse(StrictSchemaModel):
    contract: Annotated[ContractName, Field(description="Public response contract validated.")]
    valid: Annotated[bool, Field(description="Whether the JSON payload matches the contract.")]
    errors: Annotated[list[ContractIssue], Field(description="Field-level validation errors.")]


class TraceEvent(StrictSchemaModel):
    name: Annotated[str, Field(description="Request stage or upstream name.")]
    start_ms: Annotated[float, Field(description="Offset from BFF request start.")]
    duration_ms: Annotated[float, Field(description="Stage duration in milliseconds.")]
    status: Annotated[str, Field(description="Stage result state.")]
    http_status: Annotated[int | None, Field(description="Upstream HTTP status when available.")]
    raw: Annotated[
        JsonValue | None, Field(description="Unmodified upstream JSON or response text.")
    ]
    error: Annotated[str | None, Field(description="Failure detail, if any.")]


class TraceSnapshot(StrictSchemaModel):
    trace_id: Annotated[str, Field(description="Unique request trace identifier.")]
    elapsed_ms: Annotated[float, Field(description="Total request duration.")]
    bff_http_status: Annotated[int, Field(description="Final BFF response status.")]
    events: Annotated[list[TraceEvent], Field(description="Ordered request waterfall events.")]
    raw: Annotated[dict[str, JsonValue], Field(description="Raw upstream payloads by service.")]
    inner_dto: Annotated[
        JsonValue | None, Field(description="Normalized internal DTO representation.")
    ]
    public_response: Annotated[
        JsonValue | None, Field(description="Public response representation.")
    ]


class RequestTrace:
    def __init__(self, trace_id: str) -> None:
        """Start a trace for one existing BFF request.

        Args:
            trace_id: Unique identifier for the incoming request.
        Return:
            None.
        """
        self.trace_id = trace_id
        self._started = perf_counter()
        self._events: list[TraceEvent] = []
        self._raw: dict[str, JsonValue] = {}
        self._status = 500
        self._inner_dto: JsonValue | None = None
        self._public_response: JsonValue | None = None

    def record_upstream(
        self,
        service_name: str,
        started: float,
        duration_ms: float,
        http_status: int | None,
        raw: JsonValue | None,
        error: str | None,
    ) -> None:
        """Record an upstream call without changing its payload.

        Args:
            service_name: Upstream service name.
            started: Monotonic start time of the call.
            duration_ms: Total call duration in milliseconds.
            http_status: HTTP status returned by the upstream.
            raw: Raw JSON response or response text.
            error: Failure description when the call failed.
        Return:
            None.
        """
        state = "success" if error is None else "failed"
        self._events.append(
            TraceEvent(
                name=f"BFF -> {service_name}",
                start_ms=max(0, (started - self._started) * 1000),
                duration_ms=duration_ms,
                status=state,
                http_status=http_status,
                raw=raw,
                error=error,
            )
        )
        if raw is not None:
            self._raw[service_name] = raw

    def record_stage(
        self,
        name: str,
        started: float,
        status: str,
        error: str | None = None,
    ) -> None:
        """Record one BFF processing stage.

        Args:
            name: Stage label.
            started: Monotonic stage start time.
            status: Stage result.
            error: Optional failure description.
        Return:
            None.
        """
        ended = perf_counter()
        self._events.append(
            TraceEvent(
                name=name,
                start_ms=max(0, (started - self._started) * 1000),
                duration_ms=(ended - started) * 1000,
                status=status,
                http_status=None,
                raw=None,
                error=error,
            )
        )

    def record_upstream_outcome(
        self,
        service_name: str,
        outcome: UpstreamOutcome,
        error: str | None,
    ) -> None:
        """Record the semantic outcome of the latest matching upstream exchange.

        Args:
            service_name: Upstream service associated with the exchange.
            outcome: Observed result, including an unresolved command outcome.
            error: Sanitized explanation when the outcome needs attention.
        Return:
            None.
        """
        event_name = f"BFF -> {service_name}"
        for index in range(len(self._events) - 1, -1, -1):
            event = self._events[index]
            if event.name == event_name:
                self._events[index] = TraceEvent(
                    name=event.name,
                    start_ms=event.start_ms,
                    duration_ms=event.duration_ms,
                    status=outcome.value,
                    http_status=event.http_status,
                    raw=event.raw,
                    error=error,
                )
                break

    def finish(
        self,
        status: int,
        inner_dto: JsonValue | None,
        public_response: JsonValue | None,
    ) -> None:
        """Set the final result for the request trace.

        Args:
            status: Final BFF HTTP status.
            inner_dto: Normalized internal representation.
            public_response: Final public representation.
        Return:
            None.
        """
        self._status = status
        self._inner_dto = inner_dto
        self._public_response = public_response
        elapsed_ms = (perf_counter() - self._started) * 1000
        result_status = (
            UpstreamOutcome.SUCCESS.value if status < 400 else UpstreamOutcome.FAILED.value
        )
        if status == http_status_codes.HTTP_202_ACCEPTED:
            result_status = UpstreamOutcome.UNKNOWN.value
        self._events.extend(
            [
                TraceEvent(
                    name="Client -> BFF",
                    start_ms=0,
                    duration_ms=0,
                    status="received",
                    http_status=None,
                    raw=None,
                    error=None,
                ),
                TraceEvent(
                    name="BFF -> Client",
                    start_ms=elapsed_ms,
                    duration_ms=0,
                    status=result_status,
                    http_status=status,
                    raw=None,
                    error=None,
                ),
            ]
        )

    def snapshot(self) -> TraceSnapshot:
        """Create an immutable API representation of the trace.

        Args:
            None.
        Return:
            Completed request trace snapshot.
        """
        ordered_events = sorted(self._events, key=lambda event: event.start_ms)
        snapshot = TraceSnapshot(
            trace_id=self.trace_id,
            elapsed_ms=(perf_counter() - self._started) * 1000,
            bff_http_status=self._status,
            events=ordered_events,
            raw=self._raw,
            inner_dto=self._inner_dto,
            public_response=self._public_response,
        )
        return snapshot


class TraceStore:
    def __init__(self, capacity: int) -> None:
        """Create a bounded in-memory trace store.

        Args:
            capacity: Maximum retained request traces.
        Return:
            None.
        """
        self._lock = Lock()
        self._capacity = capacity
        self._traces: OrderedDict[str, TraceSnapshot] = OrderedDict()

    def record(self, snapshot: TraceSnapshot) -> None:
        """Store the latest snapshot and evict the oldest when full.

        Args:
            snapshot: Completed request snapshot.
        Return:
            None.
        """
        with self._lock:
            self._traces[snapshot.trace_id] = snapshot
            self._traces.move_to_end(snapshot.trace_id)
            while len(self._traces) > self._capacity:
                self._traces.popitem(last=False)

    def find(self, trace_id: str) -> TraceSnapshot | None:
        """Find a retained request trace.

        Args:
            trace_id: Trace identifier to look up.
        Return:
            Snapshot if it remains in the bounded store.
        """
        with self._lock:
            result = self._traces.get(trace_id)
        return result
