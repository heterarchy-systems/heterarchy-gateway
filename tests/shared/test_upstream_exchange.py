"""Regression coverage for bounded, status-aware upstream exchanges."""

import asyncio
import gzip
import tomllib
from collections import Counter
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.profile_inner_dto import (
    ProfileLifecycleCommandDto,
)
from app.orchestration.application.orchestration_command_utils import (
    ORCHESTRATION_SWARM_EXCHANGE_POLICY,
)
from app.shared.api_calling_box.base_calling import _MAX_UPSTREAM_RESPONSE_BYTES
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.diagnostics.request_trace import RequestTrace
from app.shared.exception import OrchestrationExcept
from app.shared.ingredient_element.gateway.request_trace_enums import ContractName, UpstreamOutcome
from app.shared.ingredient_element.orchestration.realtime_enums import (
    RealtimeFrameByteLimitEnum,
    RealtimeSourceReadTimeoutSecondsEnum,
)
from app.shared.types.base_types import JsonValue
from app.shared.types.json_contract import encode_json
from app.shared.types.upstream_exchange import (
    DEFAULT_UPSTREAM_EXCHANGE_POLICY,
    UpstreamExchangePolicy,
    UpstreamJsonExchange,
)


class _SizedRequestDict(TypedDict, total=True, closed=True):
    """Typed JSON body used to exercise the encoded request byte boundary."""

    payload: str


class _BlockingByteStream(httpx.AsyncByteStream):
    """A cancellable stream that records whether transport cleanup ran."""

    def __init__(self, started: asyncio.Event, closed: asyncio.Event) -> None:
        """Initialize stream lifecycle signals.

        Args:
            started: Event set when iteration begins.
            closed: Event set when the response closes the stream.
        Return:
            None.
        """
        self._started = started
        self._closed = closed
        self._blocked = asyncio.Event()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Block body iteration until the owning task is cancelled.

        Args:
            None.
        Return:
            An asynchronous stream of response bytes.
        """
        self._started.set()
        await self._blocked.wait()
        yield b"unreachable"

    async def aclose(self) -> None:
        """Record that the transport released this response stream.

        Args:
            None.
        Return:
            None.
        """
        self._closed.set()


class _CompressedResponseStream(httpx.AsyncByteStream):
    """A compressed body stream that records iteration and closure."""

    def __init__(
        self,
        body: bytes,
        started: asyncio.Event,
        closed: asyncio.Event,
    ) -> None:
        """Initialize compressed body and stream lifecycle signals.

        Args:
            body: Gzip-compressed JSON response bytes.
            started: Event set if response body iteration begins.
            closed: Event set when the response closes the stream.
        Return:
            None.
        """
        self._body = body
        self._started = started
        self._closed = closed

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Yield the compressed body after recording iteration.

        Args:
            None.
        Return:
            An asynchronous stream containing the gzip body.
        """
        self._started.set()
        yield self._body

    async def aclose(self) -> None:
        """Record that the transport released this response stream.

        Args:
            None.
        Return:
            None.
        """
        self._closed.set()


def test_json_exchange_preserves_statuses_root_arrays_and_typed_bodies() -> None:
    response_cases: dict[str, tuple[int, JsonValue]] = {
        "/profiles": (200, [{"profile_id": "profile-1"}]),
        "/create": (201, {"created": True}),
        "/replay": (200, {"created": False}),
        "/unknown": (202, {"error": {"code": "UNKNOWN_OUTCOME"}}),
        "/conflict": (409, {"code": "CONFLICT"}),
    }
    captured_bodies: list[bytes] = []
    typed_body = ProfileLifecycleCommandDto(
        request_id=UUID("11111111-1111-1111-1111-111111111111"),
        expected_revision=1,
    ).to_dict()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/create":
            captured_bodies.append(request.content)
        status_code, payload = response_cases[request.url.path]
        result = httpx.Response(status_code, json=payload, request=request)
        return result

    async def exercise_exchanges() -> list[UpstreamJsonExchange]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            caller = OrchestrationCalling(client, "https://orchestration.test")
            profile_list = await caller.execute_json_exchange("GET", "/profiles")
            created = await caller.execute_json_exchange(
                "POST",
                "/create",
                body=typed_body,
            )
            replayed = await caller.execute_json_exchange("POST", "/replay")
            unknown = await caller.execute_json_exchange("POST", "/unknown")
            conflict = await caller.execute_json_exchange("POST", "/conflict")
        result = [profile_list, created, replayed, unknown, conflict]
        return result

    exchanges = asyncio.run(exercise_exchanges())

    assert [exchange.status_code for exchange in exchanges] == [200, 201, 200, 202, 409]
    assert exchanges[0].payload == [{"profile_id": "profile-1"}]
    assert exchanges[3].payload == {"error": {"code": "UNKNOWN_OUTCOME"}}
    assert exchanges[4].to_dict() == {
        "status_code": 409,
        "payload": {"code": "CONFLICT"},
    }
    assert captured_bodies == [
        b'{"requestId":"11111111-1111-1111-1111-111111111111","expectedRevision":1}'
    ]


def test_dedicated_backend_authorization_is_request_scoped() -> None:
    from tests.shared.gateway_test_builder import GatewayTestClientBuilder

    observed: list[tuple[str, str | None]] = []
    request_id = "11111111-1111-1111-1111-111111111111"

    def handler(request: httpx.Request) -> httpx.Response:
        observed.append((request.url.host, request.headers.get("authorization")))
        if request.url.host == "forge.example.test":
            payload: JsonValue = {
                "forge_api": 1,
                "request_id": request_id,
                "ok": True,
                "result": {"entries": []},
            }
        else:
            payload = []
        result = httpx.Response(200, json=payload, request=request)
        return result

    forge_request: JsonValue = {
        "forge_api": 1,
        "request_id": request_id,
        "op": "location.list",
        "payload": {},
    }
    with GatewayTestClientBuilder().with_handler(handler).build_client() as client:
        forge_response = client.post(
            "/forges/locations/list",
            json=forge_request,
            headers={"Authorization": "Bearer forge-dedicated"},
        )
        first_profile_response = client.get(
            "/orchestrations/profiles",
            headers={"Authorization": "Bearer profile-dedicated-1"},
        )
        second_profile_response = client.get(
            "/orchestrations/profiles",
            headers={"Authorization": "Bearer profile-dedicated-2"},
        )

    assert forge_response.status_code == 200
    assert first_profile_response.status_code == 200
    assert second_profile_response.status_code == 200
    assert Counter(observed) == Counter(
        [
            ("forge.example.test", "Bearer forge-dedicated"),
            ("orchestration.example.test", "Bearer profile-dedicated-1"),
            ("orchestration.example.test", "Bearer profile-dedicated-2"),
        ]
    )


def test_upstream_request_ignores_shared_client_credentials() -> None:
    observed_credentials: list[tuple[str | None, str | None]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        observed_credentials.append(
            (
                request.headers.get("authorization"),
                request.headers.get("cookie"),
            )
        )
        result = httpx.Response(200, json={"ok": True}, request=request)
        return result

    async def exercise_requests() -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            headers={"Authorization": "Bearer shared-default"},
            cookies={"session": "shared-cookie"},
            auth=httpx.BasicAuth("shared-user", "shared-password"),
        ) as client:
            anonymous_caller = OrchestrationCalling(
                client,
                "https://orchestration.test",
            )
            bearer_caller = OrchestrationCalling(
                client,
                "https://orchestration.test",
                authorization="Bearer request-scoped",
            )
            await anonymous_caller.execute_json_exchange("GET", "/without-auth")
            await bearer_caller.execute_json_exchange("GET", "/with-auth")

    asyncio.run(exercise_requests())

    assert observed_credentials == [
        (None, None),
        ("Bearer request-scoped", None),
    ]


def test_oversized_exchange_is_sanitized_and_not_recorded_as_raw_trace_data() -> None:
    body = b'"' + b"x" * _MAX_UPSTREAM_RESPONSE_BYTES + b'"'

    def handler(request: httpx.Request) -> httpx.Response:
        result = httpx.Response(200, content=body, request=request)
        return result

    async def exercise_exchange() -> tuple[OrchestrationExcept, RequestTrace]:
        trace = RequestTrace("oversized-response")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            caller = OrchestrationCalling(
                client,
                "https://orchestration.test",
                trace=trace,
            )
            with pytest.raises(OrchestrationExcept) as captured_error:
                await caller.execute_json_exchange("GET", "/large")
        result = captured_error.value, trace
        return result

    error, trace = asyncio.run(exercise_exchange())
    snapshot = trace.snapshot()

    assert error.status_code == 502
    assert error.code == "orchestration_response_too_large"
    assert error.retryable is False
    assert snapshot.events[0].raw is None


def test_mutating_exchange_transport_failure_is_not_retryable() -> None:
    transport_cases: dict[
        str,
        tuple[str, httpx.HTTPError, UpstreamOutcome, int, bool],
    ] = {
        "post_read_timeout": (
            "POST",
            httpx.ReadTimeout("response timeout"),
            UpstreamOutcome.UNKNOWN,
            504,
            False,
        ),
        "post_write_timeout": (
            "POST",
            httpx.WriteTimeout("request timeout"),
            UpstreamOutcome.UNKNOWN,
            504,
            False,
        ),
        "post_read_error": (
            "POST",
            httpx.ReadError("response stream failed"),
            UpstreamOutcome.UNKNOWN,
            502,
            False,
        ),
        "post_write_error": (
            "POST",
            httpx.WriteError("request stream failed"),
            UpstreamOutcome.UNKNOWN,
            502,
            False,
        ),
        "post_remote_protocol_error": (
            "POST",
            httpx.RemoteProtocolError("connection ended without a response"),
            UpstreamOutcome.UNKNOWN,
            502,
            False,
        ),
        "get_read_timeout": (
            "GET",
            httpx.ReadTimeout("response timeout"),
            UpstreamOutcome.FAILED,
            504,
            True,
        ),
        "post_connect_error": (
            "POST",
            httpx.ConnectError("connection could not be established"),
            UpstreamOutcome.FAILED,
            502,
            False,
        ),
    }

    async def exercise_case(
        method: str,
        transport_error: httpx.HTTPError,
        trace_id: str,
    ) -> tuple[OrchestrationExcept, str]:
        def handler(_request: httpx.Request) -> httpx.Response:
            raise transport_error

        trace = RequestTrace(trace_id)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            caller = OrchestrationCalling(
                client,
                "https://orchestration.test",
                trace=trace,
            )
            with pytest.raises(OrchestrationExcept) as captured_error:
                await caller.execute_json_exchange(method, f"/{trace_id}")
        result = captured_error.value, trace.snapshot().events[0].status
        return result

    for trace_id, (
        method,
        transport_error,
        expected_outcome,
        expected_status,
        expected_retryable,
    ) in transport_cases.items():
        error, observed_outcome = asyncio.run(exercise_case(method, transport_error, trace_id))
        assert error.status_code == expected_status
        assert error.retryable is expected_retryable
        assert observed_outcome == expected_outcome.value


def test_cancelled_streaming_exchange_closes_its_response() -> None:
    async def exercise_cancellation() -> bool:
        started = asyncio.Event()
        closed = asyncio.Event()
        stream = _BlockingByteStream(started, closed)

        def handler(request: httpx.Request) -> httpx.Response:
            result = httpx.Response(200, stream=stream, request=request)
            return result

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            caller = OrchestrationCalling(client, "https://orchestration.test")
            pending_exchange = asyncio.create_task(caller.execute_json_exchange("GET", "/slow"))
            await started.wait()
            pending_exchange.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending_exchange
        result = closed.is_set()
        return result

    assert asyncio.run(exercise_cancellation()) is True


def test_compressed_response_is_rejected_before_body_iteration() -> None:
    compressed_body = gzip.compress(b"x" * 16_000_000)
    started = asyncio.Event()
    closed = asyncio.Event()
    stream = _CompressedResponseStream(compressed_body, started, closed)
    accepted_encodings: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        accepted_encodings.append(request.headers["accept-encoding"])
        result = httpx.Response(
            200,
            headers={"content-encoding": "gzip", "content-type": "application/json"},
            stream=stream,
            request=request,
        )
        return result

    async def exercise_exchange() -> tuple[OrchestrationExcept, RequestTrace]:
        trace = RequestTrace("compressed-response")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            caller = OrchestrationCalling(
                client,
                "https://orchestration.test",
                trace=trace,
            )
            with pytest.raises(OrchestrationExcept) as captured_error:
                await caller.execute_json_exchange("GET", "/compressed")
        result = captured_error.value, trace
        return result

    error, trace = asyncio.run(exercise_exchange())

    assert error.status_code == 502
    assert error.code == "orchestration_unsupported_content_encoding"
    assert error.retryable is False
    assert accepted_encodings == ["identity"]
    assert started.is_set() is False
    assert closed.is_set() is True
    assert trace.snapshot().events[0].raw is None


def test_swarm_policy_enforces_encoded_request_body_boundary() -> None:
    request_limit = ORCHESTRATION_SWARM_EXCHANGE_POLICY.max_request_bytes
    assert request_limit is not None
    empty_body = _SizedRequestDict(payload="")
    empty_length = len(encode_json(empty_body))
    request_at_limit = _SizedRequestDict(payload="x" * (request_limit - empty_length))
    request_over_limit = _SizedRequestDict(payload="x" * (request_limit - empty_length + 1))
    assert len(encode_json(request_at_limit)) == request_limit
    assert len(encode_json(request_over_limit)) == request_limit + 1
    sent_body_lengths: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_body_lengths.append(len(request.content))
        result = httpx.Response(200, json={"accepted": True}, request=request)
        return result

    async def exercise_requests() -> OrchestrationExcept:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            caller = OrchestrationCalling(client, "https://orchestration.test")
            await caller.execute_json_exchange(
                "POST",
                "/at-limit",
                body=request_at_limit,
                policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
            )
            with pytest.raises(OrchestrationExcept) as captured_error:
                await caller.execute_json_exchange(
                    "POST",
                    "/over-limit",
                    body=request_over_limit,
                    policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
                )
        result = captured_error.value
        return result

    error = asyncio.run(exercise_requests())

    assert error.status_code == 413
    assert error.code == "orchestration_request_too_large"
    assert error.retryable is False
    assert sent_body_lengths == [request_limit]


def test_swarm_policy_accepts_response_above_default_and_rejects_above_2mib() -> None:
    response_limit = ORCHESTRATION_SWARM_EXCHANGE_POLICY.max_response_bytes
    response_at_limit = b'"' + b"x" * (response_limit - 2) + b'"'
    response_over_limit = b'"' + b"x" * (response_limit - 1) + b'"'

    def handler(request: httpx.Request) -> httpx.Response:
        body = response_at_limit if request.url.path == "/at-limit" else response_over_limit
        result = httpx.Response(200, content=body, request=request)
        return result

    async def exercise_responses() -> tuple[UpstreamJsonExchange, OrchestrationExcept]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            caller = OrchestrationCalling(client, "https://orchestration.test")
            accepted = await caller.execute_json_exchange(
                "GET",
                "/at-limit",
                policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
            )
            with pytest.raises(OrchestrationExcept) as captured_error:
                await caller.execute_json_exchange(
                    "GET",
                    "/over-limit",
                    policy=ORCHESTRATION_SWARM_EXCHANGE_POLICY,
                )
        result = accepted, captured_error.value
        return result

    accepted, error = asyncio.run(exercise_responses())

    assert accepted.status_code == 200
    assert isinstance(accepted.payload, str)
    assert len(accepted.payload) == response_limit - 2
    assert error.status_code == 502
    assert error.code == "orchestration_response_too_large"
    assert error.retryable is False


def test_explicit_timeout_override_does_not_mutate_client_default() -> None:
    observed_read_timeouts: list[float | None] = []
    timeout_policy = UpstreamExchangePolicy(
        max_response_bytes=DEFAULT_UPSTREAM_EXCHANGE_POLICY.max_response_bytes,
        max_request_bytes=None,
        timeout_seconds=9.0,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        timeout = request.extensions["timeout"]
        observed_read_timeouts.append(timeout["read"])
        result = httpx.Response(200, json={"ok": True}, request=request)
        return result

    async def exercise_timeouts() -> float | None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            timeout=httpx.Timeout(2.0),
        ) as client:
            caller = OrchestrationCalling(client, "https://orchestration.test")
            await caller.execute_json_exchange("GET", "/default-before")
            await caller.execute_json_exchange(
                "POST",
                "/custom",
                policy=timeout_policy,
            )
            await caller.execute_json_exchange("GET", "/default-after")
            result = client.timeout.read
        return result

    client_default = asyncio.run(exercise_timeouts())

    assert observed_read_timeouts == [2.0, 9.0, 2.0]
    assert client_default == 2.0


def test_total_exchange_deadline_closes_stream_and_marks_mutation_unknown() -> None:
    async def exercise_deadline() -> tuple[OrchestrationExcept, RequestTrace, bool]:
        started = asyncio.Event()
        closed = asyncio.Event()
        stream = _BlockingByteStream(started, closed)
        trace = RequestTrace("total-exchange-deadline")
        policy = UpstreamExchangePolicy(
            max_response_bytes=DEFAULT_UPSTREAM_EXCHANGE_POLICY.max_response_bytes,
            max_request_bytes=None,
            timeout_seconds=0.01,
        )

        def handler(request: httpx.Request) -> httpx.Response:
            result = httpx.Response(200, stream=stream, request=request)
            return result

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            timeout=httpx.Timeout(2.0),
        ) as client:
            caller = OrchestrationCalling(
                client,
                "https://orchestration.test",
                trace=trace,
            )
            with pytest.raises(OrchestrationExcept) as captured_error:
                await caller.execute_json_exchange(
                    "POST",
                    "/dispatch",
                    policy=policy,
                )
        result = captured_error.value, trace, closed.is_set()
        return result

    error, trace, response_closed = asyncio.run(exercise_deadline())

    assert error.status_code == 504
    assert error.retryable is False
    assert response_closed is True
    assert trace.snapshot().events[0].status == UpstreamOutcome.UNKNOWN.value


def test_harness_response_bounds_match_the_shared_transport_limit() -> None:
    harness_path = Path(__file__).resolve().parents[2] / ".agents/python_bff_harness/HARNESS.toml"
    harness = tomllib.loads(harness_path.read_text(encoding="utf-8"))
    operations = harness["bff_operations"]

    for operation in operations:
        operation_id = operation["id"]
        if operation_id == ContractName.ORCHESTRATION_EVENTS.value:
            assert operation["kind"] == "stream"
            assert operation["max_response_bytes"] == RealtimeFrameByteLimitEnum.MAX_BYTES
            assert operation["response_budget_scope"] == "frame"
            assert operation["timeout_ms"] == (
                RealtimeSourceReadTimeoutSecondsEnum.IDLE_TIMEOUT_SECONDS * 1000
            )
            assert operation["timeout_scope"] == "read_phase"
        elif operation_id.startswith("orchestration.swarm_") or (
            operation_id == ContractName.ORCHESTRATION_AUTONOMY_OUTBOX_SYNC.value
        ):
            assert (
                operation["max_response_bytes"]
                == ORCHESTRATION_SWARM_EXCHANGE_POLICY.max_response_bytes
            )
            if "max_request_bytes" in operation:
                assert (
                    operation["max_request_bytes"]
                    == ORCHESTRATION_SWARM_EXCHANGE_POLICY.max_request_bytes
                )
        else:
            assert (
                operation["max_response_bytes"]
                == DEFAULT_UPSTREAM_EXCHANGE_POLICY.max_response_bytes
            )

    assert operations
