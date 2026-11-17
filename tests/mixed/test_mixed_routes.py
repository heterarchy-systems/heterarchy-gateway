"""Builder-based route contracts for the Mixed Swarm and DAG views."""

import asyncio
from collections.abc import AsyncIterator, Callable
from uuid import UUID

import httpx
from fastapi.testclient import TestClient
from pydantic import JsonValue

from app.forge.exceptions.forge_exceptions import ForgeFailureEnvelope
from app.mixed_module.application.inner_dto.mixed_dependency_failure_inner_dto import (
    ForgeSourceFailureDto,
    OrchestrationSourceFailureDto,
)
from app.mixed_module.application.mixed_application_utils import dependency_failure_set
from app.mixed_module.application.mixed_swarm_overview_app import (
    MixedSwarmOverviewApplication,
)
from app.mixed_module.exceptions.mixed_exceptions import MixedDependencyFailureError
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationBackendErrorDto,
)
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.filter_module.mixed_module_filter import MixedSwarmOverviewFilter
from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder

_WORKSPACE_ID = "10000000-0000-0000-0000-000000000001"
_SWARM_RUN_ID = "20000000-0000-0000-0000-000000000002"
_LOCATION_ID = "30000000-0000-0000-0000-000000000003"
_FORGE_REQUEST_ID = "40000000-0000-0000-0000-000000000004"
_SECOND_FORGE_REQUEST_ID = "40000000-0000-0000-0000-000000000005"
_GOAL_ID = "50000000-0000-0000-0000-000000000005"
_REVISION_ID = "60000000-0000-0000-0000-000000000006"
_MIGRATION_ID = "70000000-0000-0000-0000-000000000007"
_SETTLEMENT_ID = "80000000-0000-0000-0000-000000000008"
_COORDINATOR_ID = "90000000-0000-0000-0000-000000000009"
_OVERVIEW_PATH = f"/mixed/workspaces/{_WORKSPACE_ID}/swarms/{_SWARM_RUN_ID}/overview"
_FORGE_SETTLEMENT_PATH = "/api/v1/commands/swarm.settlement_get"
_ORCHESTRATION_INSPECTION_PATH = f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_SWARM_RUN_ID}"
_FORGE_DAG_PATH = "/api/v1/commands/dag.read_current"
_ORCHESTRATION_GOVERNANCE_PATH = (
    f"/internal/v1/workspaces/{_WORKSPACE_ID}/dag-settlement-governance"
)


def _json_object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise AssertionError("Expected a JSON object")
    return value


def _overview_query(request_id: str = _FORGE_REQUEST_ID) -> dict[str, str]:
    result = {
        "forge_request_id": request_id,
        "workspace_revision": "3",
        "location_id": _LOCATION_ID,
        "expected_revision": "2",
        "relative_root": "projects/example",
    }
    return result


def _run_inspection(state: str = "ACTIVE") -> JsonValue:
    run: JsonValue = {
        "swarmRunId": _SWARM_RUN_ID,
        "workspaceId": _WORKSPACE_ID,
        "title": "Mixed overview run",
        "mode": {"kind": "STANDALONE"},
        "state": state,
        "maxMembers": 8,
        "maxSpawnDepth": 2,
        "maxTotalTurns": 32,
        "totalTurnsUsed": 1,
        "requiredVerifierQuorum": 1,
        "allowWorkerAllMention": False,
        "baselineCommitOid": "0123456789abcdef0123456789abcdef01234567",
        "baselineTreeBlake3Hex": "a" * 64,
        "convergedCommitOid": None,
        "convergedTreeBlake3Hex": None,
        "convergedDiffDigestHex": None,
        "stallNudgeCount": 0,
        "settlementRequestId": None,
        "revision": 2,
        "createdAtMs": 100,
        "updatedAtMs": 120,
        "replayed": False,
    }
    result: JsonValue = {
        "run": run,
        "channels": [],
        "members": [],
        "subscriptions": [],
        "pendingDoorbells": [],
        "verificationPanel": None,
        "verdicts": [],
    }
    return result


def _settlement_receipt(state: str = "applied") -> JsonValue:
    result: JsonValue = {
        "settlement_id": _SETTLEMENT_ID,
        "swarm_run_id": _SWARM_RUN_ID,
        "target": {"kind": "standalone_swarm"},
        "state": state,
        "settled_at_ms": 200,
        "baseline_commit_oid": "baseline",
        "converged_commit_oid": "converged",
        "baseline_tree_blake3": "b" * 64,
        "settled_tree_blake3": "c" * 64,
        "converged_diff_digest": "d" * 64,
        "settled_file_count": 4,
        "upserted_paths": ["src/new.rs"],
        "deleted_paths": [],
    }
    return result


def _settlement_result(receipt: JsonValue | None = None) -> JsonValue:
    result: dict[str, JsonValue] = {
        "workspace_id": _WORKSPACE_ID,
        "swarm_run_id": _SWARM_RUN_ID,
    }
    if receipt is not None:
        result["receipt"] = receipt
    return result


def _forge_success(request_id: str, result: JsonValue) -> JsonValue:
    envelope: JsonValue = {
        "forge_api": 1,
        "request_id": request_id,
        "ok": True,
        "result": result,
    }
    return envelope


def _settlement_error(request_id: str) -> JsonValue:
    result: JsonValue = {
        "forge_api": 1,
        "request_id": request_id,
        "ok": False,
        "error": {
            "code": "UNKNOWN_OUTCOME",
            "message": "Settlement outcome requires readback.",
            "category": "unknown_outcome",
            "retryable": False,
            "recovery_action": "readback",
            "recovery_hint": "Read the durable settlement record.",
            "readback": None,
        },
    }
    return result


def _dag_found_result(goal_id: str = _GOAL_ID, revision: int = 7) -> JsonValue:
    result: JsonValue = {
        "found": True,
        "goal_id": goal_id,
        "revision_id": _REVISION_ID,
        "base_goal_revision": 4,
        "dag_revision": revision,
        "parent_revision": None,
        "created_at_ms": 100,
        "head_revision": revision,
        "head_updated_at_ms": 120,
        "node_count": 0,
        "nodes": [],
        "edges": [],
        "lineage": [],
    }
    return result


def _governance_result(goal_id: str = _GOAL_ID, revision: int = 4) -> JsonValue:
    result: JsonValue = {
        "workspaceId": _WORKSPACE_ID,
        "goalId": goal_id,
        "dagRevision": revision,
        "migrationId": _MIGRATION_ID,
        "sourceSequence": 11,
        "settlementId": _SETTLEMENT_ID,
        "coordinatorAgentId": _COORDINATOR_ID,
        "coordinatorParticipantId": None,
        "workspaceLeadershipRevision": 5,
        "acceptedWorkCreditCount": 3,
        "evaluatedAssignmentCount": 4,
        "startedMissionPlanId": None,
        "startedMissionPlanRevision": None,
        "settledAtMs": 200,
        "recallVoterFulfillmentEligible": True,
    }
    return result


def _dag_request(
    *,
    workspace_id: str = _WORKSPACE_ID,
    forge_goal_id: str = _GOAL_ID,
    governance_goal_id: str = _GOAL_ID,
    forge_request_id: str = _FORGE_REQUEST_ID,
) -> JsonValue:
    result: JsonValue = {
        "forge_request": {
            "forge_api": 1,
            "request_id": forge_request_id,
            "op": "dag.read_current",
            "payload": {
                "scope": {
                    "workspace_id": workspace_id,
                    "workspace_revision": 3,
                    "locator": {
                        "location_id": _LOCATION_ID,
                        "expected_revision": 2,
                        "relative_root": "projects/example",
                    },
                },
                "goal_id": forge_goal_id,
            },
        },
        "governance_query": {
            "goalId": governance_goal_id,
            "dagRevision": 4,
        },
    }
    return result


def _successful_handler(
    captured: list[httpx.Request],
    *,
    receipt: JsonValue | None = None,
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path == _FORGE_SETTLEMENT_PATH:
            source_request = _json_object(decode_json(request.content))
            request_id = source_request["request_id"]
            if not isinstance(request_id, str):
                raise AssertionError("Forge command request id should be text")
            body = _forge_success(request_id, _settlement_result(receipt))
            return httpx.Response(200, json=body)
        if request.url.path == _ORCHESTRATION_INSPECTION_PATH:
            return httpx.Response(200, json=_run_inspection())
        if request.url.path == _FORGE_DAG_PATH:
            source_request = _json_object(decode_json(request.content))
            request_id = source_request["request_id"]
            if not isinstance(request_id, str):
                raise AssertionError("Forge command request id should be text")
            return httpx.Response(200, json=_forge_success(request_id, _dag_found_result()))
        if request.url.path == _ORCHESTRATION_GOVERNANCE_PATH:
            return httpx.Response(200, json=_governance_result())
        return httpx.Response(404, json={"detail": "unexpected upstream request"})

    return handler


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> TestClient:
    result = GatewayTestClientBuilder().with_handler(handler).build_client()
    return result


def _headers(forge_token: str, orchestration_token: str) -> dict[str, str]:
    result = {
        "X-Forge-Authorization": f"Bearer {forge_token}",
        "X-Orchestration-Authorization": f"Bearer {orchestration_token}",
    }
    return result


def _orchestration_source_error_handler(
    captured: list[httpx.Request],
    source_status: int,
    code: str,
    case_name: str,
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path == _FORGE_SETTLEMENT_PATH:
            source_request = _json_object(decode_json(request.content))
            request_id = source_request["request_id"]
            if not isinstance(request_id, str):
                raise AssertionError("Forge command request id should be text")
            return httpx.Response(
                200,
                json=_forge_success(request_id, _settlement_result()),
            )
        if request.url.path == _ORCHESTRATION_INSPECTION_PATH:
            return httpx.Response(
                source_status,
                json={"code": code, "message": f"Source {case_name}", "retryable": False},
            )
        return httpx.Response(404, json={"detail": "unexpected upstream request"})

    return handler


def _transport_error_handler(
    failed_path: str,
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == failed_path:
            raise httpx.ConnectError("upstream unavailable", request=request)
        if request.url.path == _FORGE_SETTLEMENT_PATH:
            source_request = _json_object(decode_json(request.content))
            request_id = source_request["request_id"]
            if not isinstance(request_id, str):
                raise AssertionError("Forge command request id should be text")
            return httpx.Response(200, json=_forge_success(request_id, _settlement_result()))
        if request.url.path == _ORCHESTRATION_INSPECTION_PATH:
            return httpx.Response(200, json=_run_inspection())
        return httpx.Response(404, json={"detail": "unexpected upstream request"})

    return handler


def test_swarm_overview_preserves_some_and_none_settlement_observations() -> None:
    cases: dict[str, tuple[JsonValue | None, dict[str, str], int]] = {
        "applied_receipt": (
            _settlement_receipt(),
            {**_overview_query(), "run_state": "ACTIVE", "settled_only": "true"},
            200,
        ),
        "prepared_true": (
            _settlement_receipt("prepared"),
            {**_overview_query(), "settled_only": "true"},
            404,
        ),
        "prepared_false": (
            _settlement_receipt("prepared"),
            {**_overview_query(), "settled_only": "false"},
            200,
        ),
        "recovery_required_true": (
            _settlement_receipt("recovery_required"),
            {**_overview_query(), "settled_only": "true"},
            404,
        ),
        "recovery_required_false": (
            _settlement_receipt("recovery_required"),
            {**_overview_query(), "settled_only": "false"},
            200,
        ),
        "no_receipt_filter_false": (
            None,
            {**_overview_query(_SECOND_FORGE_REQUEST_ID), "settled_only": "false"},
            200,
        ),
        "run_state_mismatch": (
            _settlement_receipt(),
            {**_overview_query(), "run_state": "ABORTED", "settled_only": "true"},
            404,
        ),
    }
    for case_name, (receipt, params, expected_status) in cases.items():
        captured: list[httpx.Request] = []
        with _client(_successful_handler(captured, receipt=receipt)) as client:
            response = client.get(_OVERVIEW_PATH, params=params, headers=_headers("f", "o"))
        assert response.status_code == expected_status, case_name
        if expected_status == 404:
            error_body = _json_object(decode_json(response.content))
            assert isinstance(error_body["detail"], str)
            assert len(captured) == 2
            continue
        body = _json_object(decode_json(response.content))
        assert body["workspaceId"] == _WORKSPACE_ID
        assert body["swarmRunId"] == _SWARM_RUN_ID
        forge = _json_object(body["forge"])
        result = _json_object(forge["result"])
        if receipt is None:
            assert result["receipt"] is None
            assert result["outbox_entry"] is None
        else:
            observed_receipt = _json_object(result["receipt"])
            expected_receipt = _json_object(receipt)
            assert observed_receipt["state"] == expected_receipt["state"]
        assert len(captured) == 2


def test_swarm_overview_filter_mismatch_records_both_source_reads() -> None:
    captured: list[httpx.Request] = []
    with _client(_successful_handler(captured)) as client:
        response = client.get(
            _OVERVIEW_PATH,
            params={**_overview_query(), "settled_only": "true"},
            headers=_headers("forge-token", "orchestration-token"),
        )
        trace_response = client.get(f"/diagnostics/traces/{response.headers['X-Trace-ID']}")
    assert response.status_code == 404
    trace = _json_object(decode_json(trace_response.content))
    assert trace["bff_http_status"] == 404
    assert trace["public_response"] is None
    raw = _json_object(trace["raw"])
    assert "forge" in raw and "orchestration" in raw
    assert len(captured) == 2


def test_dag_governance_retains_independent_forge_and_settlement_revisions() -> None:
    captured: list[httpx.Request] = []
    with _client(_successful_handler(captured)) as client:
        response = client.post(
            f"/mixed/workspaces/{_WORKSPACE_ID}/dags/governance-overview",
            json=_dag_request(),
            headers=_headers("forge-token", "orchestration-token"),
        )
    assert response.status_code == 200
    body = _json_object(decode_json(response.content))
    assert body["workspaceId"] == _WORKSPACE_ID
    assert body["goalId"] == _GOAL_ID
    forge = _json_object(body["forge"])
    forge_result = _json_object(forge["result"])
    assert forge_result["dag_revision"] == 7
    governance = _json_object(body["governance"])
    assert governance["dagRevision"] == 4
    forge_request = next(request for request in captured if request.url.path == _FORGE_DAG_PATH)
    forwarded = _json_object(decode_json(forge_request.content))
    assert forwarded["request_id"] == _FORGE_REQUEST_ID
    assert (
        forwarded["payload"]
        == _json_object(_json_object(_dag_request())["forge_request"])["payload"]
    )


def test_dag_context_and_goal_mismatches_return_422_without_backend_calls() -> None:
    cases: dict[str, JsonValue] = {
        "workspace_scope_mismatch": _dag_request(
            workspace_id="11000000-0000-0000-0000-000000000011"
        ),
        "goal_mismatch": _dag_request(forge_goal_id="51000000-0000-0000-0000-000000000015"),
    }
    for body in cases.values():
        captured: list[httpx.Request] = []
        with _client(_successful_handler(captured)) as client:
            response = client.post(
                f"/mixed/workspaces/{_WORKSPACE_ID}/dags/governance-overview",
                json=body,
                headers=_headers("forge-token", "orchestration-token"),
            )
        assert response.status_code == 422
        validation = _json_object(decode_json(response.content))
        issues = validation["detail"]
        assert isinstance(issues, list) and issues
        assert {"loc", "msg", "type"}.issubset(_json_object(issues[0]))
        assert not captured


def test_overview_query_shape_errors_return_422_without_backend_calls() -> None:
    query = _overview_query()
    required_query = "&".join(f"{key}={value}" for key, value in query.items())
    invalid_query = {
        "duplicate_optional": f"{required_query}&settled_only=true&settled_only=false",
        "unknown_key": f"{required_query}&unexpected=value",
        "missing_locator_context": "&".join(
            f"{key}={value}" for key, value in query.items() if key != "relative_root"
        ),
    }
    for raw_query in invalid_query.values():
        captured: list[httpx.Request] = []
        with _client(_successful_handler(captured)) as client:
            response = client.get(
                f"{_OVERVIEW_PATH}?{raw_query}",
                headers=_headers("forge-token", "orchestration-token"),
            )
        assert response.status_code == 422
        assert not captured


def test_backend_credentials_are_independent_and_required() -> None:
    captured: list[httpx.Request] = []
    with _client(_successful_handler(captured)) as client:
        responses = [
            client.get(
                _OVERVIEW_PATH,
                params=_overview_query(request_id),
                headers={
                    **_headers(f"forge-{index}", f"orchestration-{index}"),
                    "Authorization": f"Bearer fallback-{index}",
                },
            )
            for index, request_id in enumerate(
                (_FORGE_REQUEST_ID, _SECOND_FORGE_REQUEST_ID),
                1,
            )
        ]
        before_missing = len(captured)
        missing = client.get(
            _OVERVIEW_PATH,
            params=_overview_query(),
            headers={"X-Forge-Authorization": "Bearer forge-only"},
        )
    assert [item.status_code for item in responses] == [200, 200]
    forge_auth = [
        request.headers["authorization"]
        for request in captured
        if request.url.host == "forge.example.test"
    ]
    orchestration_auth = [
        request.headers["authorization"]
        for request in captured
        if request.url.host == "orchestration.example.test"
    ]
    assert forge_auth == ["Bearer forge-1", "Bearer forge-2"]
    assert orchestration_auth == ["Bearer orchestration-1", "Bearer orchestration-2"]
    assert missing.status_code == 422
    assert len(captured) == before_missing


def test_forge_unknown_outcome_keeps_202_status_and_does_not_retry() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path == _FORGE_SETTLEMENT_PATH:
            source_request = _json_object(decode_json(request.content))
            request_id = source_request["request_id"]
            if not isinstance(request_id, str):
                raise AssertionError("Forge command request id should be text")
            return httpx.Response(202, json=_settlement_error(request_id))
        if request.url.path == _ORCHESTRATION_INSPECTION_PATH:
            return httpx.Response(200, json=_run_inspection())
        return httpx.Response(404, json={"detail": "unexpected upstream request"})

    with _client(handler) as client:
        response = client.get(
            _OVERVIEW_PATH,
            params=_overview_query(),
            headers=_headers("forge-token", "orchestration-token"),
        )
    assert response.status_code == 202
    body = _json_object(decode_json(response.content))
    failures = body["failures"]
    assert isinstance(failures, list) and len(failures) == 1
    failure = _json_object(failures[0])
    assert failure["status_code"] == 202
    forge_error = _json_object(failure["response"])
    assert forge_error["request_id"] == _FORGE_REQUEST_ID
    error = _json_object(forge_error["error"])
    assert error["code"] == "UNKNOWN_OUTCOME"
    assert error["retryable"] is False
    assert error["readback"] is None
    assert sum(request.url.path == _FORGE_SETTLEMENT_PATH for request in captured) == 1


def test_orchestration_source_404_and_409_keep_original_status_and_body() -> None:
    cases: dict[str, tuple[int, str]] = {
        "not_found": (404, "NOT_FOUND"),
        "conflict": (409, "CONFLICT"),
        "unprocessable": (422, "INVALID_INPUT"),
    }
    for case_name, (source_status, code) in cases.items():
        captured: list[httpx.Request] = []
        with _client(
            _orchestration_source_error_handler(
                captured,
                source_status,
                code,
                case_name,
            )
        ) as client:
            response = client.get(
                _OVERVIEW_PATH,
                params=_overview_query(),
                headers=_headers("forge-token", "orchestration-token"),
            )
        assert response.status_code == source_status
        body = _json_object(decode_json(response.content))
        failure = _json_object(body["failures"][0])
        assert failure["status_code"] == source_status
        source_error = _json_object(failure["response"])
        assert source_error["code"] == code
        assert source_error["message"] == f"Source {case_name}"
        assert len(captured) == 2


def test_simultaneous_typed_failures_keep_every_body_with_fixed_status_precedence() -> None:
    forge_envelope = ForgeFailureEnvelope.model_validate(_settlement_error(_FORGE_REQUEST_ID))
    forge_failure = ForgeSourceFailureDto(
        status_code=202,
        response=forge_envelope.to_inner_dto(),
    )
    orchestration_failure = OrchestrationSourceFailureDto(
        status_code=409,
        response=OrchestrationBackendErrorDto(
            code="CONFLICT",
            message="Governance record changed",
            retryable=False,
        ),
    )
    result = dependency_failure_set(
        (
            MixedDependencyFailureError(orchestration_failure),
            MixedDependencyFailureError(forge_failure),
        )
    )
    failures = tuple(item.to_dict() for item in result.failures)
    assert [item["backend"].value for item in failures] == ["forge", "orchestration"]
    assert [item["status_code"] for item in failures] == [202, 409]
    assert result.status_code == 202


def test_transport_errors_preserve_backend_correlation() -> None:
    cases: dict[str, tuple[str, str]] = {
        "forge_transport": (_FORGE_SETTLEMENT_PATH, "forge"),
        "orchestration_transport": (_ORCHESTRATION_INSPECTION_PATH, "orchestration"),
    }
    for _case_name, (failed_path, expected_backend) in cases.items():
        with _client(_transport_error_handler(failed_path)) as client:
            response = client.get(
                _OVERVIEW_PATH,
                params=_overview_query(),
                headers=_headers("forge-token", "orchestration-token"),
            )
        assert response.status_code == 502
        body = _json_object(decode_json(response.content))
        failure = _json_object(body["failures"][0])
        assert failure["backend"] == expected_backend
        assert failure["kind"] == f"{expected_backend}_gateway"
        error = _json_object(failure["response"])
        if expected_backend == "forge":
            assert error["request_id"] == _FORGE_REQUEST_ID
        else:
            assert error["workspace_id"] == _WORKSPACE_ID


class _BlockingStream(httpx.AsyncByteStream):
    def __init__(self, cancelled: list[bool]) -> None:
        """Create a response stream that records task cancellation.

        Args:
            cancelled: Collection receiving one marker after cancellation.
        Return:
            None.
        """
        self._cancelled = cancelled

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Hold response consumption until its owning request is cancelled.

        Args:
            None.
        Return:
            Async byte iterator for the upstream body.
        """
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self._cancelled.append(True)
            raise
        yield b"{}"

    async def aclose(self) -> None:
        """Close the test response stream.

        Args:
            None.
        Return:
            None.
        """
        return None


class _ObservedBlockingStream(httpx.AsyncByteStream):
    def __init__(
        self,
        cancelled: list[bool],
        started: asyncio.Event,
        started_count: list[int],
    ) -> None:
        """Create a stream that synchronizes two request child tasks.

        Args:
            cancelled: Collection receiving a marker after cancellation.
            started: Event set after both upstream streams begin reading.
            started_count: Event-loop-owned mutable count shared by both streams.
        Return:
            None.
        """
        self._cancelled = cancelled
        self._started = started
        self._started_count = started_count

    async def __aiter__(self) -> AsyncIterator[bytes]:
        """Wait until the parent cancels the two independent read tasks.

        Args:
            None.
        Return:
            Async byte iterator for the pending upstream body.
        """
        self._started_count[0] += 1
        if self._started_count[0] == 2:
            self._started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            self._cancelled.append(True)
            raise
        yield b"{}"

    async def aclose(self) -> None:
        """Close the test response stream.

        Args:
            None.
        Return:
            None.
        """
        return None


def test_typed_backend_reply_cancels_and_joins_sibling_read() -> None:
    cancelled: list[bool] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == _FORGE_SETTLEMENT_PATH:
            return httpx.Response(200, stream=_BlockingStream(cancelled))
        if request.url.path == _ORCHESTRATION_INSPECTION_PATH:
            return httpx.Response(
                404,
                json={"code": "NOT_FOUND", "message": "Missing run", "retryable": False},
            )
        return httpx.Response(404, json={"detail": "unexpected upstream request"})

    with _client(handler) as client:
        response = client.get(
            _OVERVIEW_PATH,
            params=_overview_query(),
            headers=_headers("forge-token", "orchestration-token"),
        )
    assert response.status_code == 404
    assert cancelled == [True]


def test_transport_exception_cancels_and_joins_sibling_read() -> None:
    cancelled: list[bool] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == _FORGE_SETTLEMENT_PATH:
            return httpx.Response(200, stream=_BlockingStream(cancelled))
        if request.url.path == _ORCHESTRATION_INSPECTION_PATH:
            raise httpx.ConnectError("upstream unavailable", request=request)
        return httpx.Response(404, json={"detail": "unexpected upstream request"})

    with _client(handler) as client:
        response = client.get(
            _OVERVIEW_PATH,
            params=_overview_query(),
            headers=_headers("forge-token", "orchestration-token"),
        )
    assert response.status_code == 502
    assert cancelled == [True]


def test_malformed_nested_orchestration_success_maps_to_correlated_502() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path == _FORGE_SETTLEMENT_PATH:
            source_request = _json_object(decode_json(request.content))
            request_id = source_request["request_id"]
            if not isinstance(request_id, str):
                raise AssertionError("Forge command request id should be text")
            return httpx.Response(200, json=_forge_success(request_id, _settlement_result()))
        if request.url.path == _ORCHESTRATION_INSPECTION_PATH:
            inspection = _json_object(_run_inspection())
            run = _json_object(inspection["run"])
            run["mode"] = {
                "kind": "DAG_NODE_HYBRID",
                "hybridTarget": {
                    "goalId": _GOAL_ID,
                    "dagRevision": -1,
                    "nodeId": _REVISION_ID,
                    "declaredWriteManifestBlake3Hex": "e" * 64,
                },
            }
            return httpx.Response(200, json=inspection)
        return httpx.Response(404, json={"detail": "unexpected upstream request"})

    with _client(handler) as client:
        response = client.get(
            _OVERVIEW_PATH,
            params=_overview_query(),
            headers=_headers("forge-token", "orchestration-token"),
        )
    assert response.status_code == 502
    body = _json_object(decode_json(response.content))
    failure = _json_object(body["failures"][0])
    assert failure["backend"] == "orchestration"
    assert failure["kind"] == "orchestration_gateway"
    assert _json_object(failure["response"])["workspace_id"] == _WORKSPACE_ID
    assert len(captured) == 2


def test_gateway_deadline_cancels_and_joins_backend_reads() -> None:
    cancelled: list[bool] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path in {_FORGE_SETTLEMENT_PATH, _ORCHESTRATION_INSPECTION_PATH}:
            return httpx.Response(200, stream=_BlockingStream(cancelled))
        return httpx.Response(404, json={"detail": "unexpected upstream request"})

    with _client(handler) as client:
        response = client.get(
            _OVERVIEW_PATH,
            params=_overview_query(),
            headers=_headers("forge-token", "orchestration-token"),
        )
    assert response.status_code == 504
    body = _json_object(decode_json(response.content))
    failure = _json_object(body["failures"][0])
    assert failure["backend"] == "gateway"
    assert failure["kind"] == "mixed_gateway_timeout"
    assert cancelled == [True, True]


def test_external_request_cancellation_propagates_after_child_cleanup() -> None:
    async def scenario() -> None:
        cancelled: list[bool] = []
        started = asyncio.Event()
        started_count = [0]

        def handler(_request: httpx.Request) -> httpx.Response:
            stream = _ObservedBlockingStream(cancelled, started, started_count)
            return httpx.Response(200, stream=stream)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            timeout=httpx.Timeout(60),
        ) as client:
            application = MixedSwarmOverviewApplication(
                ForgeCalling(client, "https://forge.example.test/api/v1"),
                OrchestrationCalling(client, "https://orchestration.example.test"),
            )
            filters = MixedSwarmOverviewFilter.model_validate(_overview_query())
            task = asyncio.create_task(
                application.execute(
                    UUID(_WORKSPACE_ID),
                    UUID(_SWARM_RUN_ID),
                    filters,
                )
            )
            await asyncio.wait_for(started.wait(), timeout=2)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            else:
                raise AssertionError("External cancellation must propagate to the caller")
        assert cancelled == [True, True]

    asyncio.run(scenario())
