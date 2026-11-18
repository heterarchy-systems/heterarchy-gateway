"""Shared HTTP calling base for outbound BFF requests."""

import asyncio
from collections.abc import AsyncIterator, Mapping
from time import perf_counter

import httpx
from fastapi import status
from pydantic import ValidationError

from app.shared.diagnostics.request_trace import FailureScenario, RequestTrace
from app.shared.exception import BaseExcept
from app.shared.ingredient_element.gateway.request_trace_enums import UpstreamOutcome
from app.shared.types.base_types import JsonValue
from app.shared.types.json_contract import decode_json, encode_json
from app.shared.types.upstream_exchange import (
    DEFAULT_UPSTREAM_EXCHANGE_POLICY,
    UpstreamExchangePolicy,
    UpstreamJsonExchange,
)

_MAX_UPSTREAM_RESPONSE_BYTES = DEFAULT_UPSTREAM_EXCHANGE_POLICY.max_response_bytes
_UPSTREAM_RESPONSE_CHUNK_BYTES = 65_536
_UNCERTAIN_MUTATION_METHODS = ("POST", "PUT", "PATCH", "DELETE")
_UNCERTAIN_MUTATION_ERRORS: tuple[type[Exception], ...] = (
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
    TimeoutError,
)


class _UpstreamResponseTooLargeError(ValueError):
    """Signal that a streamed upstream response exceeded its byte bound."""


class _UpstreamRequestTooLargeError(ValueError):
    """Signal that an encoded request body exceeded its byte bound."""


class _UnsupportedResponseEncodingError(ValueError):
    """Signal that an upstream response used unsupported content encoding."""


_FAILURE_RESPONSES: dict[tuple[FailureScenario | None, str], tuple[int, bytes]] = {
    (FailureScenario.FORGE_500, "forge"): (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        b'{"message":"Simulated Forge error"}',
    ),
    (FailureScenario.INVALID_JSON, "forge"): (status.HTTP_200_OK, b"{invalid json"),
}
_FAILURE_EXCEPTIONS: dict[tuple[FailureScenario | None, str], type[httpx.RequestError]] = {
    (FailureScenario.FORGE_TIMEOUT, "forge"): httpx.ReadTimeout,
    (FailureScenario.ORCHESTRATION_UNAVAILABLE, "orchestration"): httpx.ConnectError,
}
_FAILURE_DELAYS: dict[tuple[FailureScenario | None, str], float] = {
    (FailureScenario.SLOW_FORGE_3S, "forge"): 3.0,
}


async def provide_http_client(
    timeout_seconds: float,
    max_connections: int,
    max_keepalive_connections: int,
) -> AsyncIterator[httpx.AsyncClient]:
    """Provide a bounded asynchronous HTTP client for upstream requests."""
    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
    )
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds),
        limits=limits,
    ) as client:
        yield client


class BaseCalling:
    """Shared upstream API calling base handling GET, POST, PUT, and DELETE JSON exchanges."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        service_name: str,
        trace: RequestTrace | None = None,
        failure_scenario: FailureScenario | None = None,
        *,
        authorization: str | None = None,
    ) -> None:
        """Initialize an upstream API caller.

        Args:
            client: Shared asynchronous HTTP client.
            base_url: Root URL for the upstream API.
            service_name: Name used in request traces.
            trace: Optional request-scoped trace recorder.
            failure_scenario: Optional development failure injection.
            authorization: Optional request-scoped downstream authorization value.
        Return:
            None.
        """
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._service_name = service_name
        self._trace = trace
        self._failure_scenario = failure_scenario
        self._authorization = authorization

    async def execute_json_exchange(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        body: Mapping[str, JsonValue] | None = None,
        policy: UpstreamExchangePolicy = DEFAULT_UPSTREAM_EXCHANGE_POLICY,
    ) -> UpstreamJsonExchange:
        """Send one JSON exchange while preserving its HTTP status and root value.

        Args:
            method: HTTP method to issue.
            path: Relative upstream endpoint path.
            params: Optional query parameters for the request.
            body: Optional typed JSON request object.
            policy: Request-local byte bounds and optional total deadline.
        Return:
            Decoded payload together with the exact upstream status code.
        """
        try:
            response, payload = await self._run_json_exchange(
                method=method,
                path=path,
                params=params,
                body=body,
                policy=policy,
            )
        except _UpstreamRequestTooLargeError as error:
            self._record_upstream_outcome(
                outcome=UpstreamOutcome.FAILED,
                error="request body exceeded byte limit",
            )
            raise self._build_upstream_exception(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                code=f"{self._service_name}_request_too_large",
                message=f"Upstream {self._service_name} request exceeded its size limit",
                retryable=False,
            ) from error
        except _UpstreamResponseTooLargeError as error:
            self._record_upstream_outcome(
                outcome=UpstreamOutcome.FAILED,
                error="response body exceeded byte limit",
            )
            raise self._build_upstream_exception(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=f"{self._service_name}_response_too_large",
                message=f"Upstream {self._service_name} response exceeded its size limit",
                retryable=False,
            ) from error
        except _UnsupportedResponseEncodingError as error:
            self._record_upstream_outcome(
                outcome=UpstreamOutcome.FAILED,
                error="response used unsupported content encoding",
            )
            raise self._build_upstream_exception(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=f"{self._service_name}_unsupported_content_encoding",
                message=f"Upstream {self._service_name} response used unsupported content encoding",
                retryable=False,
            ) from error
        except TimeoutError as error:
            self._record_uncertain_transport_outcome(method=method, error=error)
            raise self._build_upstream_exception(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                code=f"{self._service_name}_timeout",
                message=f"Upstream {self._service_name} request timed out",
                retryable=method.upper() == "GET",
            ) from error
        except httpx.TimeoutException as error:
            self._record_uncertain_transport_outcome(method=method, error=error)
            raise self._build_upstream_exception(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                code=f"{self._service_name}_timeout",
                message=f"Upstream {self._service_name} request timed out",
                retryable=method.upper() == "GET",
            ) from error
        except httpx.HTTPError as error:
            self._record_uncertain_transport_outcome(method=method, error=error)
            raise self._build_upstream_exception(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=f"{self._service_name}_transport_error",
                message=f"Upstream {self._service_name} transport failed",
                retryable=method.upper() == "GET",
            ) from error
        except (ValidationError, ValueError) as error:
            self._record_upstream_outcome(outcome=UpstreamOutcome.FAILED, error=str(error))
            raise self._build_upstream_exception(
                status_code=status.HTTP_502_BAD_GATEWAY,
                code=f"{self._service_name}_invalid_payload",
                message=f"Upstream {self._service_name} returned an invalid JSON payload",
                retryable=False,
            ) from error
        result = UpstreamJsonExchange(status_code=response.status_code, payload=payload)
        return result

    async def _run_json_exchange(
        self,
        method: str,
        path: str,
        params: Mapping[str, str] | None,
        body: Mapping[str, JsonValue] | None,
        policy: UpstreamExchangePolicy,
    ) -> tuple[httpx.Response, JsonValue]:
        """Run transport and decoding under the optional total deadline.

        Args:
            method: HTTP method to issue.
            path: Relative upstream endpoint path.
            params: Optional query parameters for the request.
            body: Optional typed JSON request object.
            policy: Request-local byte bounds and deadline.
        Return:
            Buffered response and decoded JSON root value.
        """
        if policy.timeout_seconds is None:
            response = await self._request(
                method=method,
                path=path,
                params=params,
                body=body,
                policy=policy,
            )
        else:
            async with asyncio.timeout(policy.timeout_seconds):
                response = await self._request(
                    method=method,
                    path=path,
                    params=params,
                    body=body,
                    policy=policy,
                )
        payload = decode_json(payload=response.content)
        result = response, payload
        return result

    def _record_upstream_outcome(
        self,
        outcome: UpstreamOutcome,
        error: str,
    ) -> None:
        """Update the latest trace outcome when the exchange needs attention.

        Args:
            outcome: Semantic outcome for the latest upstream exchange.
            error: Sanitized explanation associated with the outcome.
        Return:
            None.
        """
        if self._trace is None:
            return
        self._trace.record_upstream_outcome(
            service_name=self._service_name, outcome=outcome, error=error
        )

    def _record_uncertain_transport_outcome(
        self,
        method: str,
        error: Exception,
    ) -> None:
        """Mark an unobserved mutation transport result without claiming admission.

        Args:
            method: HTTP method of the upstream request.
            error: Timeout or transport error that may follow request dispatch.
        Return:
            None.
        """
        if self._trace is None:
            return
        uncertain_mutation = method.upper() in _UNCERTAIN_MUTATION_METHODS and isinstance(
            error, _UNCERTAIN_MUTATION_ERRORS
        )
        if uncertain_mutation:
            self._trace.record_upstream_outcome(
                service_name=self._service_name,
                outcome=UpstreamOutcome.UNKNOWN,
                error="Request outcome is unknown because no response was observed",
            )

    def _build_upstream_exception(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool,
    ) -> BaseExcept:
        """Construct the domain exception raised for upstream call failures.

        Args:
            status_code: Public HTTP status code to emit.
            code: Stable machine-readable error code.
            message: Sanitized error explanation.
            retryable: Whether callers may retry the failed request.
        Return:
            Structured gateway exception instance.
        """
        result = BaseExcept(
            status_code=status_code,
            code=code,
            message=message,
            retryable=retryable,
        )
        return result

    async def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, str] | None = None,
        body: Mapping[str, JsonValue] | None = None,
        *,
        policy: UpstreamExchangePolicy = DEFAULT_UPSTREAM_EXCHANGE_POLICY,
    ) -> httpx.Response:
        """Send an upstream request and capture its raw response and timing.

        Args:
            method: HTTP method to send.
            path: Relative endpoint path.
            params: Optional query parameters for the request.
            body: Optional JSON request object.
            policy: Request-local byte bounds and deadline.
        Return:
            Upstream HTTP response.
        """
        started = perf_counter()
        response: httpx.Response | None = None
        error: str | None = None
        try:
            response = await self._send_request(
                method=method, path=path, params=params, body=body, policy=policy
            )
            if response.status_code >= status.HTTP_400_BAD_REQUEST:
                error = response.text
        except _UpstreamRequestTooLargeError:
            error = "Upstream request body exceeded byte limit"
            raise
        except _UpstreamResponseTooLargeError:
            error = "Upstream response body exceeded byte limit"
            raise
        except _UnsupportedResponseEncodingError:
            error = "Upstream response used unsupported content encoding"
            raise
        except asyncio.CancelledError:
            error = "Upstream request was cancelled"
            raise
        except Exception as exception:
            error = str(exception)
            raise
        finally:
            self._record_request(started=started, response=response, error=error)
        result = response
        return result

    def _record_request(
        self,
        started: float,
        response: httpx.Response | None,
        error: str | None,
    ) -> None:
        """Persist the upstream outcome when this request is being traced.

        Args:
            started: Monotonic request start time.
            response: HTTP response if one was received.
            error: Request failure detail, if any.
        Return:
            None.
        """
        if self._trace is None:
            return
        raw: JsonValue | None = None
        http_status: int | None = None
        if response is not None:
            http_status = response.status_code
            try:
                raw = decode_json(payload=response.content)
            except ValidationError, ValueError:
                raw = response.text
        self._trace.record_upstream(
            service_name=self._service_name,
            started=started,
            duration_ms=(perf_counter() - started) * 1000,
            http_status=http_status,
            raw=raw,
            error=error,
        )

    async def _send_request(
        self,
        method: str,
        path: str,
        params: Mapping[str, str] | None,
        body: Mapping[str, JsonValue] | None,
        policy: UpstreamExchangePolicy,
    ) -> httpx.Response:
        """Send an actual request or its configured failure response.

        Args:
            method: HTTP method to send.
            path: Relative upstream endpoint path.
            params: Optional query parameters.
            body: Optional JSON request body.
        Return:
            HTTP response from upstream or failure simulator.
        """
        response = await self._apply_failure_scenario(method=method, path=path)
        if response is None:
            request = self._build_http_request(
                method=method, path=path, params=params, body=body, policy=policy
            )
            response = await self._client.send(request, stream=True, auth=None)

        try:
            response_content = await self._read_bounded_response(
                response=response,
                max_response_bytes=policy.max_response_bytes,
            )
            result = httpx.Response(
                response.status_code,
                content=response_content,
                request=response.request,
            )
        finally:
            await response.aclose()
        return result

    def _build_http_request(
        self,
        method: str,
        path: str,
        params: Mapping[str, str] | None,
        body: Mapping[str, JsonValue] | None,
        policy: UpstreamExchangePolicy,
    ) -> httpx.Request:
        """Build one request with isolated credentials and optional phase timeout.

        Args:
            method: HTTP method to issue.
            path: Relative upstream endpoint path.
            params: Optional query parameters for the request.
            body: Optional typed JSON request object.
            policy: Request-local byte bounds and deadline.
        Return:
            Built HTTP request without inherited authentication or cookies.
        """
        content = self._encode_request_body(body=body, max_request_bytes=policy.max_request_bytes)
        headers = self._build_request_headers(body=body)
        if policy.timeout_seconds is None:
            request = self._client.build_request(
                method,
                f"{self._base_url}{path}",
                params=params,
                content=content,
                headers=headers,
            )
        else:
            request = self._client.build_request(
                method,
                f"{self._base_url}{path}",
                params=params,
                content=content,
                headers=headers,
                timeout=httpx.Timeout(policy.timeout_seconds),
            )
        request.headers.pop("authorization", None)
        request.headers.pop("cookie", None)
        if self._authorization is not None:
            request.headers["authorization"] = self._authorization
        return request

    @staticmethod
    def _encode_request_body(
        body: Mapping[str, JsonValue] | None,
        max_request_bytes: int | None,
    ) -> bytes | None:
        """Encode a typed JSON request and enforce its optional byte limit.

        Args:
            body: Optional typed JSON request object.
            max_request_bytes: Maximum encoded bytes, if the operation has a limit.
        Return:
            Encoded JSON bytes or None when the request has no body.
        """
        content = encode_json(value=body) if body is not None else None
        if (
            content is not None
            and max_request_bytes is not None
            and len(content) > max_request_bytes
        ):
            raise _UpstreamRequestTooLargeError
        return content

    def _build_request_headers(
        self,
        body: Mapping[str, JsonValue] | None,
    ) -> httpx.Headers:
        """Build request-local content and authorization headers.

        Args:
            body: Optional JSON body indicating whether a content type is needed.
        Return:
            Headers isolated to this upstream request.
        """
        headers = httpx.Headers()
        headers["accept-encoding"] = "identity"
        if body is not None:
            headers["content-type"] = "application/json"
        return headers

    async def _read_bounded_response(
        self,
        response: httpx.Response,
        max_response_bytes: int,
    ) -> bytes:
        """Read an upstream body in bounded chunks.

        Args:
            response: Open streaming HTTP response.
            max_response_bytes: Maximum number of response bytes to buffer.
        Return:
            Fully buffered response body within the shared byte limit.
        """
        content_encoding = response.headers.get("content-encoding", "identity")
        if content_encoding.strip().lower() != "identity":
            raise _UnsupportedResponseEncodingError
        content = bytearray()
        async for chunk in response.aiter_bytes(chunk_size=_UPSTREAM_RESPONSE_CHUNK_BYTES):
            if len(content) + len(chunk) > max_response_bytes:
                raise _UpstreamResponseTooLargeError
            content.extend(chunk)
        result = bytes(content)
        return result

    async def _apply_failure_scenario(
        self,
        method: str,
        path: str,
    ) -> httpx.Response | None:
        """Return the selected mock response or raise a transport failure.

        Args:
            method: HTTP method for the outbound request.
            path: Relative upstream request path.
        Return:
            Mock response when the scenario represents an HTTP response.
        """
        scenario_key = (self._failure_scenario, self._service_name)
        delay_seconds = _FAILURE_DELAYS.get(scenario_key, 0.0)
        await asyncio.sleep(delay_seconds)
        request = httpx.Request(method, f"{self._base_url}{path}")
        response_config = _FAILURE_RESPONSES.get(scenario_key)
        if response_config is not None:
            status_code, content = response_config
            response = httpx.Response(status_code, content=content, request=request)
            return response
        exception_type = _FAILURE_EXCEPTIONS.get(scenario_key)
        if exception_type is not None:
            raise exception_type(f"Simulated {self._service_name} transport failure")
        return None
