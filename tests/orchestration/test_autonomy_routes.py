"""Contract tests for Orchestration Autonomy routes and source outcomes."""

from collections.abc import Callable

import httpx
from fastapi.testclient import TestClient
from pydantic import JsonValue

from tests.shared.gateway_test_builder import GatewayTestClientBuilder, RouteResponseTable

_WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
_GOAL_ID = "00000000-0000-7000-8000-000000000002"
_NODE_ID = "00000000-0000-7000-8000-000000000003"
_ASSIGNMENT_ID = "00000000-0000-7000-8000-000000000004"
_PROFILE_ID = "00000000-0000-7000-8000-000000000005"
_PARTICIPANT_ID = "00000000-0000-7000-8000-000000000006"
_PARTICIPATION_ID = "00000000-0000-7000-8000-000000000007"
_AGENT_ID = "00000000-0000-7000-8000-000000000008"
_SESSION_ID = "00000000-0000-7000-8000-000000000009"
_REQUEST_ID = "00000000-0000-7000-8000-000000000010"


def _build_client(
    routes: RouteResponseTable,
    *,
    on_match: Callable[[httpx.Request], None] | None = None,
) -> TestClient:
    client = GatewayTestClientBuilder().with_route_table(routes, on_match=on_match).build_client()
    client.headers.update({"Authorization": "Bearer caller-token"})
    result = client
    return result


def test_scope_list_returns_source_root_array() -> None:
    routes: RouteResponseTable = {
        ("GET", "/internal/v1/workspaces/scopes"): (
            200,
            [
                {
                    "workspaceId": _WORKSPACE_ID,
                    "locationId": "00000000-0000-7000-8000-000000000011",
                    "locationRevision": 1,
                    "workspaceRevision": 3,
                    "locator": "v1:location:1:workspace",
                    "active": True,
                    "revision": 1,
                    "generation": 1,
                    "updatedAtMs": 1700,
                    "replayed": False,
                },
            ],
        ),
    }
    client = _build_client(routes)

    with client:
        response = client.get(
            "/orchestrations/workspaces/scopes",
            headers={"Authorization": "Bearer caller-token"},
        )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert response.json()[0]["workspaceId"] == _WORKSPACE_ID


def test_scope_list_rejects_duplicate_inactive_and_over_limit_projections() -> None:
    source_path = "/internal/v1/workspaces/scopes"
    active_scope = {
        "workspaceId": _WORKSPACE_ID,
        "locationId": "00000000-0000-7000-8000-000000000011",
        "locationRevision": 1,
        "workspaceRevision": 3,
        "locator": "v1:location:1:workspace",
        "active": True,
        "revision": 1,
        "generation": 1,
        "updatedAtMs": 1700,
        "replayed": False,
    }
    cases: dict[str, list[JsonValue]] = {
        "duplicate workspace": [active_scope, active_scope],
        "inactive record": [{**active_scope, "active": False}],
        "over source bound": [
            {
                **active_scope,
                "workspaceId": f"00000000-0000-7000-8000-{index:012x}",
            }
            for index in range(1, 66)
        ],
    }

    for payload in cases.values():
        client = _build_client({("GET", source_path): (200, payload)})
        with client:
            response = client.get("/orchestrations/workspaces/scopes")
        assert response.status_code == 502
        assert response.json()["code"] == "orchestration_invalid_payload"


def test_scope_registration_returns_matching_source_scope() -> None:
    location_id = "00000000-0000-7000-8000-000000000011"
    source_path = "/internal/v1/workspaces/scopes"
    source_scope = {
        "workspaceId": _WORKSPACE_ID,
        "locationId": location_id,
        "locationRevision": 1,
        "workspaceRevision": 3,
        "locator": "v1:location:1:workspace",
    }
    source_result = {
        **source_scope,
        "active": True,
        "revision": 1,
        "generation": 1,
        "updatedAtMs": 1700,
        "replayed": False,
    }
    routes: RouteResponseTable = {("POST", source_path): (200, source_result)}
    client = _build_client(routes)

    with client:
        response = client.post(
            "/orchestrations/workspaces/scopes",
            json={
                "requestId": _REQUEST_ID,
                "expectedRevision": 0,
                "scope": source_scope,
            },
        )

    assert response.status_code == 200
    assert response.json() == source_result


def test_scope_registration_rejects_nonadvancing_source_revision() -> None:
    location_id = "00000000-0000-7000-8000-000000000011"
    source_path = "/internal/v1/workspaces/scopes"
    source_result = {
        "workspaceId": _WORKSPACE_ID,
        "locationId": location_id,
        "locationRevision": 1,
        "workspaceRevision": 3,
        "locator": "v1:location:1:workspace",
        "active": True,
        "revision": 0,
        "generation": 0,
        "updatedAtMs": 1700,
        "replayed": False,
    }
    client = _build_client({("POST", source_path): (200, source_result)})

    with client:
        response = client.post(
            "/orchestrations/workspaces/scopes",
            json={
                "requestId": _REQUEST_ID,
                "expectedRevision": 0,
                "scope": {
                    "workspaceId": _WORKSPACE_ID,
                    "locationId": location_id,
                    "locationRevision": 1,
                    "workspaceRevision": 3,
                    "locator": "v1:location:1:workspace",
                },
            },
        )

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_invalid_payload"


def test_missing_scope_query_normalizes_source_omission_to_null() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/scopes"
    routes: RouteResponseTable = {
        ("GET", source_path): (200, {"workspaceId": _WORKSPACE_ID}),
    }
    client = _build_client(routes)

    with client:
        response = client.get(f"/orchestrations/workspaces/{_WORKSPACE_ID}/scopes")

    assert response.status_code == 200
    assert response.json() == {"workspaceId": _WORKSPACE_ID, "scope": None}


def test_scope_query_rejects_workspace_id_outside_the_route_path() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/scopes"
    routes: RouteResponseTable = {
        ("GET", source_path): (
            200,
            {"workspaceId": "00000000-0000-7000-8000-000000000021"},
        ),
    }
    client = _build_client(routes)

    with client:
        response = client.get(f"/orchestrations/workspaces/{_WORKSPACE_ID}/scopes")

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_invalid_payload"


def test_snapshot_query_uses_exact_camel_case_key_and_normalizes_missing_record() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/execution-snapshots"
    recorded_queries: list[dict[str, str]] = []
    routes: RouteResponseTable = {
        ("GET", source_path): (
            200,
            {
                "workspaceId": _WORKSPACE_ID,
                "goalId": _GOAL_ID,
                "dagRevision": 2,
                "nodeId": _NODE_ID,
                "assignmentId": _ASSIGNMENT_ID,
                "attempt": 0,
            },
        ),
    }

    def record_query(request: httpx.Request) -> None:
        recorded_queries.append(dict(request.url.params))

    client = _build_client(routes, on_match=record_query)
    params = {
        "goalId": _GOAL_ID,
        "dagRevision": "2",
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": "0",
    }

    with client:
        response = client.get(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/execution-snapshots",
            params=params,
        )

    assert response.status_code == 200
    assert response.json()["record"] is None
    assert recorded_queries == [params]


def test_snapshot_readback_validates_exact_attempt_and_record_fields() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/execution-snapshots"
    params = {
        "goalId": _GOAL_ID,
        "dagRevision": "2",
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": "0",
    }
    record: dict[str, JsonValue] = {
        "snapshotId": "00000000-0000-7000-8000-000000000020",
        "workspaceId": _WORKSPACE_ID,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": 0,
        "state": {
            "status": "UNKNOWN",
            "ownership": {
                "pid": 123,
                "pgid": 123,
                "startTime": "1700",
                "bootId": "boot-1",
            },
            "exitCode": None,
            "unknownReason": "EXECUTION_TIMED_OUT",
            "observedAtMs": 2100,
        },
        "revision": 2,
        "updatedAtMs": 2100,
    }
    source_result: dict[str, JsonValue] = {
        "workspaceId": _WORKSPACE_ID,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": 0,
        "record": record,
    }
    cases: dict[str, tuple[dict[str, JsonValue], int]] = {
        "valid_unknown_record": (source_result, 200),
        "explicit_null_record": ({**source_result, "record": None}, 200),
        "maximum_record_revision": (
            {**source_result, "record": {**record, "revision": 2**64 - 1}},
            200,
        ),
    }
    mismatched_fields: dict[str, JsonValue] = {
        "workspaceId": _PROFILE_ID,
        "goalId": _PROFILE_ID,
        "dagRevision": 3,
        "nodeId": _PROFILE_ID,
        "assignmentId": _PROFILE_ID,
        "attempt": 1,
    }
    for field, value in mismatched_fields.items():
        cases[f"outer_{field}"] = ({**source_result, field: value}, 502)
        cases[f"record_{field}"] = (
            {**source_result, "record": {**record, field: value}},
            502,
        )
    invalid_records: dict[str, tuple[str, JsonValue]] = {
        "nil_snapshot": ("snapshotId", "00000000-0000-0000-0000-000000000000"),
        "zero_revision": ("revision", 0),
        "negative_revision": ("revision", -1),
        "overflow_revision": ("revision", 2**64),
        "boolean_revision": ("revision", True),
        "text_revision": ("revision", "2"),
    }
    for name, (field, value) in invalid_records.items():
        cases[name] = ({**source_result, "record": {**record, field: value}}, 502)
    invalid_query_values: dict[str, JsonValue] = {
        "boolean": True,
        "float": 2.0,
        "text": "2",
    }
    for name, value in invalid_query_values.items():
        cases[f"dag_revision_{name}"] = ({**source_result, "dagRevision": value}, 502)
        attempt_value = {"boolean": False, "float": 0.0, "text": "0"}[name]
        cases[f"attempt_{name}"] = ({**source_result, "attempt": attempt_value}, 502)

    for name, (payload, expected_status) in cases.items():
        routes: RouteResponseTable = {("GET", source_path): (200, payload)}
        with _build_client(routes) as client:
            response = client.get(
                f"/orchestrations/workspaces/{_WORKSPACE_ID}/execution-snapshots",
                params=params,
            )
        assert response.status_code == expected_status, name
        if expected_status == 200:
            assert response.json() == payload, name
        else:
            assert response.json()["code"] == "orchestration_invalid_payload", name
            assert response.json()["workspace_id"] == _WORKSPACE_ID, name

    with _build_client({}) as client:
        for name in ("nil_snapshot", "zero_revision"):
            payload = cases[name][0]
            diagnostic = client.post(
                "/diagnostics/contracts/orchestration.execution_snapshot_get/validate",
                json={"value": payload},
            )
            assert diagnostic.status_code == 200
            assert diagnostic.json()["valid"] is False, name


def test_snapshot_query_rejects_missing_duplicate_and_unknown_keys() -> None:
    path = f"/orchestrations/workspaces/{_WORKSPACE_ID}/execution-snapshots"
    complete_params = [
        ("goalId", _GOAL_ID),
        ("dagRevision", "2"),
        ("nodeId", _NODE_ID),
        ("assignmentId", _ASSIGNMENT_ID),
        ("attempt", "0"),
    ]
    cases: dict[str, list[tuple[str, str]]] = {
        "missing attempt": complete_params[:-1],
        "duplicate attempt": [*complete_params, ("attempt", "1")],
        "unknown key": [*complete_params, ("unexpected", "value")],
    }

    for params in cases.values():
        client = _build_client({})
        with client:
            response = client.get(path, params=params)
        assert response.status_code == 422


def test_authority_request_requires_explicit_nullable_participant() -> None:
    path = f"/orchestrations/workspaces/{_WORKSPACE_ID}/dag-settlement-authority"
    cases: dict[str, dict[str, JsonValue]] = {
        "omitted nullable participant": {"expectedLeadershipRevision": 3},
        "boolean revision is not an integer": {
            "expectedLeadershipRevision": True,
            "participant": None,
        },
    }

    for body in cases.values():
        client = _build_client({})
        with client:
            response = client.post(path, json=body)
        assert response.status_code == 422


def test_reviewer_assignment_verdict_and_gate_keep_200_results() -> None:
    workspace_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}"
    assignment_id = "00000000-0000-7000-8000-000000000004"
    correlation = {
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": assignment_id,
        "attempt": 0,
    }
    principal = {"kind": "direct_token", "id": _AGENT_ID}
    author = {
        "profileId": _PROFILE_ID,
        "participantId": _PARTICIPANT_ID,
        "principal": principal,
    }
    reviewer = {
        "participationId": _PARTICIPATION_ID,
        "profileId": _PROFILE_ID,
        "participantId": _PARTICIPANT_ID,
        "principal": principal,
    }
    resolved_author = {
        "profileId": _PROFILE_ID,
        "participantId": _PARTICIPANT_ID,
        "principal": principal,
    }
    recorded_verdict = {
        "requestId": "00000000-0000-7000-8000-000000000015",
        "outcome": "accepted",
        "handoffDiffDigestHex": "c4" * 32,
        "rationale": "Accepted reviewed handoff.",
        "recordedAtMs": 1800,
    }
    assignment = {
        "assignmentRecordId": "00000000-0000-7000-8000-000000000016",
        "workspaceId": _WORKSPACE_ID,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": assignment_id,
        "attempt": 0,
        "reviewer": reviewer,
        "executor": resolved_author,
        "assigningLeader": resolved_author,
        "qualificationDomain": "rust-autonomy",
        "ruleGeneration": 1,
        "revision": 2,
        "assignedAtMs": 1700,
        "verdict": recorded_verdict,
        "replayed": False,
    }
    assignment_response = {
        "admitted": True,
        "rejectionCode": None,
        "detail": None,
        "assignment": {**assignment, "revision": 1, "verdict": None},
    }
    verdict_response = {
        "admitted": True,
        "rejectionCode": None,
        "detail": None,
        "assignment": assignment,
    }
    routes: RouteResponseTable = {
        ("POST", f"{workspace_path}/reviewer-assignments"): (200, assignment_response),
        ("POST", f"{workspace_path}/reviewer-verdicts"): (200, verdict_response),
        ("POST", f"{workspace_path}/node-completion-gate"): (200, verdict_response),
    }
    client = _build_client(routes)
    assignment_request = {
        "requestId": _REQUEST_ID,
        "correlation": correlation,
        "requiredDomain": "rust-autonomy",
        "executor": author,
        "assigningLeader": author,
        "candidates": [
            {
                **reviewer,
                "agentId": _AGENT_ID,
                "sessionId": _SESSION_ID,
            },
        ],
    }
    verdict_request = {
        "requestId": recorded_verdict["requestId"],
        "correlation": correlation,
        "expectedRevision": 1,
        "reviewerAgentId": _AGENT_ID,
        "reviewerSessionId": _SESSION_ID,
        "reviewer": None,
        "verdict": "accepted",
        "handoffDiffDigestHex": "c4" * 32,
    }
    gate_request = {
        "correlation": correlation,
        "currentHandoffDiffDigestHex": "c4" * 32,
    }

    with client:
        assigned = client.post(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/reviewer-assignments",
            json=assignment_request,
        )
        verdict = client.post(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/reviewer-verdicts",
            json=verdict_request,
        )
        gate = client.post(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/node-completion-gate",
            json=gate_request,
        )

    assert assigned.status_code == 200
    assert assigned.json() == assignment_response
    assert verdict.status_code == 200
    assert verdict.json() == verdict_response
    assert gate.status_code == 200
    assert gate.json() == verdict_response


def test_reviewer_domain_conflict_preserves_typed_source_body() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/reviewer-assignments"
    rejection = {
        "admitted": False,
        "rejectionCode": "NO_QUALIFIED_REVIEWER",
        "detail": "No qualified reviewer candidate.",
        "assignment": None,
    }
    routes: RouteResponseTable = {("POST", source_path): (409, rejection)}
    client = _build_client(routes)
    author = {
        "profileId": _PROFILE_ID,
        "participantId": _PARTICIPANT_ID,
        "principal": {"kind": "direct_token", "id": _AGENT_ID},
    }
    request_body = {
        "requestId": _REQUEST_ID,
        "correlation": {
            "goalId": _GOAL_ID,
            "dagRevision": 2,
            "nodeId": _NODE_ID,
            "assignmentId": _ASSIGNMENT_ID,
            "attempt": 0,
        },
        "requiredDomain": "rust-autonomy",
        "executor": author,
        "assigningLeader": author,
        "candidates": [
            {
                "profileId": _PROFILE_ID,
                "participantId": _PARTICIPANT_ID,
                "participationId": _PARTICIPATION_ID,
                "principal": {"kind": "trusted_stdio", "id": ""},
                "agentId": _AGENT_ID,
                "sessionId": _SESSION_ID,
            },
        ],
    }

    with client:
        response = client.post(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/reviewer-assignments",
            json=request_body,
        )

    assert response.status_code == 409
    assert response.json() == rejection

    wrong_status_client = _build_client({("POST", source_path): (200, rejection)})
    with wrong_status_client:
        wrong_status_response = wrong_status_client.post(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/reviewer-assignments",
            json=request_body,
        )

    assert wrong_status_response.status_code == 502
    assert wrong_status_response.json()["code"] == "orchestration_invalid_payload"


def test_snapshot_validation_conflict_preserves_typed_source_body() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/execution-snapshots"
    rejection = {
        "committed": False,
        "rejectionCode": "ENGINE_MISMATCH",
        "detail": "Resolved engine does not match profile.",
        "record": None,
    }
    routes: RouteResponseTable = {("POST", source_path): (409, rejection)}
    client = _build_client(routes)
    request_body = {
        "requestId": _REQUEST_ID,
        "snapshotId": "00000000-0000-7000-8000-000000000012",
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": 0,
        "activityId": "00000000-0000-7000-8000-000000000013",
        "profileId": _PROFILE_ID,
        "profileRevision": 1,
        "resolvedEngine": "codex",
        "resolvedModel": "gpt-6-astra",
        "resolvedReasoning": None,
        "rolePromptDigestHex": None,
        "worktreePath": "/workspaces/autonomy/worker-1",
        "leaseId": "00000000-0000-7000-8000-000000000014",
        "leaseRevision": 1,
        "leaseExpiresAtMs": 90000,
        "mcpGrant": None,
        "permissions": {
            "allowWorkspaceWrite": True,
            "allowLocalShell": True,
            "allowNetwork": False,
        },
        "timeouts": {
            "startupTimeoutMs": 5000,
            "executionTimeoutMs": 60000,
            "terminationGraceMs": 5000,
        },
    }

    with client:
        response = client.post(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/execution-snapshots",
            json=request_body,
        )

    assert response.status_code == 409
    assert response.json() == rejection


def test_snapshot_prepare_returns_committed_record() -> None:
    workspace_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}"
    snapshot_id = "00000000-0000-7000-8000-000000000012"
    activity_id = "00000000-0000-7000-8000-000000000013"
    lease_id = "00000000-0000-7000-8000-000000000014"
    source_result = {
        "committed": True,
        "rejectionCode": None,
        "detail": None,
        "record": {
            "snapshotId": snapshot_id,
            "workspaceId": _WORKSPACE_ID,
            "goalId": _GOAL_ID,
            "dagRevision": 2,
            "nodeId": _NODE_ID,
            "assignmentId": _ASSIGNMENT_ID,
            "attempt": 0,
            "state": {
                "status": "PREPARED",
                "ownership": None,
                "exitCode": None,
                "unknownReason": None,
                "observedAtMs": None,
            },
            "revision": 1,
            "updatedAtMs": 1900,
        },
    }
    routes: RouteResponseTable = {
        ("POST", f"{workspace_path}/execution-snapshots"): (200, source_result),
    }
    client = _build_client(routes)
    request_body = {
        "requestId": _REQUEST_ID,
        "snapshotId": snapshot_id,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": 0,
        "activityId": activity_id,
        "profileId": _PROFILE_ID,
        "profileRevision": 1,
        "resolvedEngine": "codex",
        "resolvedModel": "gpt-6-astra",
        "resolvedReasoning": None,
        "rolePromptDigestHex": None,
        "worktreePath": "/workspaces/autonomy/worker-1",
        "leaseId": lease_id,
        "leaseRevision": 1,
        "leaseExpiresAtMs": 90000,
        "mcpGrant": {
            "tokenId": "00000000-0000-7000-8000-000000000017",
            "issuedAtMs": 100,
            "expiresAtMs": 90000,
        },
        "permissions": {
            "allowWorkspaceWrite": True,
            "allowLocalShell": True,
            "allowNetwork": False,
        },
        "timeouts": {
            "startupTimeoutMs": 5000,
            "executionTimeoutMs": 60000,
            "terminationGraceMs": 5000,
        },
    }

    with client:
        response = client.post(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/execution-snapshots",
            json=request_body,
        )

    assert response.status_code == 200
    assert response.json() == source_result


def test_snapshot_prepare_rejects_invalid_status_and_result_pairs() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/execution-snapshots"
    snapshot_id = "00000000-0000-7000-8000-000000000012"
    record = {
        "snapshotId": snapshot_id,
        "workspaceId": _WORKSPACE_ID,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": 0,
        "state": {
            "status": "PREPARED",
            "ownership": None,
            "exitCode": None,
            "unknownReason": None,
            "observedAtMs": None,
        },
        "revision": 1,
        "updatedAtMs": 1900,
    }
    committed = {
        "committed": True,
        "rejectionCode": None,
        "detail": None,
        "record": record,
    }
    rejected = {
        "committed": False,
        "rejectionCode": "ENGINE_MISMATCH",
        "detail": "Resolved engine does not match profile.",
        "record": None,
    }
    malformed_rejection = {
        "committed": False,
        "rejectionCode": None,
        "detail": "Missing rejection code.",
        "record": None,
    }
    missing_commit_record = {
        "committed": True,
        "rejectionCode": None,
        "detail": None,
        "record": None,
    }
    cases: dict[str, tuple[int, JsonValue]] = {
        "rejection on HTTP 200": (200, rejected),
        "commit on HTTP 409": (409, committed),
        "commit without record": (200, missing_commit_record),
        "rejection without code": (409, malformed_rejection),
    }
    mismatched_record_fields: dict[str, JsonValue] = {
        "snapshotId": _PROFILE_ID,
        "workspaceId": _PROFILE_ID,
        "goalId": _PROFILE_ID,
        "dagRevision": 3,
        "nodeId": _PROFILE_ID,
        "assignmentId": _PROFILE_ID,
        "attempt": 1,
    }
    for field, value in mismatched_record_fields.items():
        cases[f"mismatched_record_{field}"] = (
            200,
            {**committed, "record": {**record, field: value}},
        )
    request_body = {
        "requestId": _REQUEST_ID,
        "snapshotId": snapshot_id,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": 0,
        "activityId": "00000000-0000-7000-8000-000000000013",
        "profileId": _PROFILE_ID,
        "profileRevision": 1,
        "resolvedEngine": "codex",
        "resolvedModel": "gpt-6-astra",
        "resolvedReasoning": None,
        "rolePromptDigestHex": None,
        "worktreePath": "/workspaces/autonomy/worker-1",
        "leaseId": "00000000-0000-7000-8000-000000000014",
        "leaseRevision": 1,
        "leaseExpiresAtMs": 90000,
        "mcpGrant": None,
        "permissions": {
            "allowWorkspaceWrite": True,
            "allowLocalShell": True,
            "allowNetwork": False,
        },
        "timeouts": {
            "startupTimeoutMs": 5000,
            "executionTimeoutMs": 60000,
            "terminationGraceMs": 5000,
        },
    }

    for response_case in cases.values():
        status_code, source_payload = response_case
        client = _build_client({("POST", source_path): (status_code, source_payload)})
        with client:
            response = client.post(
                f"/orchestrations/workspaces/{_WORKSPACE_ID}/execution-snapshots",
                json=request_body,
            )
        assert response.status_code == 502
        assert response.json()["code"] == "orchestration_invalid_payload"


def test_missing_governance_link_preserves_upstream_not_found() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/dag-settlement-governance"
    source_error = {
        "code": "NOT_FOUND",
        "message": "No DAG settlement governance link exists.",
        "retryable": False,
    }
    routes: RouteResponseTable = {("GET", source_path): (404, source_error)}
    client = _build_client(routes)

    with client:
        response = client.get(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/dag-settlement-governance",
            params={"goalId": _GOAL_ID, "dagRevision": "2"},
        )

    assert response.status_code == 404
    assert response.json() == source_error


def test_authority_check_and_governance_read_keep_200_results() -> None:
    workspace_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}"
    authority = {
        "workspaceId": _WORKSPACE_ID,
        "leaderParticipantId": _PARTICIPANT_ID,
        "leadershipRevision": 3,
    }
    governance = {
        "workspaceId": _WORKSPACE_ID,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "migrationId": "00000000-0000-7000-8000-000000000018",
        "sourceSequence": 1,
        "settlementId": "00000000-0000-7000-8000-000000000019",
        "coordinatorAgentId": _AGENT_ID,
        "coordinatorParticipantId": _PARTICIPANT_ID,
        "workspaceLeadershipRevision": 3,
        "acceptedWorkCreditCount": 2,
        "evaluatedAssignmentCount": 1,
        "startedMissionPlanId": None,
        "startedMissionPlanRevision": None,
        "settledAtMs": 2000,
        "recallVoterFulfillmentEligible": True,
    }
    routes: RouteResponseTable = {
        ("POST", f"{workspace_path}/dag-settlement-authority"): (200, authority),
        ("GET", f"{workspace_path}/dag-settlement-governance"): (200, governance),
    }
    client = _build_client(routes)

    with client:
        authority_response = client.post(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/dag-settlement-authority",
            json={"expectedLeadershipRevision": 3, "participant": None},
        )
        governance_response = client.get(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/dag-settlement-governance",
            params={"goalId": _GOAL_ID, "dagRevision": "2"},
        )

    assert authority_response.status_code == 200
    assert authority_response.json() == authority
    assert governance_response.status_code == 200
    assert governance_response.json() == governance


def test_governance_read_rejects_invalid_source_link_identity() -> None:
    source_path = f"/internal/v1/workspaces/{_WORKSPACE_ID}/dag-settlement-governance"
    source_result = {
        "workspaceId": _WORKSPACE_ID,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "migrationId": "00000000-0000-0000-0000-000000000000",
        "sourceSequence": 1,
        "settlementId": "00000000-0000-7000-8000-000000000019",
        "coordinatorAgentId": _AGENT_ID,
        "coordinatorParticipantId": None,
        "workspaceLeadershipRevision": None,
        "acceptedWorkCreditCount": 2,
        "evaluatedAssignmentCount": 1,
        "startedMissionPlanId": None,
        "startedMissionPlanRevision": None,
        "settledAtMs": 2000,
        "recallVoterFulfillmentEligible": True,
    }
    client = _build_client({("GET", source_path): (200, source_result)})

    with client:
        response = client.get(
            f"/orchestrations/workspaces/{_WORKSPACE_ID}/dag-settlement-governance",
            params={"goalId": _GOAL_ID, "dagRevision": "2"},
        )

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_invalid_payload"


def test_malformed_scope_result_is_rejected_as_invalid_upstream_payload() -> None:
    routes: RouteResponseTable = {
        ("GET", "/internal/v1/workspaces/scopes"): (
            200,
            [{"workspaceId": "not-a-uuid"}],
        ),
    }
    client = _build_client(routes)

    with client:
        response = client.get("/orchestrations/workspaces/scopes")

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_invalid_payload"
