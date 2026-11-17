"""Outcome diagnostics retain the distinction between successive upstream calls."""

from time import perf_counter

from app.shared.diagnostics.request_trace import RequestTrace
from app.shared.ingredient_element.gateway.request_trace_enums import UpstreamOutcome


def test_upstream_outcome_updates_only_the_latest_matching_exchange() -> None:
    trace = RequestTrace("outcome-trace")
    exchanges: dict[str, tuple[str, int]] = {
        "earlier_forge_read": ("forge", 200),
        "forge_unknown_outcome": ("forge", 202),
        "orchestration_read": ("orchestration", 200),
    }
    for service, status_code in exchanges.values():
        trace.record_upstream(service, perf_counter(), 1.0, status_code, None, None)

    trace.record_upstream_outcome("forge", UpstreamOutcome.UNKNOWN, "Command outcome is unknown")
    snapshot = trace.snapshot()
    assert [event.status for event in snapshot.events] == ["success", "unknown", "success"]
    assert [event.http_status for event in snapshot.events] == [200, 202, 200]

    trace.finish(202, None, None)
    completed = trace.snapshot()
    assert [event.status for event in completed.events if event.name == "BFF -> Client"] == [
        "unknown"
    ]
