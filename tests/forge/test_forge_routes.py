"""Forge command-envelope route contracts and Source passthrough behavior."""

import httpx
from pydantic import JsonValue

from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder, RouteResponseTable

_REQUEST_ID = "11111111-1111-4111-8111-111111111111"
_OTHER_REQUEST_ID = "22222222-2222-4222-8222-222222222222"
_LOCATION_ID = "33333333-3333-4333-8333-333333333333"
_OTHER_LOCATION_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
_WORKSPACE_ID = "44444444-4444-4444-8444-444444444444"
_OTHER_WORKSPACE_ID = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
_ACTIVITY_ID = "55555555-5555-4555-8555-555555555555"
_SESSION_ID = "66666666-6666-4666-8666-666666666666"
_GOAL_ID = "77777777-7777-4777-8777-777777777777"
_OTHER_GOAL_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
_REVISION_ID = "88888888-8888-4888-8888-888888888888"
_NODE_ID = "99999999-9999-4999-8999-999999999999"
_SETTLEMENT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
_OTHER_SETTLEMENT_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
_LOCATOR = f"v1:{_LOCATION_ID}:2:cHJvamVjdA"
_SCOPE: dict[str, JsonValue] = {
    "workspace_id": _WORKSPACE_ID,
    "workspace_revision": 4,
    "locator": {
        "location_id": _LOCATION_ID,
        "expected_revision": 2,
        "relative_root": "project",
    },
}
_ACTOR_PUBLIC: dict[str, JsonValue] = {
    "session_id": _SESSION_ID,
    "principal": {"kind": "trusted_stdio", "token_id": None, "grant_id": None},
    "workspace_id": _WORKSPACE_ID,
}
_ACTOR_SOURCE: dict[str, JsonValue] = {
    "session_id": _SESSION_ID,
    "principal": {"kind": "trusted_stdio"},
    "workspace_id": _WORKSPACE_ID,
}

type ForgeRouteCase = tuple[
    str,
    str,
    dict[str, JsonValue],
    dict[str, JsonValue],
    dict[str, JsonValue],
]


def test_forge_workspace_and_dag_routes_preserve_typed_envelopes() -> None:
    route_cases: dict[str, ForgeRouteCase] = {
        "location_list": (
            "/forges/locations/list",
            "location.list",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "location.list",
                "payload": {},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "location.list",
                "payload": {},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": True,
                "result": {
                    "entries": [
                        {
                            "location_id": _LOCATION_ID,
                            "display_name": "Project files",
                            "revision": 2,
                            "state": "enabled",
                        },
                    ],
                },
            },
        ),
        "workspace_list": (
            "/forges/workspaces/list",
            "workspace.list",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "workspace.list",
                "payload": {"location_id": _LOCATION_ID, "expected_revision": 2},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "workspace.list",
                "payload": {"location_id": _LOCATION_ID, "expected_revision": 2},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": True,
                "result": {
                    "entries": [
                        {
                            "locator": _LOCATOR,
                            "display_name": "Project",
                            "workspace_id": _WORKSPACE_ID,
                            "workspace_revision": 4,
                        },
                    ],
                },
            },
        ),
        "activity_list": (
            "/forges/activities/list",
            "activity.list",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "activity.list",
                "payload": {
                    "locator": _LOCATOR,
                    "workspace_id": _WORKSPACE_ID,
                    "workspace_revision": 4,
                    "limit": 20,
                },
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "activity.list",
                "payload": {
                    "locator": _LOCATOR,
                    "workspace_id": _WORKSPACE_ID,
                    "workspace_revision": 4,
                    "limit": 20,
                },
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": True,
                "result": {
                    "scope": {
                        "workspace_id": _WORKSPACE_ID,
                        "workspace_revision": 4,
                        "locator": _LOCATOR,
                    },
                    "activities": [
                        {
                            "activity_id": _ACTIVITY_ID,
                            "workspace_id": _WORKSPACE_ID,
                            "state": "open",
                            "liveness": "available",
                            "revision": 1,
                            "created_at_ms": 100,
                            "updated_at_ms": 100,
                            "lease_owner_id": None,
                            "lease_until_ms": None,
                            "lease_revision": 0,
                        },
                    ],
                },
            },
        ),
        "dag_read_current": (
            "/forges/dags/current",
            "dag.read_current",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "dag.read_current",
                "payload": {"scope": _SCOPE, "goal_id": _GOAL_ID},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "dag.read_current",
                "payload": {"scope": _SCOPE, "goal_id": _GOAL_ID},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": True,
                "result": {
                    "found": True,
                    "goal_id": _GOAL_ID,
                    "revision_id": _REVISION_ID,
                    "base_goal_revision": 2,
                    "dag_revision": 3,
                    "parent_revision": None,
                    "created_at_ms": 150,
                    "head_revision": 3,
                    "head_updated_at_ms": 150,
                    "node_count": 1,
                    "nodes": [
                        {
                            "node_id": _NODE_ID,
                            "ordinal": 1,
                            "title": "Build",
                            "objective": "Build the service",
                            "acceptance": ["Service starts"],
                            "lifecycle": "pending",
                            "lifecycle_reason": None,
                            "status": "ready",
                            "waiting_on": [],
                            "revision": 1,
                            "evidence_count": 0,
                            "created_at_ms": 150,
                            "updated_at_ms": 150,
                        },
                    ],
                    "edges": [],
                    "lineage": [],
                },
            },
        ),
        "dag_settle": (
            "/forges/dags/settle",
            "dag.settle",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "dag.settle",
                "payload": {
                    "scope": _SCOPE,
                    "activity_id": _ACTIVITY_ID,
                    "actor": _ACTOR_PUBLIC,
                    "goal_id": _GOAL_ID,
                    "expected_goal_revision": 2,
                    "expected_dag_revision": 3,
                    "settlement_id": _SETTLEMENT_ID,
                    "observed_at_ms": 200,
                },
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "dag.settle",
                "payload": {
                    "scope": _SCOPE,
                    "activity_id": _ACTIVITY_ID,
                    "actor": _ACTOR_SOURCE,
                    "goal_id": _GOAL_ID,
                    "expected_goal_revision": 2,
                    "expected_dag_revision": 3,
                    "settlement_id": _SETTLEMENT_ID,
                    "observed_at_ms": 200,
                },
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": True,
                "result": {
                    "settlement_id": _SETTLEMENT_ID,
                    "goal_id": _GOAL_ID,
                    "dag_revision": 3,
                    "state": "applied",
                    "settled_at_ms": 200,
                    "terminal_sink_node_ids": [_NODE_ID],
                    "baseline_commit_oid": "a" * 40,
                    "candidate_commit_oid": "b" * 40,
                    "baseline_tree_blake3": "c" * 64,
                    "settled_tree_blake3": "d" * 64,
                    "settled_file_count": 1,
                    "upserted_paths": ["README.md"],
                    "deleted_paths": [],
                },
            },
        ),
    }
    upstream_routes: RouteResponseTable = {
        ("POST", f"/api/v1/commands/{operation}"): (200, reply)
        for _path, operation, _request_body, _source_body, reply in route_cases.values()
    }
    forwarded_requests: list[tuple[str, str, JsonValue, str | None]] = []

    def record_request(request: httpx.Request) -> None:
        forwarded_requests.append(
            (
                request.method,
                request.url.path,
                decode_json(request.content),
                request.headers.get("authorization"),
            ),
        )

    client = (
        GatewayTestClientBuilder()
        .with_route_table(upstream_routes, on_match=record_request)
        .build_client()
    )
    client.headers["Authorization"] = "Bearer forge-contract-test"
    observed_responses: dict[str, dict[str, JsonValue]] = {}
    with client:
        for name, (path, _operation, request_body, _source_body, _reply) in route_cases.items():
            response = client.post(path, json=request_body)
            assert response.status_code == 200
            observed_responses[name] = response.json()

    expected_forwarded = [
        ("POST", f"/api/v1/commands/{operation}", source_body, "Bearer forge-contract-test")
        for _path, operation, _request_body, source_body, _reply in route_cases.values()
    ]
    assert forwarded_requests == expected_forwarded
    assert observed_responses == {
        name: reply for name, (_path, _operation, _body, _source, reply) in route_cases.items()
    }


def test_forge_invalid_location_payload_is_rejected_before_upstream_call() -> None:
    forwarded_paths: list[str] = []
    client = (
        GatewayTestClientBuilder()
        .with_route_table(
            {("POST", "/api/v1/commands/location.list"): (200, {})},
            on_match=lambda request: forwarded_paths.append(request.url.path),
        )
        .build_client()
    )
    invalid_cases: dict[str, dict[str, JsonValue]] = {
        "unexpected_payload_field": {
            "forge_api": 1,
            "request_id": _REQUEST_ID,
            "op": "location.list",
            "payload": {"unexpected": "field"},
        },
        "boolean_api_version": {
            "forge_api": True,
            "request_id": _REQUEST_ID,
            "op": "location.list",
            "payload": {},
        },
        "operation_mismatch": {
            "forge_api": 1,
            "request_id": _REQUEST_ID,
            "op": "workspace.list",
            "payload": {},
        },
    }
    with client:
        responses = {
            name: client.post("/forges/locations/list", json=request_body)
            for name, request_body in invalid_cases.items()
        }

    assert all(response.status_code == 422 for response in responses.values())
    assert forwarded_paths == []


def test_forge_workspace_list_requires_revision_payload_field() -> None:
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/workspace.list"): (200, {})})
        .build_client()
    )
    with client:
        response = client.post(
            "/forges/workspaces/list",
            json={
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "workspace.list",
                "payload": {"location_id": _LOCATION_ID},
            },
        )

    assert response.status_code == 422


def test_dag_read_current_preserves_source_missing_result() -> None:
    source_reply: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "ok": True,
        "result": {"found": False},
    }
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "dag.read_current",
        "payload": {"scope": _SCOPE, "goal_id": _GOAL_ID},
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/dag.read_current"): (200, source_reply)})
        .build_client()
    )
    with client:
        response = client.post("/forges/dags/current", json=request_body)

    assert response.status_code == 200
    assert response.json() == source_reply


def test_forge_conflict_envelope_preserves_source_status_and_error() -> None:
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "dag.settle",
        "payload": {
            "scope": _SCOPE,
            "activity_id": _ACTIVITY_ID,
            "actor": _ACTOR_PUBLIC,
            "goal_id": _GOAL_ID,
            "expected_goal_revision": 2,
            "expected_dag_revision": 3,
            "settlement_id": _SETTLEMENT_ID,
            "observed_at_ms": 200,
        },
    }
    error_envelope: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "ok": False,
        "error": {
            "code": "PLANNING_CONFLICT",
            "message": "DAG revision changed",
            "category": "planning_conflict",
            "retryable": False,
            "recovery_action": "read_back",
            "recovery_hint": "",
            "readback": None,
        },
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/dag.settle"): (409, error_envelope)})
        .build_client()
    )
    with client:
        response = client.post("/forges/dags/settle", json=request_body)

    assert response.status_code == 409
    assert response.json() == error_envelope


def test_forge_pre_envelope_auth_rejection_preserves_nil_source_request_id() -> None:
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "location.list",
        "payload": {},
    }
    error_envelope: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": "00000000-0000-0000-0000-000000000000",
        "ok": False,
        "error": {
            "code": "AUTH_FAILED",
            "message": "authentication failed",
            "category": "authentication",
            "retryable": False,
            "recovery_action": "authenticate",
            "recovery_hint": "",
            "readback": None,
        },
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/location.list"): (400, error_envelope)})
        .build_client()
    )
    with client:
        response = client.post("/forges/locations/list", json=request_body)

    assert response.status_code == 400
    assert response.json() == error_envelope


def test_forge_pre_envelope_invalid_json_rejection_preserves_nil_source_request_id() -> None:
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "location.list",
        "payload": {},
    }
    error_envelope: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": "00000000-0000-0000-0000-000000000000",
        "ok": False,
        "error": {
            "code": "INVALID_INPUT",
            "message": "request body could not be decoded",
            "category": "input_validation",
            "retryable": False,
            "recovery_action": "correct_input",
            "recovery_hint": "",
            "readback": None,
        },
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/location.list"): (400, error_envelope)})
        .build_client()
    )
    with client:
        response = client.post("/forges/locations/list", json=request_body)

    assert response.status_code == 400
    assert response.json() == error_envelope


def test_forge_pre_envelope_capacity_rejection_preserves_nil_source_request_id() -> None:
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "location.list",
        "payload": {},
    }
    error_envelope: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": "00000000-0000-0000-0000-000000000000",
        "ok": False,
        "error": {
            "code": "CAPACITY_EXCEEDED",
            "message": "Forge is shutting down",
            "category": "capacity_exceeded",
            "retryable": True,
            "recovery_action": "retry_when_available",
            "recovery_hint": "",
            "readback": None,
        },
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/location.list"): (503, error_envelope)})
        .build_client()
    )
    with client:
        response = client.post("/forges/locations/list", json=request_body)

    assert response.status_code == 503
    assert response.json() == error_envelope


def test_forge_corrupt_envelopes_and_results_map_to_sanitized_502() -> None:
    cases: dict[str, tuple[str, dict[str, JsonValue], dict[str, JsonValue]]] = {
        "mismatched_request_id": (
            "dag.settle",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "dag.settle",
                "payload": {
                    "scope": _SCOPE,
                    "activity_id": _ACTIVITY_ID,
                    "actor": _ACTOR_PUBLIC,
                    "goal_id": _GOAL_ID,
                    "expected_goal_revision": 2,
                    "expected_dag_revision": 3,
                    "settlement_id": _SETTLEMENT_ID,
                    "observed_at_ms": 200,
                },
            },
            {
                "forge_api": 1,
                "request_id": _OTHER_REQUEST_ID,
                "ok": True,
                "result": {},
            },
        ),
        "missing_workspace_identity": (
            "workspace.list",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "workspace.list",
                "payload": {"location_id": _LOCATION_ID, "expected_revision": 2},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": True,
                "result": {
                    "entries": [
                        {
                            "locator": _LOCATOR,
                            "display_name": "Project",
                            "workspace_revision": 4,
                        },
                    ],
                },
            },
        ),
        "numeric_success_flag": (
            "activity.list",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "activity.list",
                "payload": {
                    "locator": _LOCATOR,
                    "workspace_id": _WORKSPACE_ID,
                    "workspace_revision": 4,
                    "limit": 20,
                },
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": 1,
                "result": {"entries": []},
            },
        ),
        "numeric_dag_found_flag": (
            "dag.read_current",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "dag.read_current",
                "payload": {"scope": _SCOPE, "goal_id": _GOAL_ID},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": True,
                "result": {"found": 0},
            },
        ),
        "location_revision_overflow": (
            "location.list",
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "op": "location.list",
                "payload": {},
            },
            {
                "forge_api": 1,
                "request_id": _REQUEST_ID,
                "ok": True,
                "result": {
                    "entries": [
                        {
                            "location_id": _LOCATION_ID,
                            "display_name": "Project files",
                            "revision": 2**65,
                            "state": "enabled",
                        },
                    ],
                },
            },
        ),
    }
    upstream_routes: RouteResponseTable = {
        ("POST", f"/api/v1/commands/{operation}"): (200, response_body)
        for operation, _request_body, response_body in cases.values()
    }
    client = GatewayTestClientBuilder().with_route_table(upstream_routes).build_client()

    with client:
        responses = {
            name: client.post(
                {
                    "location.list": "/forges/locations/list",
                    "workspace.list": "/forges/workspaces/list",
                    "activity.list": "/forges/activities/list",
                    "dag.read_current": "/forges/dags/current",
                    "dag.settle": "/forges/dags/settle",
                }[operation],
                json=request_body,
            )
            for name, (operation, request_body, _response_body) in cases.items()
        }

    for response in responses.values():
        assert response.status_code == 502
        assert response.json()["code"] == "forge_invalid_payload"


def test_forge_workspace_list_locator_is_bound_to_requested_location_revision() -> None:
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "workspace.list",
        "payload": {"location_id": _LOCATION_ID, "expected_revision": 2},
    }
    source_reply: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "ok": True,
        "result": {
            "entries": [
                {
                    "locator": f"v1:{_OTHER_LOCATION_ID}:2:cHJvamVjdA",
                    "display_name": "Foreign Project",
                    "workspace_id": _WORKSPACE_ID,
                    "workspace_revision": 4,
                },
            ],
        },
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/workspace.list"): (200, source_reply)})
        .build_client()
    )
    with client:
        response = client.post("/forges/workspaces/list", json=request_body)

    assert response.status_code == 502
    assert response.json()["code"] == "forge_invalid_payload"


def test_forge_activity_scope_is_bound_to_requested_workspace_locator() -> None:
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "activity.list",
        "payload": {
            "locator": _LOCATOR,
            "workspace_id": _WORKSPACE_ID,
            "workspace_revision": 4,
            "limit": 20,
        },
    }
    source_reply: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "ok": True,
        "result": {
            "scope": {
                "workspace_id": _OTHER_WORKSPACE_ID,
                "workspace_revision": 4,
                "locator": _LOCATOR,
            },
            "activities": [],
        },
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/activity.list"): (200, source_reply)})
        .build_client()
    )
    with client:
        response = client.post("/forges/activities/list", json=request_body)

    assert response.status_code == 502
    assert response.json()["code"] == "forge_invalid_payload"


def test_forge_dag_read_current_echoes_requested_goal_identity() -> None:
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "dag.read_current",
        "payload": {"scope": _SCOPE, "goal_id": _GOAL_ID},
    }
    source_reply: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "ok": True,
        "result": {
            "found": True,
            "goal_id": _OTHER_GOAL_ID,
            "revision_id": _REVISION_ID,
            "base_goal_revision": 2,
            "dag_revision": 3,
            "parent_revision": None,
            "created_at_ms": 150,
            "head_revision": 3,
            "head_updated_at_ms": 150,
            "node_count": 0,
            "nodes": [],
            "edges": [],
            "lineage": [],
        },
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/dag.read_current"): (200, source_reply)})
        .build_client()
    )
    with client:
        response = client.post("/forges/dags/current", json=request_body)

    assert response.status_code == 502
    assert response.json()["code"] == "forge_invalid_payload"


def test_forge_dag_settle_receipt_matches_requested_identity_and_revision() -> None:
    request_body: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "op": "dag.settle",
        "payload": {
            "scope": _SCOPE,
            "activity_id": _ACTIVITY_ID,
            "actor": _ACTOR_PUBLIC,
            "goal_id": _GOAL_ID,
            "expected_goal_revision": 2,
            "expected_dag_revision": 3,
            "settlement_id": _SETTLEMENT_ID,
            "observed_at_ms": 200,
        },
    }
    source_reply: dict[str, JsonValue] = {
        "forge_api": 1,
        "request_id": _REQUEST_ID,
        "ok": True,
        "result": {
            "settlement_id": _OTHER_SETTLEMENT_ID,
            "goal_id": _GOAL_ID,
            "dag_revision": 3,
            "state": "applied",
            "settled_at_ms": 200,
            "terminal_sink_node_ids": [_NODE_ID],
            "baseline_commit_oid": "a" * 40,
            "candidate_commit_oid": "b" * 40,
            "baseline_tree_blake3": "c" * 64,
            "settled_tree_blake3": "d" * 64,
            "settled_file_count": 1,
            "upserted_paths": ["README.md"],
            "deleted_paths": [],
        },
    }
    client = (
        GatewayTestClientBuilder()
        .with_route_table({("POST", "/api/v1/commands/dag.settle"): (200, source_reply)})
        .build_client()
    )
    with client:
        response = client.post("/forges/dags/settle", json=request_body)

    assert response.status_code == 502
    assert response.json()["code"] == "forge_invalid_payload"
