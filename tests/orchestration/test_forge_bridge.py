"""Dictionary-grouped contract checks for East-West Forge bridge routes."""

from collections.abc import Callable

import httpx
from fastapi.testclient import TestClient
from pydantic import JsonValue

from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder

_WORKSPACE_ID = "00000000-0000-7000-8000-000000000101"
_SWARM_RUN_ID = "00000000-0000-7000-8000-000000000102"
_REQUEST_ID = "00000000-0000-7000-8000-000000000103"
_SESSION_ID = "00000000-0000-7000-8000-000000000104"
_AGENT_ID = "00000000-0000-7000-8000-000000000105"
_MIGRATION_ID = "00000000-0000-7000-8000-000000000106"
_PANEL_ID = "00000000-0000-7000-8000-000000000107"
_SETTLEMENT_ID = _REQUEST_ID
_CONVERGE_PATH = f"/orchestrations/workspaces/{_WORKSPACE_ID}/swarms/{_SWARM_RUN_ID}/forge-converge"
_SETTLE_PATH = f"/orchestrations/workspaces/{_WORKSPACE_ID}/swarms/{_SWARM_RUN_ID}/forge-settle"
_SYNC_PATH = f"/orchestrations/workspaces/{_WORKSPACE_ID}/autonomy-outbox/sync"
_CONVERGE_UPSTREAM = f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_SWARM_RUN_ID}/forge-converge"
_SETTLE_UPSTREAM = f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_SWARM_RUN_ID}/forge-settle"
_SYNC_UPSTREAM = f"/internal/v1/workspaces/{_WORKSPACE_ID}/autonomy-outbox/sync"
_CALLER_HEADERS = {"Authorization": "Bearer bridge-caller"}


def _run_wire(
    *,
    workspace_id: str = _WORKSPACE_ID,
    swarm_run_id: str = _SWARM_RUN_ID,
    state: str = "CANDIDATE_READY",
) -> JsonValue:
    result: JsonValue = {
        "swarmRunId": swarm_run_id,
        "workspaceId": workspace_id,
        "title": "East-West contract test",
        "mode": {"kind": "STANDALONE", "hybridTarget": None},
        "state": state,
        "maxMembers": 8,
        "maxSpawnDepth": 2,
        "maxTotalTurns": 32,
        "totalTurnsUsed": 2,
        "requiredVerifierQuorum": 1,
        "allowWorkerAllMention": False,
        "baselineCommitOid": "0123456789abcdef0123456789abcdef01234567",
        "baselineTreeBlake3Hex": "a" * 64,
        "convergedCommitOid": "1123456789abcdef0123456789abcdef01234567",
        "convergedTreeBlake3Hex": "b" * 64,
        "convergedDiffDigestHex": "c" * 64,
        "stallNudgeCount": 0,
        "settlementRequestId": None,
        "revision": 3,
        "createdAtMs": 100,
        "updatedAtMs": 200,
        "replayed": False,
    }
    return result


def _gate_wire(*, swarm_run_id: str = _SWARM_RUN_ID) -> JsonValue:
    result: JsonValue = {
        "panelId": _PANEL_ID,
        "swarmRunId": swarm_run_id,
        "convergedDiffDigestHex": "c" * 64,
        "requiredQuorum": 1,
        "acceptedVerdicts": [],
    }
    return result


def _converge_response(
    *, include_gate: bool = True, swarm_run_id: str = _SWARM_RUN_ID
) -> JsonValue:
    result: dict[str, JsonValue] = {
        "run": _run_wire(swarm_run_id=swarm_run_id),
        "changedFiles": ["src/bridge-output.txt"],
    }
    if include_gate:
        result["gate"] = _gate_wire(swarm_run_id=swarm_run_id)
    return result


def _settle_response() -> JsonValue:
    result: JsonValue = {
        "run": _run_wire(state="SETTLED"),
        "gate": _gate_wire(),
        "settlementId": _SETTLEMENT_ID,
        "settledFileCount": 1,
        "settledAtMs": 300,
        "purgedEphemeral": True,
    }
    return result


def _sync_response(*, last_sequence: int = 7) -> JsonValue:
    result: JsonValue = {
        "appliedCount": 2,
        "dagSettledCount": 1,
        "swarmSettledCount": 1,
        "lastSequence": last_sequence,
    }
    return result


def _valid_requests() -> dict[str, tuple[str, str, JsonValue]]:
    return {
        "converge": (
            "POST",
            _CONVERGE_PATH,
            {
                "requestId": _REQUEST_ID,
                "sessionId": _SESSION_ID,
                "candidateMemberIds": [],
                "stageCandidateOnly": False,
            },
        ),
        "settle": (
            "POST",
            _SETTLE_PATH,
            {
                "requestId": _REQUEST_ID,
                "sessionId": _SESSION_ID,
                "activityId": None,
                "coordinatorAgentId": _AGENT_ID,
                "outboxMigrationId": None,
                "outboxAfterSequence": None,
                "purgeEphemeral": False,
            },
        ),
        "sync": (
            "POST",
            _SYNC_PATH,
            {"migrationId": _MIGRATION_ID, "afterSequence": 5, "limit": None},
        ),
    }


def _bridge_client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> TestClient:
    client = GatewayTestClientBuilder().with_handler(handler).build_client()
    result = client
    return result


def _fixed_response_handler(
    status_code: int,
    payload: JsonValue,
) -> Callable[[httpx.Request], httpx.Response]:
    """Bind one immutable source response for a grouped route case."""

    def handler(request: httpx.Request) -> httpx.Response:
        result = httpx.Response(status_code, json=payload, request=request)
        return result

    return handler


def _json_object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise AssertionError("Expected JSON object")
    result: dict[str, JsonValue] = value
    return result


def test_bridge_requests_serialize_source_omissions_and_responses_normalize_nulls() -> None:
    successful_responses: dict[str, tuple[int, JsonValue]] = {
        _CONVERGE_UPSTREAM: (200, _converge_response(include_gate=False)),
        _SETTLE_UPSTREAM: (200, _settle_response()),
        _SYNC_UPSTREAM: (200, _sync_response()),
    }
    captured: list[httpx.Request] = []
    public_responses: dict[str, dict[str, JsonValue]] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        status_code, payload = successful_responses[request.url.path]
        request_payload = _json_object(decode_json(request.content))
        if request.url.path == _CONVERGE_UPSTREAM and request_payload["stageCandidateOnly"] is True:
            payload = {**_json_object(_converge_response()), "gate": None}
        if (
            request.url.path == _SETTLE_UPSTREAM
            and request_payload.get("outboxMigrationId") is not None
        ):
            settle_payload = _json_object(_settle_response())
            settle_payload["outboxSequence"] = 6
            settle_payload["outboxSync"] = _sync_response(last_sequence=7)
            payload = settle_payload
        elif request.url.path == _SETTLE_UPSTREAM and request_payload["purgeEphemeral"] is True:
            payload = {
                **_json_object(_settle_response()),
                "outboxSequence": None,
                "outboxSync": None,
            }
        return httpx.Response(status_code, json=payload, request=request)

    with _bridge_client(handler) as client:
        for method, path, payload in _valid_requests().values():
            response = client.request(method, path, json=payload, headers=_CALLER_HEADERS)
            assert response.status_code == 200
            public_responses[path] = _json_object(decode_json(response.content))
        settle_request = _json_object(_valid_requests()["settle"][2])
        settle_request["activityId"] = _AGENT_ID
        settle_request["outboxMigrationId"] = _MIGRATION_ID
        settle_request["outboxAfterSequence"] = 5
        settle_with_sync = client.post(
            _SETTLE_PATH,
            json=settle_request,
            headers=_CALLER_HEADERS,
        )
        assert settle_with_sync.status_code == 200
        public_responses["settle_with_sync"] = _json_object(decode_json(settle_with_sync.content))
        converge_with_null_gate = client.post(
            _CONVERGE_PATH,
            json={**_json_object(_valid_requests()["converge"][2]), "stageCandidateOnly": True},
            headers=_CALLER_HEADERS,
        )
        settle_with_nulls = client.post(
            _SETTLE_PATH,
            json={**_json_object(_valid_requests()["settle"][2]), "purgeEphemeral": True},
            headers=_CALLER_HEADERS,
        )
        assert converge_with_null_gate.status_code == 200
        assert settle_with_nulls.status_code == 200
        public_responses["converge_with_null_gate"] = _json_object(
            decode_json(converge_with_null_gate.content)
        )
        public_responses["settle_with_nulls"] = _json_object(decode_json(settle_with_nulls.content))

    forwarded = [
        (request.url.path, _json_object(decode_json(request.content))) for request in captured
    ]
    assert {path for path, _body in forwarded} == {
        _CONVERGE_UPSTREAM,
        _SETTLE_UPSTREAM,
        _SYNC_UPSTREAM,
    }
    converge_requests = [body for path, body in forwarded if path == _CONVERGE_UPSTREAM]
    assert converge_requests[0] == {
        "requestId": _REQUEST_ID,
        "sessionId": _SESSION_ID,
        "candidateMemberIds": [],
        "stageCandidateOnly": False,
    }
    assert converge_requests[1]["stageCandidateOnly"] is True
    settle_requests = [body for path, body in forwarded if path == _SETTLE_UPSTREAM]
    assert settle_requests[0] == {
        "requestId": _REQUEST_ID,
        "sessionId": _SESSION_ID,
        "coordinatorAgentId": _AGENT_ID,
        "purgeEphemeral": False,
    }
    assert settle_requests[1]["activityId"] == _AGENT_ID
    assert settle_requests[1]["outboxMigrationId"] == _MIGRATION_ID
    assert settle_requests[1]["outboxAfterSequence"] == 5
    assert settle_requests[2]["purgeEphemeral"] is True
    sync_requests = [body for path, body in forwarded if path == _SYNC_UPSTREAM]
    assert sync_requests == [{"migrationId": _MIGRATION_ID, "afterSequence": 5}]

    assert public_responses[_CONVERGE_PATH]["gate"] is None
    assert public_responses[_SETTLE_PATH]["outboxSequence"] is None
    assert public_responses[_SETTLE_PATH]["outboxSync"] is None
    assert public_responses["converge_with_null_gate"]["gate"] is None
    assert public_responses["settle_with_nulls"]["outboxSequence"] is None
    assert public_responses["settle_with_nulls"]["outboxSync"] is None
    assert public_responses["settle_with_sync"]["outboxSequence"] == 6
    assert public_responses["settle_with_sync"]["outboxSync"] == _sync_response()
    assert public_responses[_SYNC_PATH] == {
        "appliedCount": 2,
        "dagSettledCount": 1,
        "swarmSettledCount": 1,
        "lastSequence": 7,
    }


def test_bridge_rejects_missing_unknown_and_invalid_request_fields_before_send() -> None:
    valid = _valid_requests()
    cases: dict[str, tuple[str, str, JsonValue]] = {}
    for operation, (method, path, payload) in valid.items():
        body = _json_object(payload)
        missing = dict(body)
        missing.pop(next(iter(body)))
        cases[f"{operation}_missing"] = (method, path, missing)
        cases[f"{operation}_unknown"] = (method, path, {**body, "unknownField": "unexpected"})
    sync_body = _json_object(valid["sync"][2])
    cases["sync_zero_limit"] = (
        "POST",
        _SYNC_PATH,
        {**sync_body, "limit": 0},
    )
    cases["sync_boolean_cursor"] = (
        "POST",
        _SYNC_PATH,
        {**sync_body, "afterSequence": True},
    )
    converge_body = _json_object(valid["converge"][2])
    cases["nil_workspace_path"] = (
        "POST",
        _CONVERGE_PATH.replace(_WORKSPACE_ID, "00000000-0000-0000-0000-000000000000"),
        converge_body,
    )
    cases["uppercase_workspace_path"] = (
        "POST",
        _CONVERGE_PATH.replace(_WORKSPACE_ID, "AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA"),
        converge_body,
    )
    cases["nil_swarm_path"] = (
        "POST",
        _CONVERGE_PATH.replace(_SWARM_RUN_ID, "00000000-0000-0000-0000-000000000000"),
        converge_body,
    )

    sent_paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_paths.append(request.url.path)
        return httpx.Response(200, json={}, request=request)

    with _bridge_client(handler) as client:
        for case_name, (method, path, payload) in cases.items():
            response = client.request(method, path, json=payload, headers=_CALLER_HEADERS)
            assert response.status_code == 422, case_name
    assert sent_paths == []


def test_bridge_preserves_source_errors_and_rejects_bad_success_projections() -> None:
    cases: dict[str, tuple[str, str, int, JsonValue, int]] = {
        "converge_conflict": (
            "POST",
            _CONVERGE_PATH,
            409,
            {"code": "ORCHESTRATION_CONFLICT", "message": "merge conflict", "retryable": False},
            409,
        ),
        "settle_rejection": (
            "POST",
            _SETTLE_PATH,
            409,
            {
                "code": "REVIEW_NOT_ACCEPTED",
                "message": "verifier quorum missing",
                "retryable": False,
            },
            409,
        ),
        "sync_failure": (
            "POST",
            _SYNC_PATH,
            503,
            {
                "code": "ORCHESTRATION_UNAVAILABLE",
                "message": "bridge unavailable",
                "retryable": True,
            },
            503,
        ),
        "converge_wrong_workspace": (
            "POST",
            _CONVERGE_PATH,
            200,
            _converge_response(swarm_run_id=_SESSION_ID),
            502,
        ),
        "converge_unknown_response_field": (
            "POST",
            _CONVERGE_PATH,
            200,
            {**_json_object(_converge_response()), "unknownField": True},
            502,
        ),
        "settle_wrong_settlement_id": (
            "POST",
            _SETTLE_PATH,
            200,
            {**_json_object(_settle_response()), "settlementId": _SESSION_ID},
            502,
        ),
        "settle_numeric_overflow": (
            "POST",
            _SETTLE_PATH,
            200,
            {**_json_object(_settle_response()), "settledFileCount": 2**64},
            502,
        ),
        "settle_boolean_timestamp": (
            "POST",
            _SETTLE_PATH,
            200,
            {**_json_object(_settle_response()), "settledAtMs": True},
            502,
        ),
        "settle_regressive_nested_outbox_cursor": (
            "POST",
            _SETTLE_PATH,
            200,
            {
                **_json_object(_settle_response()),
                "outboxSequence": 7,
                "outboxSync": _sync_response(last_sequence=7),
            },
            502,
        ),
        "sync_regressive_cursor": (
            "POST",
            _SYNC_PATH,
            200,
            _sync_response(last_sequence=4),
            502,
        ),
        "sync_boolean_counter": (
            "POST",
            _SYNC_PATH,
            200,
            {**_json_object(_sync_response()), "appliedCount": True},
            502,
        ),
    }

    for case_name, (method, path, source_status, payload, expected_status) in cases.items():
        request_payload = _json_object(
            _valid_requests()[
                "converge"
                if path == _CONVERGE_PATH
                else "settle"
                if path == _SETTLE_PATH
                else "sync"
            ][2]
        )
        if case_name == "sync_regressive_cursor":
            request_payload["afterSequence"] = 5
        if case_name == "settle_regressive_nested_outbox_cursor":
            request_payload["outboxMigrationId"] = _MIGRATION_ID
            request_payload["outboxAfterSequence"] = 8
        with _bridge_client(_fixed_response_handler(source_status, payload)) as client:
            response = client.request(method, path, json=request_payload, headers=_CALLER_HEADERS)
        assert response.status_code == expected_status, case_name
        if source_status >= 400:
            assert response.json() == payload, case_name
        else:
            assert response.json()["code"] == "orchestration_invalid_payload", case_name
