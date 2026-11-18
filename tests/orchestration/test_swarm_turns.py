"""Builder-based regression coverage Native Swarm turn contracts."""

import asyncio
from collections.abc import Callable
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import JsonValue

from app.orchestration.application.swarm.swarm_turn_app import (
    SwarmTurnApplication,
    build_dispatch_exchange_policy,
)
from app.orchestration.schema.swarm.orchestration_swarm_turn_schema import (
    ClaimSwarmWakeupRequest,
    DispatchSwarmTurnRequest,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder, RouteResponseTable

_WORKSPACE_ID = "00000000-0000-7000-8000-000000000001"
_RUN_ID = "00000000-0000-7000-8000-000000000002"
_MEMBER_ID = "00000000-0000-7000-8000-000000000003"
_SNAPSHOT_ID = "00000000-0000-7000-8000-000000000004"
_SNAPSHOT_REQUEST_ID = "00000000-0000-7000-8000-000000000005"
_ACTIVITY_ID = "00000000-0000-7000-8000-000000000006"
_LEASE_ID = "00000000-0000-7000-8000-000000000007"
_PROFILE_ID = "00000000-0000-7000-8000-000000000008"
_REQUEST_ID = "00000000-0000-7000-8000-000000000009"
_GOAL_ID = "00000000-0000-7000-8000-000000000010"
_NODE_ID = "00000000-0000-7000-8000-000000000011"
_ASSIGNMENT_ID = "00000000-0000-7000-8000-000000000012"
_CHANNEL_ID = "00000000-0000-7000-8000-000000000013"
_MESSAGE_ID = "00000000-0000-7000-8000-000000000014"
_TOKEN_ID = "00000000-0000-7000-8000-000000000015"  # noqa: S105 - principal fixture, not a credential.


def _member_payload(
    *,
    member_id: str = _MEMBER_ID,
    member_state: str = "WORKING",
    workspace_id: str = _WORKSPACE_ID,
    swarm_run_id: str = _RUN_ID,
) -> dict[str, JsonValue]:
    """Build a source-shaped member with legal omitted nullable fields.

    Args:
        member_id: Member identity to project.
        member_state: Canonical source member state.
        workspace_id: Workspace identity to project.
        swarm_run_id: Swarm run identity to project.
    Return:
        Decoded source member fixture.
    """
    result: dict[str, JsonValue] = {
        "memberId": member_id,
        "swarmRunId": swarm_run_id,
        "workspaceId": workspace_id,
        "rosterName": "worker-1",
        "roleKind": "WORKER",
        "spawnDepth": 0,
        "workspaceMode": "INHERIT",
        "memberState": member_state,
        "identity": {
            "profileId": _PROFILE_ID,
            "participantId": _REQUEST_ID,
            "principal": {"kind": "direct_token", "id": _TOKEN_ID},
        },
        "committedSeenSeq": 0,
        "inflightTargetSeq": 1,
        "attemptEpoch": 1,
        "turnsUsed": 0,
        "pingPongStreak": 0,
        "createdAtMs": 1,
        "updatedAtMs": 2,
    }
    return result


def _message_payload() -> dict[str, JsonValue]:
    """Build a board message omitting source-skipped author fields.

    Args:
        None.
    Return:
        Decoded source board-message fixture.
    """
    result: dict[str, JsonValue] = {
        "messageId": _MESSAGE_ID,
        "workspaceId": _WORKSPACE_ID,
        "sequence": 1,
        "swarmRunId": _RUN_ID,
        "channelId": _CHANNEL_ID,
        "channelName": "main",
        "authorRosterName": "worker-1",
        "body": "ready",
        "submittedAtMs": 3,
    }
    return result


def _wakeup_payload() -> dict[str, JsonValue]:
    """Build a source wakeup batch with one unread board message.

    Args:
        None.
    Return:
        Decoded source wakeup-batch fixture.
    """
    result: dict[str, JsonValue] = {
        "swarmRunId": _RUN_ID,
        "member": _member_payload(),
        "snapshotId": _SNAPSHOT_ID,
        "committedSeenSeq": 0,
        "inflightTargetSeq": 1,
        "messages": [_message_payload()],
        "totalBodyBytes": 5,
    }
    return result


def _preference_payload(*, include_nullable: bool) -> dict[str, JsonValue]:
    """Build an execution preference with explicit input nullable controls.

    Args:
        include_nullable: Whether source response nullable keys are present.
    Return:
        Decoded source execution preference fixture.
    """
    result: dict[str, JsonValue] = {
        "cliEngine": "codex",
        "preferredModel": "codex-frontier",
        "capabilities": ["research"],
    }
    if include_nullable:
        result["preferredReasoning"] = None
        result["rolePromptDigestHex"] = None
    return result


def _launch_ledger_payload() -> dict[str, JsonValue]:
    """Build the launch-ledger output while omitting nullable source fields.

    Args:
        None.
    Return:
        Decoded launch-ledger record fixture.
    """
    result: dict[str, JsonValue] = {
        "snapshotId": _SNAPSHOT_ID,
        "workspaceId": _WORKSPACE_ID,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": 0,
        "state": {"status": "EXITED"},
        "revision": 1,
        "updatedAtMs": 4,
    }
    return result


def _committed_snapshot_payload() -> dict[str, JsonValue]:
    """Build the frozen source execution snapshot fixture.

    Args:
        None.
    Return:
        Decoded committed snapshot fixture.
    """
    result: dict[str, JsonValue] = {
        "snapshotId": _SNAPSHOT_ID,
        "workspaceId": _WORKSPACE_ID,
        "goalId": _GOAL_ID,
        "dagRevision": 2,
        "nodeId": _NODE_ID,
        "assignmentId": _ASSIGNMENT_ID,
        "attempt": 0,
        "activityId": _ACTIVITY_ID,
        "profileId": _PROFILE_ID,
        "profileRevision": 1,
        "resolvedEngine": "codex",
        "resolvedModel": "codex-frontier",
        "worktreePath": "/workspace/swarm-worker-1",
        "leaseId": _LEASE_ID,
        "leaseRevision": 1,
        "leaseExpiresAtMs": 99_999,
        "permissions": {
            "allowWorkspaceWrite": True,
            "allowLocalShell": False,
            "allowNetwork": False,
        },
        "timeouts": {
            "startupTimeoutMs": 100,
            "executionTimeoutMs": 200,
            "terminationGraceMs": 50,
        },
        "committedAtMs": 5,
    }
    return result


def _dispatch_payload() -> dict[str, JsonValue]:
    """Build a complete dispatch receipt with omitted nullable observations.

    Args:
        None.
    Return:
        Decoded dispatch response fixture.
    """
    result: dict[str, JsonValue] = {
        "wakeupBatch": _wakeup_payload(),
        "committedSnapshot": _committed_snapshot_payload(),
        "supervision": {"status": "EXITED", "ledger": _launch_ledger_payload()},
        "disposition": {
            "kind": "COMPLETED",
            "member": _member_payload(member_state="WAITING"),
            "timedOut": False,
        },
        "usedParentSpawnerSlot": True,
    }
    return result


def _model_switch_payload() -> dict[str, JsonValue]:
    """Build a source model-switch receipt with nullable preference omissions.

    Args:
        None.
    Return:
        Decoded model-switch response fixture.
    """
    result: dict[str, JsonValue] = {
        "member": _member_payload(member_state="WAKE_QUEUED"),
        "profileId": _PROFILE_ID,
        "profileRevision": 2,
        "resolvedPreference": _preference_payload(include_nullable=False),
    }
    return result


def _build_client(
    routes: RouteResponseTable,
    *,
    on_match: Callable[[httpx.Request], None] | None = None,
) -> TestClient:
    """Build an isolated Gateway test client and upstream route table.

    Args:
        routes: Source method/path response fixtures.
        on_match: Optional callback recording forwarded upstream requests.
    Return:
        Fresh Gateway TestClient.
    """
    client = GatewayTestClientBuilder().with_route_table(routes, on_match=on_match).build_client()
    client.headers["Authorization"] = "Bearer swarm-turn-test"
    return client


def _request_cases() -> dict[str, tuple[str, str, dict[str, JsonValue], JsonValue]]:
    """Group the five public routes with their source requests and results.

    Args:
        None.
    Return:
        Named route fixtures with public path, source path, request body and response body.
    """
    workspace_path = f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/members/{_MEMBER_ID}"
    request_path = (
        f"/orchestrations/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/members/{_MEMBER_ID}"
    )
    result: dict[str, tuple[str, str, dict[str, JsonValue], JsonValue]] = {
        "claim": (
            f"{request_path}/turns/claim",
            f"{workspace_path}/turns/claim",
            {"snapshotId": _SNAPSHOT_ID},
            _wakeup_payload(),
        ),
        "complete": (
            f"{request_path}/turns/complete",
            f"{workspace_path}/turns/complete",
            {
                "expectedSnapshotId": _SNAPSHOT_ID,
                "outputCommitOid": None,
                "outputTreeBlake3Hex": None,
            },
            _member_payload(member_state="WAITING"),
        ),
        "fail": (
            f"{request_path}/turns/fail",
            f"{workspace_path}/turns/fail",
            {
                "expectedSnapshotId": _SNAPSHOT_ID,
                "disposition": "transient_retry",
                "consumeTurn": False,
            },
            _member_payload(member_state="WAKE_QUEUED"),
        ),
        "dispatch": (
            f"{request_path}/turns/dispatch",
            f"{workspace_path}/turns/dispatch",
            {
                "snapshotRequestId": _SNAPSHOT_REQUEST_ID,
                "snapshotId": _SNAPSHOT_ID,
                "activityId": _ACTIVITY_ID,
                "defaultWorktreePath": "/workspace/swarm-worker-1",
                "leaseId": _LEASE_ID,
                "leaseRevision": 1,
                "leaseExpiresAtMs": 99_999,
                "mcpGrant": None,
                "permissions": {
                    "allowWorkspaceWrite": True,
                    "allowLocalShell": False,
                    "allowNetwork": False,
                },
                "timeouts": {
                    "startupTimeoutMs": 100,
                    "executionTimeoutMs": 200,
                    "terminationGraceMs": 50,
                },
                "dispatchedAtMs": None,
                "cleanExitOutputCommitOid": None,
                "cleanExitOutputTreeBlake3Hex": None,
                "forgeSessionId": None,
            },
            _dispatch_payload(),
        ),
        "model_switch": (
            f"{request_path}/model-switch",
            f"{workspace_path}/model-switch",
            {
                "newProfileId": _PROFILE_ID,
                "requestId": None,
                "profileId": None,
                "expectedProfileRevision": None,
                "newPreference": None,
            },
            _model_switch_payload(),
        ),
    }
    return result


def test_five_turn_routes_preserve_source_paths_statuses_and_nullable_outputs() -> None:
    """Forward the five Source operations and validate their typed readbacks.

    Args:
        None.
    Return:
        None.
    """
    cases = _request_cases()
    for case_id, (request_path, source_path, body, payload) in cases.items():
        captured: list[httpx.Request] = []
        client = _build_client(
            {("POST", source_path): (200, payload)},
            on_match=captured.append,
        )
        with client:
            response = client.post(request_path, json=body)

        assert response.status_code == 200, (case_id, response.text)
        assert len(captured) == 1, case_id
        assert captured[0].method == "POST", case_id
        assert captured[0].url.path == source_path, case_id
        upstream_body = dict(body)
        if case_id == "fail":
            upstream_body["disposition"] = "TRANSIENT_RETRY"
        assert decode_json(captured[0].content) == upstream_body, case_id
        response_body = response.json()
        if case_id == "claim":
            assert response_body["messages"][0]["authorMemberId"] is None
            assert response_body["member"]["parentMemberId"] is None
        if case_id in {"complete", "fail"}:
            assert response_body["parentMemberId"] is None
        if case_id == "dispatch":
            assert response_body["committedSnapshot"]["resolvedReasoning"] is None
            assert response_body["supervision"]["ledger"]["state"]["ownership"] is None
            assert response_body["disposition"]["member"]["parentMemberId"] is None
        if case_id == "model_switch":
            assert response_body["resolvedPreference"]["preferredReasoning"] is None


def test_turn_routes_forward_both_optional_values_and_switch_shapes() -> None:
    """Preserve Some/None request controls for completion, dispatch and switching.

    Args:
        None.
    Return:
        None.
    """
    cases = _request_cases()
    complete_path, complete_source, _, _ = cases["complete"]
    complete_body: dict[str, JsonValue] = {
        "expectedSnapshotId": _SNAPSHOT_ID,
        "outputCommitOid": "a" * 40,
        "outputTreeBlake3Hex": "b" * 64,
    }
    dispatch_path, dispatch_source, dispatch_body, dispatch_response = cases["dispatch"]
    dispatch_body["defaultWorktreePath"] = ""
    dispatch_body["forgeSessionId"] = _ACTIVITY_ID
    dispatch_body["mcpGrant"] = {
        "tokenId": _TOKEN_ID,
        "issuedAtMs": 10,
        "expiresAtMs": 20,
    }
    dispatch_body["dispatchedAtMs"] = 15
    dispatch_body["cleanExitOutputCommitOid"] = "a" * 40
    dispatch_body["cleanExitOutputTreeBlake3Hex"] = "b" * 64
    fail_path, fail_source, fail_body, fail_response = cases["fail"]
    fail_body["consumeTurn"] = True
    update_path, update_source, _, update_response = cases["model_switch"]
    update_body: dict[str, JsonValue] = {
        "newProfileId": None,
        "requestId": _REQUEST_ID,
        "profileId": _PROFILE_ID,
        "expectedProfileRevision": 1,
        "newPreference": _preference_payload(include_nullable=True),
    }
    some_cases: dict[str, tuple[str, str, dict[str, JsonValue], JsonValue]] = {
        "complete_some": (complete_path, complete_source, complete_body, _member_payload()),
        "fail_consume": (fail_path, fail_source, fail_body, fail_response),
        "dispatch_some": (dispatch_path, dispatch_source, dispatch_body, dispatch_response),
        "model_update": (update_path, update_source, update_body, update_response),
    }
    for case_id, (request_path, source_path, body, payload) in some_cases.items():
        captured: list[httpx.Request] = []
        client = _build_client(
            {("POST", source_path): (200, payload)},
            on_match=captured.append,
        )
        with client:
            response = client.post(request_path, json=body)

        assert response.status_code == 200, (case_id, response.text)
        assert len(captured) == 1, case_id
        upstream_body = dict(body)
        if case_id == "fail_consume":
            upstream_body["disposition"] = "TRANSIENT_RETRY"
        assert decode_json(captured[0].content) == upstream_body, case_id


def test_turn_routes_preserve_typed_backend_409_rejections() -> None:
    """Keep backend conflict bodies and statuses for every mutation route.

    Args:
        None.
    Return:
        None.
    """
    rejection: dict[str, JsonValue] = {
        "code": "MEMBER_NOT_WORKING",
        "message": "Member turn is not working.",
        "retryable": False,
    }
    for case_id, (request_path, source_path, body, _) in _request_cases().items():
        client = _build_client({("POST", source_path): (409, rejection)})
        with client:
            response = client.post(request_path, json=body)

        assert response.status_code == 409, case_id
        assert response.json() == rejection, case_id


def test_swarm_dispatch_preserves_gateway_timeout_status() -> None:
    """Retain a source timeout response and its typed backend error body.

    Args:
        None.
    Return:
        None.
    """
    request_path, source_path, body, _ = _request_cases()["dispatch"]
    timeout: dict[str, JsonValue] = {
        "code": "UPSTREAM_TIMEOUT",
        "message": "Swarm dispatch exceeded its bounded deadline.",
        "retryable": True,
    }
    client = _build_client({("POST", source_path): (504, timeout)})
    with client:
        response = client.post(request_path, json=body)

    assert response.status_code == 504
    assert response.json() == timeout


def test_turn_routes_reject_correlated_source_identity_mismatches() -> None:
    """Fail closed when source readbacks escape route or snapshot identity.

    Args:
        None.
    Return:
        None.
    """
    cases = _request_cases()
    bad_claim = _wakeup_payload()
    bad_claim["snapshotId"] = _ACTIVITY_ID
    bad_complete = _member_payload(member_id=_ACTIVITY_ID)
    bad_fail = _member_payload(workspace_id=_ACTIVITY_ID)
    bad_dispatch = _dispatch_payload()
    supervision = bad_dispatch["supervision"]
    assert isinstance(supervision, dict)
    ledger = supervision["ledger"]
    assert isinstance(ledger, dict)
    ledger["workspaceId"] = _ACTIVITY_ID
    bad_switch = _model_switch_payload()
    bad_switch["profileRevision"] = 0
    mismatch_cases: dict[str, tuple[str, JsonValue]] = {
        "claim_snapshot": ("claim", bad_claim),
        "complete_member": ("complete", bad_complete),
        "fail_workspace": ("fail", bad_fail),
        "dispatch_ledger_workspace": ("dispatch", bad_dispatch),
        "model_switch_revision": ("model_switch", bad_switch),
    }
    for case_id, (route_id, payload) in mismatch_cases.items():
        request_path, source_path, body, _ = cases[route_id]
        client = _build_client(
            {("POST", source_path): (200, payload)},
        )
        with client:
            response = client.post(request_path, json=body)

        assert response.status_code == 502, case_id
        assert response.json()["code"] == "orchestration_invalid_payload", case_id


def test_turn_routes_reject_bad_identity_overflow_and_non_boolean_inputs() -> None:
    """Reject malformed IDs, source integer overflow and integer booleans pre-call.

    Args:
        None.
    Return:
        None.
    """
    _, _, dispatch_body, _ = _request_cases()["dispatch"]
    bad_dispatch_id = dict(dispatch_body)
    bad_dispatch_id["snapshotId"] = "00000000-0000-7000-8000-0000000000AF"
    bad_nil_id = dict(dispatch_body)
    bad_nil_id["snapshotId"] = "00000000-0000-0000-0000-000000000000"
    bad_revision = dict(dispatch_body)
    bad_revision["leaseRevision"] = 2**63
    bad_boolean = dict(dispatch_body)
    bad_worktree = dict(dispatch_body)
    bad_worktree["defaultWorktreePath"] = ""
    permissions = dict(dispatch_body["permissions"])
    permissions["allowNetwork"] = 1
    bad_boolean["permissions"] = permissions
    request_path = f"/orchestrations/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/members/{_MEMBER_ID}/turns/dispatch"
    malformed_path = (
        f"/orchestrations/workspaces/00000000-0000-7000-8000-00000000000A/swarms/{_RUN_ID}"
        f"/members/{_MEMBER_ID}/turns/dispatch"
    )
    cases: dict[str, tuple[str, dict[str, JsonValue]]] = {
        "noncanonical_path_uuid": (malformed_path, dispatch_body),
        "noncanonical_body_uuid": (request_path, bad_dispatch_id),
        "nil_body_uuid": (request_path, bad_nil_id),
        "signed_revision_overflow": (request_path, bad_revision),
        "integer_as_boolean": (request_path, bad_boolean),
        "empty_worktree_without_session": (request_path, bad_worktree),
    }
    for case_id, (path, body) in cases.items():
        client = _build_client({})
        with client:
            response = client.post(path, json=body)
        assert response.status_code == 422, case_id


def test_swarm_dispatch_request_cap_returns_typed_413_without_forwarding() -> None:
    """Apply the 128-KiB Swarm request cap before the upstream exchange.

    Args:
        None.
    Return:
        None.
    """
    request_path, _, body, _ = _request_cases()["dispatch"]
    oversized_body = dict(body)
    oversized_body["defaultWorktreePath"] = "x" * 131_073
    forwarded: list[httpx.Request] = []
    client = _build_client({}, on_match=forwarded.append)
    with client:
        response = client.post(request_path, json=oversized_body)

    assert response.status_code == 413
    assert response.json()["code"] == "orchestration_request_too_large"
    assert forwarded == []


def test_dispatch_exchange_deadline_uses_runtime_floor_phase_budget_and_cap() -> None:
    """Preserve the source phase sum while bounding the dispatch HTTP deadline.

    Args:
        None.
    Return:
        None.
    """
    _, _, request_body, _ = _request_cases()["dispatch"]
    default_request = DispatchSwarmTurnRequest.model_validate(request_body)
    default_policy = build_dispatch_exchange_policy(default_request, 120.0)
    assert default_policy.timeout_seconds == 120.0
    assert default_policy.max_request_bytes == 131_072
    assert default_policy.max_response_bytes == 2_097_152

    long_request_body = dict(request_body)
    long_request_body["timeouts"] = {
        "startupTimeoutMs": 400_000,
        "executionTimeoutMs": 400_000,
        "terminationGraceMs": 400_000,
    }
    long_request = DispatchSwarmTurnRequest.model_validate(long_request_body)
    capped_policy = build_dispatch_exchange_policy(long_request, 2.0)
    assert capped_policy.timeout_seconds == 900.0


class _CancellationTransport(httpx.AsyncBaseTransport):
    """Raise task cancellation at the actual Orchestration transport boundary."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        """Cancel the active caller without translating it to an HTTP response.

        Args:
            request: Request handed to the source transport.
        Return:
            Never returns because the request task is cancelled.
        """
        _ = request
        raise asyncio.CancelledError


def test_turn_application_propagates_transport_cancellation() -> None:
    """Keep cancellation observable through the application and shared caller.

    Args:
        None.
    Return:
        None.
    """

    async def execute() -> None:
        transport = _CancellationTransport()
        async with httpx.AsyncClient(transport=transport, timeout=1.0) as client:
            calling = OrchestrationCalling(client, "http://orchestration.test")
            application = SwarmTurnApplication(calling)
            request = ClaimSwarmWakeupRequest.model_validate({"snapshotId": _SNAPSHOT_ID})
            await application.claim_turn(
                UUID(_WORKSPACE_ID),
                UUID(_RUN_ID),
                UUID(_MEMBER_ID),
                request,
            )

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(execute())
