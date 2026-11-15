"""Shared HTTP calling base for outbound BFF requests."""

import asyncio
from collections.abc import AsyncIterator, Mapping
from time import perf_counter

import httpx
from pydantic import ValidationError

from app.shared.diagnostics.request_trace import FailureScenario, RequestTrace
from app.shared.exception import BaseExcept
from app.shared.types.base_types import JsonObject, JsonValue
from app.shared.types.json_contract import decode_json, encode_json

_FAILURE_RESPONSES: dict[tuple[FailureScenario | None, str], tuple[int, bytes]] = {
    (FailureScenario.FORGE_500, "forge"): (500, b'{"message":"Simulated Forge error"}'),
    (FailureScenario.INVALID_JSON, "forge"): (200, b"{invalid json"),
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
    ) -> None:
        """Initialize an upstream API caller.

        Args:
            client: Shared asynchronous HTTP client.
            base_url: Root URL for the upstream API.
            service_name: Name used in request traces.
            trace: Optional request-scoped trace recorder.
            failure_scenario: Optional development failure injection.
        Return:
            None.
        """
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._service_name = service_name
        self._trace = trace
        self._failure_scenario = failure_scenario

    async def fetch_json(
        self,
        path: str,
        params: Mapping[str, str] | None = None,
    ) -> JsonObject:
        """Fetch and decode an upstream JSON object.

        Args:
            path: Relative endpoint path.
            params: Optional query parameters for the request.
        Return:
            Decoded JSON object.
        """
        payload = await self._execute_json("GET", path, params=params)
        return payload

    async def post_json(
        self,
        path: str,
        body: JsonObject,
    ) -> JsonObject:
        """Post a JSON object and decode the response.

        Args:
            path: Relative endpoint path.
            body: JSON request object.
        Return:
            Decoded JSON response object.
        """
        payload = await self._execute_json("POST", path, body=body)
        return payload

    async def put_json(
        self,
        path: str,
        body: JsonObject,
    ) -> JsonObject:
        """Put a JSON object and decode the response.

        Args:
            path: Relative endpoint path.
            body: JSON request object.
        Return:
            Decoded JSON response object.
        """
        payload = await self._execute_json("PUT", path, body=body)
        return payload

    async def delete_json(self, path: str) -> JsonObject:
        """Delete an upstream resource and decode the response.

        Args:
            path: Relative endpoint path.
        Return:
            Decoded JSON response object.
        """
        payload = await self._execute_json("DELETE", path)
        return payload

    async def _execute_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
        body: JsonObject | None = None,
    ) -> JsonObject:
        """Execute an upstream JSON exchange and map transport or payload failures.

        Args:
            method: HTTP method to issue.
            path: Relative endpoint path.
            params: Optional query parameters.
            body: Optional JSON request body.
        Return:
            Decoded JSON object.
        """
        try:
            response = await self._request(method, path, params=params, body=body)
            payload = self._decode_response(response)
        except httpx.TimeoutException as error:
            raise self._build_upstream_exception(
                504,
                f"{self._service_name}_timeout",
                f"Upstream {self._service_name} request timed out",
                retryable=True,
            ) from error
        except httpx.HTTPStatusError as error:
            upstream_status = error.response.status_code
            public_status = 404 if upstream_status == 404 else 502
            raise self._build_upstream_exception(
                public_status,
                f"{self._service_name}_http_{upstream_status}",
                f"Upstream {self._service_name} returned HTTP {upstream_status}",
                retryable=upstream_status >= 500,
            ) from error
        except httpx.HTTPError as error:
            raise self._build_upstream_exception(
                502,
                f"{self._service_name}_transport_error",
                f"Upstream {self._service_name} transport failed",
                retryable=True,
            ) from error
        except (ValidationError, ValueError) as error:
            raise self._build_upstream_exception(
                502,
                f"{self._service_name}_invalid_payload",
                f"Upstream {self._service_name} returned an invalid JSON payload",
                retryable=False,
            ) from error
        result = payload
        return result

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
            status_code,
            code,
            message,
            retryable=retryable,
        )
        return result

    async def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, str] | None = None,
        body: JsonObject | None = None,
    ) -> httpx.Response:
        """Send an upstream request and capture its raw response and timing.

        Args:
            method: HTTP method to send.
            path: Relative upstream endpoint path.
            params: Optional query parameters.
            body: Optional JSON request object.
        Return:
            Upstream HTTP response.
        """
        started = perf_counter()
        response: httpx.Response | None = None
        error: str | None = None
        try:
            response = await self._send_request(method, path, params, body)
            if response.status_code >= 400:
                error = response.text
        except Exception as exception:
            error = str(exception)
            raise
        finally:
            self._record_request(started, response, error)
        return response

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
                raw = decode_json(response.content)
            except ValidationError, ValueError:
                raw = response.text
        self._trace.record_upstream(
            self._service_name,
            started,
            (perf_counter() - started) * 1000,
            http_status,
            raw,
            error,
        )

    async def _send_request(
        self,
        method: str,
        path: str,
        params: Mapping[str, str] | None,
        body: JsonObject | None,
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
        mock_response = await self._apply_failure_scenario(method, path)
        if mock_response is not None:
            return mock_response
        headers = {"content-type": "application/json"} if body is not None else None
        content = encode_json(body) if body is not None else None
        request = self._client.build_request(
            method,
            f"{self._base_url}{path}",
            params=params,
            content=content,
            headers=headers,
        )
        response = await self._client.send(request)
        return response

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

    def _decode_response(self, response: httpx.Response) -> JsonObject:
        """Validate an HTTP response and decode its JSON object.

        Args:
            response: Response returned by the upstream HTTP request.
        Return:
            Decoded JSON object from a successful response.
        """
        response.raise_for_status()
        try:
            decoded_payload = decode_json(response.content)
        except (ValidationError, ValueError) as error:
            if self._trace is not None:
                self._trace.fail_upstream(self._service_name, str(error))
            raise
        payload = self._decode_object(decoded_payload)
        return payload

    @staticmethod
    def _decode_object(payload: JsonValue) -> JsonObject:
        """Require a JSON object response.

        Args:
            payload: Decoded JSON value.
        Return:
            JSON object with string keys.
        """
        if not isinstance(payload, dict):
            raise ValueError("Expected the upstream API to return a JSON object")
        decoded: JsonObject = {}
        for key, value in payload.items():
            if not isinstance(key, str):
                raise ValueError("Expected the upstream JSON object to use string keys")
            decoded[key] = value
        return decoded
