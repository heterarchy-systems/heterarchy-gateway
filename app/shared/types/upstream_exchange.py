"""Typed JSON response metadata for upstream HTTP exchanges."""

from dataclasses import dataclass

from pydantic import JsonValue
from typing_extensions import TypedDict


class UpstreamJsonExchangeDict(TypedDict, total=True, closed=True):
    """Closed mapping representation of one decoded upstream response."""

    status_code: int
    payload: JsonValue


@dataclass(frozen=True, slots=True, kw_only=True)
class UpstreamJsonExchange:
    """Preserve the upstream status and any JSON root value."""

    status_code: int
    payload: JsonValue

    def to_dict(self) -> UpstreamJsonExchangeDict:
        """Create the typed representation for strict schema validation.

        Args:
            None.
        Return:
            Closed JSON exchange mapping.
        """
        result = UpstreamJsonExchangeDict(
            status_code=self.status_code,
            payload=self.payload,
        )
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class UpstreamExchangePolicy:
    """Request-local byte and deadline bounds for one upstream exchange."""

    max_response_bytes: int
    max_request_bytes: int | None
    timeout_seconds: float | None


DEFAULT_UPSTREAM_EXCHANGE_POLICY = UpstreamExchangePolicy(
    max_response_bytes=1_048_576,
    max_request_bytes=None,
    timeout_seconds=None,
)
