"""Exercise all Gateway Forge Swarm command routes against typed source replies."""

import json

import httpx
import pytest
from pydantic import ValidationError

from app.forge.schema.swarm.settlement.forge_swarm_settlement_schema import (
    ForgeSwarmSettlementGetResult,
    ForgeSwarmSettleResult,
)
from app.forge.schema.swarm.workspace.forge_swarm_workspace_schema import (
    ForgeSwarmPurgeCommandRequest,
    ForgeSwarmPurgeResult,
    ForgeSwarmWorkspaceGetResult,
    ForgeSwarmWorkspaceReceiptResult,
)
from app.shared.types.base_types import JsonObject, JsonValue
from app.shared.types.json_contract import decode_json

type RouteResponseTable = dict[tuple[str, str], tuple[int, JsonValue]]

_LOCATION_ID = "10000000-0000-0000-0000-000000000001"
_WORKSPACE_ID = "20000000-0000-0000-0000-000000000002"
_SESSION_ID = "30000000-0000-0000-0000-000000000003"
_SWARM_RUN_ID = "40000000-0000-0000-0000-000000000004"
_MEMBER_ID = "50000000-0000-0000-0000-000000000005"
_SETTLEMENT_ID = "60000000-0000-0000-0000-000000000006"
_GOAL_ID = "70000000-0000-0000-0000-000000000007"
_NODE_ID = "80000000-0000-0000-0000-000000000008"
_COORDINATOR_ID = "90000000-0000-0000-0000-000000000009"


def _scope() -> JsonObject:
    return {
        "workspace_id": _WORKSPACE_ID,
        "workspace_revision": 2,
        "locator": {
            "location_id": _LOCATION_ID,
            "expected_revision": 1,
            "relative_root": ".",
        },
    }


def _actor() -> JsonObject:
    return {
        "session_id": _SESSION_ID,
        "principal": {"kind": "trusted_stdio", "token_id": None, "grant_id": None},
        "workspace_id": _WORKSPACE_ID,
    }


def _receipt(*, target: JsonObject) -> JsonObject:
    return {
        "swarm_run_id": _SWARM_RUN_ID,
        "member_id": _MEMBER_ID,
        "mode": "inherit",
        "target": target,
        "worktree_path": ".codex/swarm/member-1",
        "provisioned_at_ms": 100,
        "initial_tree_blake3": "a" * 64,
        "initial_file_count": 3,
        "input_commit_oid": "input-commit",
    }


def _settlement_receipt(*, target: JsonObject) -> JsonObject:
    return {
        "settlement_id": str(_SETTLEMENT_ID),
        "swarm_run_id": _SWARM_RUN_ID,
        "target": target,
        "state": "applied",
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


def _success(request_id: str, result: JsonObject) -> JsonObject:
    return {"forge_api": 1, "request_id": request_id, "ok": True, "result": result}


def _failure(
    request_id: str, code: str, category: str, action: str, readback: JsonObject | None
) -> JsonObject:
    return {
        "forge_api": 1,
        "request_id": request_id,
        "ok": False,
        "error": {
            "code": code,
            "message": "The source rejected this command.",
            "category": category,
            "retryable": False,
            "recovery_action": action,
            "recovery_hint": "",
            "readback": readback,
        },
    }


def _command_body(request_id: str, operation: str, payload: JsonObject) -> JsonObject:
    return {"forge_api": 1, "request_id": request_id, "op": operation, "payload": payload}


def test_swarm_routes_forward_typed_payloads_and_normalize_source_omissions() -> None:
    from tests.shared.gateway_test_builder import GatewayTestClientBuilder

    standalone_target: JsonObject = {"kind": "standalone_swarm"}
    hybrid_target: JsonObject = {
        "kind": "dag_node_hybrid",
        "goal_id": _GOAL_ID,
        "dag_revision": 4,
        "node_id": _NODE_ID,
    }
    cases: dict[str, tuple[str, str, JsonObject, JsonObject]] = {
        "workspace_provision": (
            "/forges/swarms/workspaces/provision",
            "swarm.workspace_provision",
            {
                "scope": _scope(),
                "actor": _actor(),
                "swarm_run_id": _SWARM_RUN_ID,
                "member_id": _MEMBER_ID,
                "mode": "inherit",
                "target": standalone_target,
                "candidate_commit_oid": None,
                "observed_at_ms": 100,
            },
            _receipt(target=standalone_target),
        ),
        "workspace_get": (
            "/forges/swarms/workspaces/inspect",
            "swarm.workspace_get",
            {
                "scope": _scope(),
                "swarm_run_id": _SWARM_RUN_ID,
                "member_id": _MEMBER_ID,
            },
            {
                "workspace_id": _WORKSPACE_ID,
                "swarm_run_id": _SWARM_RUN_ID,
                "member_id": _MEMBER_ID,
                "found": False,
            },
        ),
        "member_capture": (
            "/forges/swarms/members/capture",
            "swarm.member_capture",
            {
                "scope": _scope(),
                "actor": _actor(),
                "swarm_run_id": _SWARM_RUN_ID,
                "member_id": _MEMBER_ID,
                "captured_at_ms": 150,
            },
            {
                "swarm_run_id": _SWARM_RUN_ID,
                "member_id": _MEMBER_ID,
                "mode": "inherit",
                "input_commit_oid": "input-commit",
                "output_commit_oid": "output-commit",
                "initial_tree_blake3": "a" * 64,
                "final_tree_blake3": "e" * 64,
                "final_file_count": 4,
                "changed_paths": ["src/new.rs"],
                "diff_digest": "f" * 64,
                "captured_at_ms": 150,
            },
        ),
        "converge": (
            "/forges/swarms/converge",
            "swarm.converge",
            {
                "scope": _scope(),
                "actor": _actor(),
                "swarm_run_id": _SWARM_RUN_ID,
                "candidates": [
                    {
                        "member_id": _MEMBER_ID,
                        "expected_output_commit_oid": None,
                        "expected_diff_digest": None,
                    }
                ],
                "observed_at_ms": 160,
            },
            {
                "status": "conflict",
                "swarm_run_id": _SWARM_RUN_ID,
                "conflicting_member_id": _MEMBER_ID,
                "details": ["member output differs"],
            },
        ),
        "settle": (
            "/forges/swarms/settle",
            "swarm.settle",
            {
                "scope": _scope(),
                "activity_id": None,
                "actor": _actor(),
                "coordinator_agent_id": _COORDINATOR_ID,
                "swarm_run_id": _SWARM_RUN_ID,
                "settlement_id": _SETTLEMENT_ID,
                "converged_commit_oid": "converged",
                "expected_diff_digest": None,
                "settled_at_ms": 200,
            },
            {"receipt": _settlement_receipt(target=standalone_target)},
        ),
        "materialize_hybrid": (
            "/forges/swarms/materialize-hybrid",
            "swarm.materialize_hybrid",
            {
                "scope": _scope(),
                "activity_id": _SESSION_ID,
                "actor": _actor(),
                "swarm_run_id": _SWARM_RUN_ID,
                "settlement_id": _SETTLEMENT_ID,
                "goal_id": _GOAL_ID,
                "expected_goal_revision": 5,
                "expected_dag_revision": 4,
                "node_id": _NODE_ID,
                "converged_commit_oid": "converged",
                "expected_diff_digest": None,
                "settled_at_ms": 200,
            },
            _settlement_receipt(target=hybrid_target),
        ),
        "settlement_get": (
            "/forges/swarms/settlement",
            "swarm.settlement_get",
            {"scope": _scope(), "swarm_run_id": _SWARM_RUN_ID},
            {"workspace_id": _WORKSPACE_ID, "swarm_run_id": _SWARM_RUN_ID},
        ),
        "purge": (
            "/forges/swarms/purge",
            "swarm.purge",
            {"scope": _scope(), "actor": _actor(), "swarm_run_id": _SWARM_RUN_ID},
            {"workspace_id": _WORKSPACE_ID, "swarm_run_id": _SWARM_RUN_ID, "purged": True},
        ),
    }

    routes: RouteResponseTable = {}
    request_envelopes_by_path: dict[str, JsonObject] = {}
    expected_upstream_by_path: dict[str, JsonObject] = {}
    for name, (_, operation, _payload, result) in cases.items():
        request_id = f"aaaaaaaa-aaaa-aaaa-aaaa-{len(name):012d}"
        path = f"/api/v1/commands/{operation}"
        routes[("POST", path)] = (200, _success(request_id, result))
        request_envelopes_by_path[path] = {
            "forge_api": 1,
            "request_id": request_id,
            "op": operation,
            "payload": _payload,
        }
        expected_payload: JsonObject = {key: value for key, value in _payload.items()}
        if "actor" in expected_payload:
            expected_payload["actor"] = {
                "session_id": _SESSION_ID,
                "principal": {"kind": "trusted_stdio"},
                "workspace_id": _WORKSPACE_ID,
            }
        if operation == "swarm.converge":
            expected_payload["candidates"] = [{"member_id": _MEMBER_ID}]
        expected_upstream_by_path[path] = {
            "forge_api": 1,
            "request_id": request_id,
            "op": operation,
            "payload": expected_payload,
        }

    received: list[tuple[str, str | None, JsonObject]] = []

    def record_request(request: httpx.Request) -> None:
        payload = decode_json(request.content)
        assert isinstance(payload, dict)
        received.append((request.url.path, request.headers.get("authorization"), payload))

    with (
        GatewayTestClientBuilder()
        .with_route_table(routes, on_match=record_request)
        .build_client() as client
    ):
        responses = {
            name: client.post(
                route,
                json=request_envelopes_by_path[f"/api/v1/commands/{operation}"],
                headers={"Authorization": "Bearer forge-token"},
            )
            for name, (route, operation, _, _) in cases.items()
        }

    assert {name: response.status_code for name, response in responses.items()} == dict.fromkeys(
        cases,
        200,
    ), {name: response.json() for name, response in responses.items()}
    assert responses["converge"].json()["result"]["status"] == "conflict"
    assert responses["workspace_get"].json()["result"]["receipt"] is None
    assert responses["settle"].json()["result"]["outbox_sequence"] is None
    assert responses["settlement_get"].json()["result"]["receipt"] is None
    assert responses["settlement_get"].json()["result"]["outbox_entry"] is None
    assert len(received) == len(cases)
    assert all(authorization == "Bearer forge-token" for _, authorization, _ in received)
    for path, _, envelope in received:
        assert envelope == expected_upstream_by_path[path]


def test_swarm_response_schemas_require_nullable_source_fields_at_public_boundary() -> None:
    provision_response = _receipt(target={"kind": "standalone_swarm"})
    with pytest.raises(ValidationError):
        ForgeSwarmWorkspaceReceiptResult.model_validate_json(json.dumps(provision_response))

    workspace_lookup = {
        "workspace_id": _WORKSPACE_ID,
        "swarm_run_id": _SWARM_RUN_ID,
        "member_id": _MEMBER_ID,
        "found": False,
    }
    with pytest.raises(ValidationError):
        ForgeSwarmWorkspaceGetResult.model_validate_json(json.dumps(workspace_lookup))

    receipt = _settlement_receipt(target={"kind": "standalone_swarm"})
    with pytest.raises(ValidationError):
        ForgeSwarmSettleResult.model_validate_json(json.dumps({"receipt": receipt}))

    with pytest.raises(ValidationError):
        ForgeSwarmSettlementGetResult.model_validate_json(
            json.dumps({"workspace_id": _WORKSPACE_ID, "swarm_run_id": _SWARM_RUN_ID})
        )

    with pytest.raises(ValidationError):
        ForgeSwarmPurgeResult.model_validate_json(
            json.dumps({"workspace_id": _WORKSPACE_ID, "swarm_run_id": _SWARM_RUN_ID, "purged": 1})
        )

    with pytest.raises(ValidationError):
        ForgeSwarmPurgeCommandRequest.model_validate_json(
            json.dumps(
                {
                    "forge_api": True,
                    "request_id": "aaaaaaaa-aaaa-aaaa-aaaa-000000000001",
                    "op": "swarm.purge",
                    "payload": {
                        "scope": _scope(),
                        "actor": _actor(),
                        "swarm_run_id": _SWARM_RUN_ID,
                    },
                }
            )
        )


def test_swarm_routes_preserve_unknown_conflict_and_corrupt_result_semantics() -> None:
    from tests.shared.gateway_test_builder import GatewayTestClientBuilder

    unknown_request_id = "aaaaaaaa-aaaa-aaaa-aaaa-000000000101"
    conflict_request_id = "aaaaaaaa-aaaa-aaaa-aaaa-000000000102"
    corrupt_request_id = "aaaaaaaa-aaaa-aaaa-aaaa-000000000103"
    unknown_payload: JsonObject = {
        "scope": _scope(),
        "actor": _actor(),
        "swarm_run_id": _SWARM_RUN_ID,
        "member_id": _MEMBER_ID,
        "mode": "inherit",
        "target": {"kind": "standalone_swarm"},
        "candidate_commit_oid": None,
        "observed_at_ms": 100,
    }
    conflict_payload: JsonObject = {
        "scope": _scope(),
        "swarm_run_id": _SWARM_RUN_ID,
        "member_id": _MEMBER_ID,
    }
    corrupt_payload: JsonObject = {
        "scope": _scope(),
        "actor": _actor(),
        "swarm_run_id": _SWARM_RUN_ID,
    }
    unknown_readback: JsonObject = {
        "kind": "swarm_workspace",
        "workspace_id": _WORKSPACE_ID,
        "swarm_run_id": _SWARM_RUN_ID,
        "member_id": _MEMBER_ID,
    }
    routes: RouteResponseTable = {
        ("POST", "/api/v1/commands/swarm.workspace_provision"): (
            202,
            _failure(
                unknown_request_id,
                "UNKNOWN_OUTCOME",
                "unknown_outcome",
                "read_back",
                unknown_readback,
            ),
        ),
        ("POST", "/api/v1/commands/swarm.workspace_get"): (
            409,
            _failure(
                conflict_request_id,
                "WORKSPACE_IDENTITY_CONFLICT",
                "workspace_state",
                "inspect_workspace",
                None,
            ),
        ),
        ("POST", "/api/v1/commands/swarm.purge"): (
            200,
            _success(
                corrupt_request_id,
                {
                    "workspace_id": _WORKSPACE_ID,
                    "swarm_run_id": _SWARM_RUN_ID,
                    "purged": 1,
                },
            ),
        ),
    }
    with GatewayTestClientBuilder().with_route_table(routes).build_client() as client:
        unknown = client.post(
            "/forges/swarms/workspaces/provision",
            json=_command_body(
                unknown_request_id,
                "swarm.workspace_provision",
                unknown_payload,
            ),
            headers={"Authorization": "Bearer forge-token"},
        )
        conflict = client.post(
            "/forges/swarms/workspaces/inspect",
            json=_command_body(conflict_request_id, "swarm.workspace_get", conflict_payload),
            headers={"Authorization": "Bearer forge-token"},
        )
        corrupt = client.post(
            "/forges/swarms/purge",
            json=_command_body(corrupt_request_id, "swarm.purge", corrupt_payload),
            headers={"Authorization": "Bearer forge-token"},
        )

    assert unknown.status_code == 202
    assert unknown.json()["error"]["code"] == "UNKNOWN_OUTCOME"
    assert unknown.json()["error"]["readback"] == unknown_readback
    assert unknown.json()["request_id"] == unknown_request_id
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "WORKSPACE_IDENTITY_CONFLICT"
    assert conflict.json()["request_id"] == conflict_request_id
    assert corrupt.status_code == 502
    assert corrupt.json()["code"] == "forge_invalid_payload"
    assert corrupt.json()["request_id"] == corrupt_request_id


def test_swarm_routes_reject_source_identity_mismatches_per_operation_fixture() -> None:
    from tests.shared.gateway_test_builder import GatewayTestClientBuilder

    foreign_workspace_id = "21000000-0000-0000-0000-000000000021"
    foreign_run_id = "41000000-0000-0000-0000-000000000041"
    foreign_member_id = "51000000-0000-0000-0000-000000000051"
    workspace_payload: JsonObject = {
        "scope": _scope(),
        "swarm_run_id": _SWARM_RUN_ID,
        "member_id": _MEMBER_ID,
    }
    settlement_payload: JsonObject = {"scope": _scope(), "swarm_run_id": _SWARM_RUN_ID}
    mismatched_receipt = _receipt(target={"kind": "standalone_swarm"})
    mismatched_receipt["member_id"] = foreign_member_id
    mismatched_settlement_receipt = _settlement_receipt(target={"kind": "standalone_swarm"})
    mismatched_settlement_receipt["swarm_run_id"] = foreign_run_id
    mismatched_converged_commit = _settlement_receipt(target={"kind": "standalone_swarm"})
    mismatched_converged_commit["converged_commit_oid"] = "other-converged-commit"
    mismatched_hybrid_receipt = _settlement_receipt(
        target={
            "kind": "dag_node_hybrid",
            "goal_id": _GOAL_ID,
            "dag_revision": 5,
            "node_id": _NODE_ID,
        }
    )
    mismatched_outbox_entry: JsonObject = {
        "sequence": 1,
        "migration_id": "61000000-0000-0000-0000-000000000062",
        "destination_id": "61000000-0000-0000-0000-000000000063",
        "workspace_id": _WORKSPACE_ID,
        "fact": {
            "kind": "swarm_settled",
            "settlement_id": _SETTLEMENT_ID,
            "workspace_id": foreign_workspace_id,
            "activity_id": None,
            "swarm_run_id": _SWARM_RUN_ID,
            "settled_file_count": 4,
            "settled_tree_digest": "a" * 64,
            "converged_diff_digest": "b" * 64,
            "coordinator_agent_id": _COORDINATOR_ID,
            "coordinator_session_id": None,
            "settled_at_ms": 200,
        },
    }
    mismatch_cases: dict[str, tuple[str, str, JsonObject]] = {
        "workspace_outer_identity": (
            "/forges/swarms/workspaces/inspect",
            "swarm.workspace_get",
            {
                "workspace_id": foreign_workspace_id,
                "swarm_run_id": _SWARM_RUN_ID,
                "member_id": _MEMBER_ID,
                "found": False,
            },
        ),
        "workspace_nested_receipt_identity": (
            "/forges/swarms/workspaces/inspect",
            "swarm.workspace_get",
            {
                "workspace_id": _WORKSPACE_ID,
                "swarm_run_id": _SWARM_RUN_ID,
                "member_id": _MEMBER_ID,
                "found": True,
                "receipt": mismatched_receipt,
            },
        ),
        "settlement_nested_receipt_identity": (
            "/forges/swarms/settlement",
            "swarm.settlement_get",
            {
                "workspace_id": _WORKSPACE_ID,
                "swarm_run_id": _SWARM_RUN_ID,
                "receipt": mismatched_settlement_receipt,
                "outbox_entry": None,
            },
        ),
        "settlement_nested_fact_workspace": (
            "/forges/swarms/settlement",
            "swarm.settlement_get",
            {
                "workspace_id": _WORKSPACE_ID,
                "swarm_run_id": _SWARM_RUN_ID,
                "receipt": None,
                "outbox_entry": mismatched_outbox_entry,
            },
        ),
        "provision_mode_target": (
            "/forges/swarms/workspaces/provision",
            "swarm.workspace_provision",
            _receipt(
                target={
                    "kind": "dag_node_hybrid",
                    "goal_id": _GOAL_ID,
                    "dag_revision": 4,
                    "node_id": _NODE_ID,
                }
            ),
        ),
        "capture_run_member": (
            "/forges/swarms/members/capture",
            "swarm.member_capture",
            {
                "swarm_run_id": foreign_run_id,
                "member_id": _MEMBER_ID,
                "mode": "inherit",
                "input_commit_oid": "input-commit",
                "output_commit_oid": "output-commit",
                "initial_tree_blake3": "a" * 64,
                "final_tree_blake3": "e" * 64,
                "final_file_count": 4,
                "changed_paths": ["src/new.rs"],
                "diff_digest": "f" * 64,
                "captured_at_ms": 150,
            },
        ),
        "convergence_run": (
            "/forges/swarms/converge",
            "swarm.converge",
            {
                "status": "conflict",
                "swarm_run_id": foreign_run_id,
                "conflicting_member_id": _MEMBER_ID,
                "details": ["member output differs"],
            },
        ),
        "settlement_converged_commit": (
            "/forges/swarms/settle",
            "swarm.settle",
            {"receipt": mismatched_converged_commit},
        ),
        "hybrid_target_revision": (
            "/forges/swarms/materialize-hybrid",
            "swarm.materialize_hybrid",
            mismatched_hybrid_receipt,
        ),
        "purge_workspace": (
            "/forges/swarms/purge",
            "swarm.purge",
            {"workspace_id": foreign_workspace_id, "swarm_run_id": _SWARM_RUN_ID, "purged": True},
        ),
    }
    request_payloads = {
        "workspace_outer_identity": workspace_payload,
        "workspace_nested_receipt_identity": workspace_payload,
        "settlement_nested_receipt_identity": settlement_payload,
        "settlement_nested_fact_workspace": settlement_payload,
        "provision_mode_target": {
            "scope": _scope(),
            "actor": _actor(),
            "swarm_run_id": _SWARM_RUN_ID,
            "member_id": _MEMBER_ID,
            "mode": "inherit",
            "target": {"kind": "standalone_swarm"},
            "candidate_commit_oid": None,
            "observed_at_ms": 100,
        },
        "capture_run_member": {
            "scope": _scope(),
            "actor": _actor(),
            "swarm_run_id": _SWARM_RUN_ID,
            "member_id": _MEMBER_ID,
            "captured_at_ms": 150,
        },
        "convergence_run": {
            "scope": _scope(),
            "actor": _actor(),
            "swarm_run_id": _SWARM_RUN_ID,
            "candidates": [],
            "observed_at_ms": 160,
        },
        "settlement_converged_commit": {
            "scope": _scope(),
            "activity_id": None,
            "actor": _actor(),
            "coordinator_agent_id": _COORDINATOR_ID,
            "swarm_run_id": _SWARM_RUN_ID,
            "settlement_id": _SETTLEMENT_ID,
            "converged_commit_oid": "converged",
            "expected_diff_digest": None,
            "settled_at_ms": 200,
        },
        "hybrid_target_revision": {
            "scope": _scope(),
            "activity_id": _SESSION_ID,
            "actor": _actor(),
            "swarm_run_id": _SWARM_RUN_ID,
            "settlement_id": _SETTLEMENT_ID,
            "goal_id": _GOAL_ID,
            "expected_goal_revision": 5,
            "expected_dag_revision": 4,
            "node_id": _NODE_ID,
            "converged_commit_oid": "converged",
            "expected_diff_digest": None,
            "settled_at_ms": 200,
        },
        "purge_workspace": {"scope": _scope(), "actor": _actor(), "swarm_run_id": _SWARM_RUN_ID},
    }

    for index, (case_name, (route, operation, result)) in enumerate(mismatch_cases.items(), 1):
        request_id = f"bbbbbbbb-bbbb-bbbb-bbbb-{index:012d}"
        upstream_path = f"/api/v1/commands/{operation}"
        routes: RouteResponseTable = {
            ("POST", upstream_path): (200, _success(request_id, result)),
        }
        with GatewayTestClientBuilder().with_route_table(routes).build_client() as client:
            response = client.post(
                route,
                json=_command_body(request_id, operation, request_payloads[case_name]),
                headers={"Authorization": "Bearer forge-token"},
            )

        assert response.status_code == 502
        assert response.json()["code"] == "forge_invalid_payload"
        assert response.json()["request_id"] == request_id


def test_settlement_get_accepts_matching_receipt_and_outbox_identity() -> None:
    from tests.shared.gateway_test_builder import GatewayTestClientBuilder

    request_id = "cccccccc-cccc-cccc-cccc-000000000001"
    receipt = _settlement_receipt(target={"kind": "standalone_swarm"})
    result: JsonObject = {
        "workspace_id": _WORKSPACE_ID,
        "swarm_run_id": _SWARM_RUN_ID,
        "receipt": receipt,
        "outbox_entry": {
            "sequence": 1,
            "migration_id": "61000000-0000-0000-0000-000000000062",
            "destination_id": "61000000-0000-0000-0000-000000000063",
            "workspace_id": _WORKSPACE_ID,
            "fact": {
                "kind": "swarm_settled",
                "settlement_id": _SETTLEMENT_ID,
                "workspace_id": _WORKSPACE_ID,
                "activity_id": None,
                "swarm_run_id": _SWARM_RUN_ID,
                "settled_file_count": 4,
                "settled_tree_digest": "a" * 64,
                "converged_diff_digest": "b" * 64,
                "coordinator_agent_id": _COORDINATOR_ID,
                "coordinator_session_id": None,
                "settled_at_ms": 200,
            },
        },
    }
    routes: RouteResponseTable = {
        ("POST", "/api/v1/commands/swarm.settlement_get"): (200, _success(request_id, result)),
    }
    with GatewayTestClientBuilder().with_route_table(routes).build_client() as client:
        response = client.post(
            "/forges/swarms/settlement",
            json=_command_body(
                request_id,
                "swarm.settlement_get",
                {"scope": _scope(), "swarm_run_id": _SWARM_RUN_ID},
            ),
            headers={"Authorization": "Bearer forge-token"},
        )

    assert response.status_code == 200
    assert response.json()["result"]["receipt"]["settlement_id"] == _SETTLEMENT_ID
    assert response.json()["result"]["outbox_entry"]["fact"]["settlement_id"] == _SETTLEMENT_ID


def test_unknown_outcome_rejects_readback_for_another_swarm_workspace() -> None:
    from tests.shared.gateway_test_builder import GatewayTestClientBuilder

    request_id = "cccccccc-cccc-cccc-cccc-000000000002"
    foreign_readback: JsonObject = {
        "kind": "swarm_workspace",
        "workspace_id": "21000000-0000-0000-0000-000000000021",
        "swarm_run_id": _SWARM_RUN_ID,
        "member_id": _MEMBER_ID,
    }
    routes: RouteResponseTable = {
        ("POST", "/api/v1/commands/swarm.workspace_provision"): (
            202,
            _failure(
                request_id,
                "UNKNOWN_OUTCOME",
                "unknown_outcome",
                "read_back",
                foreign_readback,
            ),
        ),
    }
    with GatewayTestClientBuilder().with_route_table(routes).build_client() as client:
        response = client.post(
            "/forges/swarms/workspaces/provision",
            json=_command_body(
                request_id,
                "swarm.workspace_provision",
                {
                    "scope": _scope(),
                    "actor": _actor(),
                    "swarm_run_id": _SWARM_RUN_ID,
                    "member_id": _MEMBER_ID,
                    "mode": "inherit",
                    "target": {"kind": "standalone_swarm"},
                    "candidate_commit_oid": None,
                    "observed_at_ms": 100,
                },
            ),
            headers={"Authorization": "Bearer forge-token"},
        )

    assert response.status_code == 502
    assert response.json()["code"] == "forge_invalid_payload"
    assert response.json()["request_id"] == request_id
