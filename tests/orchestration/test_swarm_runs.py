"""Builder-based regression coverage Native Swarm run contracts."""

import httpx
from fastapi.testclient import TestClient
from pydantic import JsonValue

from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import (
    GatewayTestClientBuilder,
    RouteResponseTable,
)

_WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
_SWARM_RUN_ID = "00000000-0000-0000-0000-000000000002"
_CHANNEL_ID = "00000000-0000-0000-0000-000000000003"
_MEMBER_ID = "00000000-0000-0000-0000-000000000004"
_PROFILE_ID = "00000000-0000-0000-0000-000000000005"
_PARTICIPANT_ID = "00000000-0000-0000-0000-000000000006"
_REQUEST_ID = "00000000-0000-0000-0000-000000000007"
_GATEWAY_SWARM_PATH = f"/orchestrations/workspaces/{_WORKSPACE_ID}/swarms"
_SOURCE_SWARM_PATH = f"/v1/workspaces/{_WORKSPACE_ID}/swarms"


def run_payload(
    *,
    workspace_id: str = _WORKSPACE_ID,
    swarm_run_id: str = _SWARM_RUN_ID,
    replayed: bool = False,
    title: str = "Gateway contract run",
    state: str = "ACTIVE",
    created_at_ms: int = 100,
    updated_at_ms: int | None = None,
) -> JsonValue:
    """Build one source Swarm run response omitting Rust skip-serialized fields.

    Args:
        workspace_id: Source Workspace identity.
        swarm_run_id: Source Swarm run identity.
        replayed: Whether the source response represents an exact replay.
        title: Source run title.
        state: Source Swarm run state.
        created_at_ms: Source creation time.
        updated_at_ms: Source update time or creation time when omitted.
    Return:
        Source-shaped Swarm run JSON.
    """
    update_time = created_at_ms if updated_at_ms is None else updated_at_ms
    result: JsonValue = {
        "swarmRunId": swarm_run_id,
        "workspaceId": workspace_id,
        "title": title,
        "mode": {"kind": "STANDALONE"},
        "state": state,
        "maxMembers": 8,
        "maxSpawnDepth": 3,
        "maxTotalTurns": 64,
        "totalTurnsUsed": 0,
        "requiredVerifierQuorum": 1,
        "allowWorkerAllMention": False,
        "baselineCommitOid": "0123456789abcdef0123456789abcdef01234567",
        "baselineTreeBlake3Hex": "b" * 64,
        "stallNudgeCount": 0,
        "revision": 1,
        "createdAtMs": created_at_ms,
        "updatedAtMs": update_time,
        "replayed": replayed,
    }
    return result


def channel_payload(
    *,
    channel_id: str = _CHANNEL_ID,
    swarm_run_id: str = _SWARM_RUN_ID,
    workspace_id: str = _WORKSPACE_ID,
    name: str = "analysis",
) -> JsonValue:
    """Build one source channel response omitting optional channel properties.

    Args:
        channel_id: Source channel identity.
        swarm_run_id: Source Swarm run identity.
        workspace_id: Source Workspace identity.
        name: Source channel name.
    Return:
        Source-shaped Swarm channel JSON.
    """
    result: JsonValue = {
        "channelId": channel_id,
        "swarmRunId": swarm_run_id,
        "workspaceId": workspace_id,
        "name": name,
        "createdAtMs": 100,
    }
    return result


def member_payload(
    *,
    member_id: str = _MEMBER_ID,
    swarm_run_id: str = _SWARM_RUN_ID,
    workspace_id: str = _WORKSPACE_ID,
    member_state: str = "WAITING",
    roster_name: str = "worker-1",
) -> JsonValue:
    """Build one source member response omitting Rust skip-serialized fields.

    Args:
        member_id: Source member identity.
        swarm_run_id: Source Swarm run identity.
        workspace_id: Source Workspace identity.
        member_state: Source member state.
        roster_name: Source member roster name.
    Return:
        Source-shaped Swarm member JSON.
    """
    result: JsonValue = {
        "memberId": member_id,
        "swarmRunId": swarm_run_id,
        "workspaceId": workspace_id,
        "rosterName": roster_name,
        "roleKind": "WORKER",
        "spawnDepth": 0,
        "workspaceMode": "INHERIT",
        "memberState": member_state,
        "identity": {
            "profileId": _PROFILE_ID,
            "participantId": _PARTICIPANT_ID,
            "principal": {"kind": "trusted_stdio", "id": ""},
        },
        "committedSeenSeq": 0,
        "inflightTargetSeq": 0,
        "attemptEpoch": 1,
        "turnsUsed": 0,
        "pingPongStreak": 0,
        "createdAtMs": 100,
        "updatedAtMs": 100,
    }
    return result


def create_run_request_payload() -> JsonValue:
    """Build a complete public run request with explicit nullable source fields.

    Args:
        None.
    Return:
        Strict Gateway Swarm run request JSON.
    """
    result: JsonValue = {
        "requestId": _REQUEST_ID,
        "title": "Gateway contract run",
        "mode": {"kind": "STANDALONE", "hybridTarget": None},
        "maxMembers": 8,
        "maxSpawnDepth": 3,
        "maxTotalTurns": 64,
        "requiredVerifierQuorum": 1,
        "allowWorkerAllMention": False,
        "baselineCommitOid": "0123456789abcdef0123456789abcdef01234567",
        "baselineTreeBlake3Hex": "b" * 64,
        "scope": None,
    }
    return result


def add_member_request_payload() -> JsonValue:
    """Build a complete public member request with explicit nullable fields.

    Args:
        None.
    Return:
        Strict Gateway Swarm member request JSON.
    """
    result: JsonValue = {
        "memberId": _MEMBER_ID,
        "rosterName": "worker-1",
        "roleKind": "worker",
        "parentMemberId": None,
        "workspaceMode": "inherit",
        "worktreePath": None,
        "identity": {
            "profileId": _PROFILE_ID,
            "participantId": _PARTICIPANT_ID,
            "principal": {"kind": "trusted_stdio", "id": ""},
        },
        "initialChannels": [],
    }
    return result


def request_with_field(payload: JsonValue, key: str, value: JsonValue) -> JsonValue:
    """Return one copied public request with a single field replaced.

    Args:
        payload: Base public request JSON object.
        key: Public camelCase field to replace.
        value: Replacement JSON value.
    Return:
        Updated public request JSON object.
    """
    if not isinstance(payload, dict):
        raise ValueError("Request fixture must be a JSON object")
    updated_payload = payload.copy()
    updated_payload[key] = value
    result: JsonValue = updated_payload
    return result


def add_member_request_with_identity(identity: JsonValue) -> JsonValue:
    """Return one member request with a supplied identity fixture.

    Args:
        identity: Exact public execution identity JSON.
    Return:
        Updated public member request JSON object.
    """
    result = request_with_field(add_member_request_payload(), "identity", identity)
    return result


def make_client(
    method: str,
    path: str,
    status_code: int,
    payload: JsonValue,
    captured: list[httpx.Request],
) -> TestClient:
    """Build one isolated Orchestration source fixture client.

    Args:
        method: One source HTTP method.
        path: One exact source path.
        status_code: One source response status.
        payload: One source response body.
        captured: Requests recorded for the fixture.
    Return:
        Gateway TestClient with one isolated source fixture.
    """
    routes: RouteResponseTable = {(method, path): (status_code, payload)}
    client = (
        GatewayTestClientBuilder().with_route_table(routes, on_match=captured.append).build_client()
    )
    client.headers.update({"Authorization": "Bearer caller-token"})
    return client


def test_create_run_preserves_create_replay_statuses_and_source_omission() -> None:
    cases: dict[str, tuple[int, bool]] = {
        "new_run": (201, False),
        "exact_replay": (200, True),
    }
    for case_id, (source_status, replayed) in cases.items():
        captured: list[httpx.Request] = []
        response_payload: JsonValue = {
            "run": run_payload(replayed=replayed),
            "mainChannel": channel_payload(name="main"),
        }
        client = make_client("POST", _SOURCE_SWARM_PATH, source_status, response_payload, captured)
        with client:
            response = client.post(_GATEWAY_SWARM_PATH, json=create_run_request_payload())

        assert response.status_code == source_status, (case_id, response.text)
        assert response.json()["run"]["replayed"] is replayed, case_id
        assert response.json()["run"]["convergedCommitOid"] is None, case_id
        assert response.json()["mainChannel"]["purpose"] is None, case_id
        assert len(captured) == 1, case_id
        assert captured[0].url.path == _SOURCE_SWARM_PATH, case_id
        assert decode_json(captured[0].content) == {
            "requestId": _REQUEST_ID,
            "title": "Gateway contract run",
            "mode": {"kind": "STANDALONE"},
            "maxMembers": 8,
            "maxSpawnDepth": 3,
            "maxTotalTurns": 64,
            "requiredVerifierQuorum": 1,
            "allowWorkerAllMention": False,
            "baselineCommitOid": "0123456789abcdef0123456789abcdef01234567",
            "baselineTreeBlake3Hex": "b" * 64,
        }, case_id


def test_create_run_rejects_source_client_invalid_requests_before_transport() -> None:
    hybrid_target: JsonValue = {
        "goalId": _PROFILE_ID,
        "dagRevision": 1,
        "nodeId": _PARTICIPANT_ID,
        "declaredWriteManifestBlake3Hex": "a" * 64,
    }
    cases: dict[str, JsonValue] = {
        "noncanonical_request_id": request_with_field(
            create_run_request_payload(),
            "requestId",
            "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
        ),
        "nil_request_id": request_with_field(
            create_run_request_payload(),
            "requestId",
            "00000000-0000-0000-0000-000000000000",
        ),
        "blank_title": request_with_field(create_run_request_payload(), "title", " \t"),
        "zero_max_members": request_with_field(create_run_request_payload(), "maxMembers", 0),
        "zero_total_turns": request_with_field(create_run_request_payload(), "maxTotalTurns", 0),
        "zero_verifier_quorum": request_with_field(
            create_run_request_payload(), "requiredVerifierQuorum", 0
        ),
        "invalid_baseline_oid": request_with_field(
            create_run_request_payload(), "baselineCommitOid", "not-a-commit-oid"
        ),
        "zero_baseline_digest": request_with_field(
            create_run_request_payload(), "baselineTreeBlake3Hex", "0" * 64
        ),
        "standalone_with_hybrid_target": request_with_field(
            create_run_request_payload(),
            "mode",
            {"kind": "STANDALONE", "hybridTarget": hybrid_target},
        ),
        "hybrid_without_target": request_with_field(
            create_run_request_payload(),
            "mode",
            {"kind": "dagNodeHybrid", "hybridTarget": None},
        ),
        "zero_hybrid_dag_revision": request_with_field(
            create_run_request_payload(),
            "mode",
            {
                "kind": "DAG_NODE_HYBRID",
                "hybridTarget": {
                    "goalId": _PROFILE_ID,
                    "dagRevision": 0,
                    "nodeId": _PARTICIPANT_ID,
                    "declaredWriteManifestBlake3Hex": "a" * 64,
                },
            },
        ),
        "zero_hybrid_manifest_digest": request_with_field(
            create_run_request_payload(),
            "mode",
            {
                "kind": "DAG_NODE_HYBRID",
                "hybridTarget": {
                    "goalId": _PROFILE_ID,
                    "dagRevision": 1,
                    "nodeId": _PARTICIPANT_ID,
                    "declaredWriteManifestBlake3Hex": "0" * 64,
                },
            },
        ),
    }
    for case_id, payload in cases.items():
        captured: list[httpx.Request] = []
        client = make_client("POST", _SOURCE_SWARM_PATH, 201, run_payload(), captured)
        with client:
            response = client.post(_GATEWAY_SWARM_PATH, json=payload)

        assert response.status_code == 422, (case_id, response.text)
        assert captured == [], case_id


def test_create_run_rejects_scope_path_mismatch_before_transport() -> None:
    scopes: dict[str, JsonValue] = {
        "workspace_path_mismatch": {
            "workspaceId": "00000000-0000-0000-0000-000000000009",
            "locationId": "00000000-0000-0000-0000-000000000010",
            "locationRevision": 1,
            "workspaceRevision": 1,
            "locator": "v1:location:1:workspace",
        },
        "nil_location_id": {
            "workspaceId": _WORKSPACE_ID,
            "locationId": "00000000-0000-0000-0000-000000000000",
            "locationRevision": 1,
            "workspaceRevision": 1,
            "locator": "v1:location:1:workspace",
        },
    }
    for case_id, scope in scopes.items():
        payload = request_with_field(create_run_request_payload(), "scope", scope)
        captured: list[httpx.Request] = []
        client = make_client("POST", _SOURCE_SWARM_PATH, 201, run_payload(), captured)
        with client:
            response = client.post(_GATEWAY_SWARM_PATH, json=payload)

        assert response.status_code == 400, (case_id, response.text)
        assert captured == [], case_id


def test_run_routes_reject_noncanonical_and_nil_path_ids_before_transport() -> None:
    uppercase_uuid = "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"
    nil_uuid = "00000000-0000-0000-0000-000000000000"
    cases: dict[str, tuple[str, str, str]] = {
        "uppercase_workspace": (
            "GET",
            _SOURCE_SWARM_PATH,
            f"/orchestrations/workspaces/{uppercase_uuid}/swarms",
        ),
        "nil_workspace": (
            "GET",
            _SOURCE_SWARM_PATH,
            f"/orchestrations/workspaces/{nil_uuid}/swarms",
        ),
        "uppercase_run": (
            "GET",
            f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}",
            f"{_GATEWAY_SWARM_PATH}/{uppercase_uuid}",
        ),
        "nil_member": (
            "POST",
            f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}/members/{_MEMBER_ID}/kill",
            f"{_GATEWAY_SWARM_PATH}/{_SWARM_RUN_ID}/members/{nil_uuid}/kill",
        ),
    }
    for case_id, (method, source_path, gateway_path) in cases.items():
        captured: list[httpx.Request] = []
        client = make_client(method, source_path, 200, {}, captured)
        with client:
            response = (
                client.post(gateway_path, json={}) if method == "POST" else client.get(gateway_path)
            )

        assert response.status_code == 422, (case_id, response.text)
        assert captured == [], case_id


def test_list_runs_checks_requested_count_and_run_readback_contracts() -> None:
    second_run_id = "00000000-0000-0000-0000-000000000008"
    cases: dict[str, tuple[list[JsonValue], int, int]] = {
        "valid_ordered_list": (
            [run_payload(), run_payload(swarm_run_id=second_run_id)],
            2,
            200,
        ),
        "over_requested_count": (
            [run_payload(), run_payload(swarm_run_id=second_run_id)],
            1,
            502,
        ),
        "empty_title": ([run_payload(title="")], 1, 502),
        "whitespace_title": ([run_payload(title=" ")], 1, 200),
        "negative_creation_time": ([run_payload(created_at_ms=-1)], 1, 502),
        "update_before_creation": (
            [run_payload(created_at_ms=101, updated_at_ms=100)],
            1,
            502,
        ),
        "unknown_run_state": ([run_payload(state="UNKNOWN")], 1, 502),
    }
    for case_id, (runs, requested_limit, expected_status) in cases.items():
        captured: list[httpx.Request] = []
        client = make_client("GET", _SOURCE_SWARM_PATH, 200, {"runs": runs}, captured)
        with client:
            response = client.get(_GATEWAY_SWARM_PATH, params={"limit": requested_limit})

        assert response.status_code == expected_status, (case_id, response.text)
        assert len(captured) == 1, case_id
        assert captured[0].url.params["limit"] == str(requested_limit), case_id
        if case_id == "valid_ordered_list":
            assert [run["swarmRunId"] for run in response.json()["runs"]] == [
                _SWARM_RUN_ID,
                second_run_id,
            ]
        if case_id == "whitespace_title":
            assert response.json()["runs"][0]["title"] == " ", case_id


def test_inspection_normalizes_optional_fields_and_checks_path_identity() -> None:
    source_path = f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}"
    gateway_path = f"{_GATEWAY_SWARM_PATH}/{_SWARM_RUN_ID}"
    source_payload: JsonValue = {
        "run": run_payload(),
        "channels": [channel_payload(name="main")],
        "members": [member_payload()],
        "subscriptions": [],
        "pendingDoorbells": [],
        "verdicts": [],
    }
    cases: dict[str, tuple[JsonValue, int]] = {
        "valid_snapshot": (source_payload, 200),
        "foreign_run": (
            {
                "run": run_payload(workspace_id="00000000-0000-0000-0000-000000000009"),
                "channels": [],
                "members": [],
                "subscriptions": [],
                "pendingDoorbells": [],
                "verdicts": [],
            },
            502,
        ),
    }
    for case_id, (payload, expected_status) in cases.items():
        captured: list[httpx.Request] = []
        client = make_client("GET", source_path, 200, payload, captured)
        with client:
            response = client.get(gateway_path)

        assert response.status_code == expected_status, (case_id, response.text)
        assert len(captured) == 1, case_id
        if expected_status == 200:
            assert response.json()["verificationPanel"] is None, case_id
            assert response.json()["members"][0]["activeSnapshotId"] is None, case_id


def test_create_channel_forwards_null_optionals_as_source_omission() -> None:
    source_path = f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}/channels"
    gateway_path = f"{_GATEWAY_SWARM_PATH}/{_SWARM_RUN_ID}/channels"
    captured: list[httpx.Request] = []
    client = make_client("POST", source_path, 201, channel_payload(), captured)
    request_payload: JsonValue = {
        "channelId": _CHANNEL_ID,
        "name": "analysis",
        "purpose": None,
        "createdByMemberId": None,
    }
    with client:
        response = client.post(gateway_path, json=request_payload)

    assert response.status_code == 201, response.text
    assert response.json()["purpose"] is None
    assert decode_json(captured[0].content) == {"channelId": _CHANNEL_ID, "name": "analysis"}


def test_create_channel_rejects_invalid_source_client_requests_before_transport() -> None:
    source_path = f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}/channels"
    gateway_path = f"{_GATEWAY_SWARM_PATH}/{_SWARM_RUN_ID}/channels"
    valid_request: JsonValue = {
        "channelId": _CHANNEL_ID,
        "name": "analysis",
        "purpose": None,
        "createdByMemberId": None,
    }
    cases: dict[str, JsonValue] = {
        "noncanonical_channel_id": request_with_field(
            valid_request,
            "channelId",
            "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
        ),
        "nil_channel_id": request_with_field(
            valid_request,
            "channelId",
            "00000000-0000-0000-0000-000000000000",
        ),
        "blank_channel_name": request_with_field(valid_request, "name", " \t"),
        "noncanonical_creator_id": request_with_field(
            valid_request,
            "createdByMemberId",
            "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
        ),
    }
    for case_id, payload in cases.items():
        captured: list[httpx.Request] = []
        client = make_client("POST", source_path, 201, channel_payload(), captured)
        with client:
            response = client.post(gateway_path, json=payload)

        assert response.status_code == 422, (case_id, response.text)
        assert captured == [], case_id


def test_subscribe_channel_preserves_source_result_identity() -> None:
    source_path = f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}/channels/{_CHANNEL_ID}/subscriptions"
    gateway_path = f"{_GATEWAY_SWARM_PATH}/{_SWARM_RUN_ID}/channels/{_CHANNEL_ID}/subscriptions"
    captured: list[httpx.Request] = []
    payload: JsonValue = {
        "swarmRunId": _SWARM_RUN_ID,
        "channelId": _CHANNEL_ID,
        "memberId": _MEMBER_ID,
        "newlySubscribed": True,
    }
    client = make_client("POST", source_path, 200, payload, captured)
    with client:
        response = client.post(gateway_path, json={"memberId": _MEMBER_ID})

    assert response.status_code == 200, response.text
    assert response.json() == payload
    assert decode_json(captured[0].content) == {"memberId": _MEMBER_ID}


def test_add_member_canonicalizes_inputs_and_preserves_source_conflict() -> None:
    source_path = f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}/members"
    gateway_path = f"{_GATEWAY_SWARM_PATH}/{_SWARM_RUN_ID}/members"
    cases: dict[str, tuple[int, JsonValue, int]] = {
        "created": (201, member_payload(), 201),
        "empty_roster_name": (201, member_payload(roster_name=""), 502),
        "whitespace_roster_name": (201, member_payload(roster_name=" "), 201),
        "source_conflict": (
            409,
            {
                "code": "invalid_worktree_path",
                "message": "Worktree path is rejected",
                "retryable": False,
            },
            409,
        ),
    }
    for case_id, (source_status, payload, expected_status) in cases.items():
        captured: list[httpx.Request] = []
        client = make_client("POST", source_path, source_status, payload, captured)
        with client:
            response = client.post(gateway_path, json=add_member_request_payload())

        assert response.status_code == expected_status, (case_id, response.text)
        assert len(captured) == 1, case_id
        body = decode_json(captured[0].content)
        if expected_status == 201:
            assert isinstance(body, dict), case_id
            assert response.json()["memberState"] == "WAITING", case_id
            if case_id == "whitespace_roster_name":
                assert response.json()["rosterName"] == " ", case_id
            assert body["roleKind"] == "WORKER", case_id
            assert body["workspaceMode"] == "INHERIT", case_id
            assert "parentMemberId" not in body, case_id
            assert "worktreePath" not in body, case_id
        elif expected_status == 409:
            assert response.json()["code"] == "invalid_worktree_path", case_id
        else:
            assert response.json()["code"] == "orchestration_invalid_payload", case_id


def test_add_member_rejects_invalid_source_client_requests_before_transport() -> None:
    source_path = f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}/members"
    direct_token_identity: JsonValue = {
        "profileId": _PROFILE_ID,
        "participantId": _PARTICIPANT_ID,
        "principal": {
            "kind": "direct_token",
            "id": "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
        },
    }
    nil_direct_token_identity: JsonValue = {
        "profileId": _PROFILE_ID,
        "participantId": _PARTICIPANT_ID,
        "principal": {
            "kind": "direct_token",
            "id": "00000000-0000-0000-0000-000000000000",
        },
    }
    trusted_stdio_identity: JsonValue = {
        "profileId": _PROFILE_ID,
        "participantId": _PARTICIPANT_ID,
        "principal": {"kind": "trusted_stdio", "id": "not-empty"},
    }
    unsupported_principal_identity: JsonValue = {
        "profileId": _PROFILE_ID,
        "participantId": _PARTICIPANT_ID,
        "principal": {"kind": "unknown", "id": ""},
    }
    cases: dict[str, JsonValue] = {
        "noncanonical_member_id": request_with_field(
            add_member_request_payload(),
            "memberId",
            "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
        ),
        "nil_member_id": request_with_field(
            add_member_request_payload(),
            "memberId",
            "00000000-0000-0000-0000-000000000000",
        ),
        "blank_roster_name": request_with_field(add_member_request_payload(), "rosterName", " \t"),
        "unsupported_role": request_with_field(
            add_member_request_payload(), "roleKind", "reviewer"
        ),
        "unsupported_workspace_mode": request_with_field(
            add_member_request_payload(), "workspaceMode", "sandbox"
        ),
        "nil_parent_member_id": request_with_field(
            add_member_request_payload(),
            "parentMemberId",
            "00000000-0000-0000-0000-000000000000",
        ),
        "noncanonical_parent_member_id": request_with_field(
            add_member_request_payload(),
            "parentMemberId",
            "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
        ),
        "nil_profile_id": add_member_request_with_identity(
            {
                "profileId": "00000000-0000-0000-0000-000000000000",
                "participantId": _PARTICIPANT_ID,
                "principal": {"kind": "trusted_stdio", "id": ""},
            }
        ),
        "noncanonical_participant_id": add_member_request_with_identity(
            {
                "profileId": _PROFILE_ID,
                "participantId": "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA",
                "principal": {"kind": "trusted_stdio", "id": ""},
            }
        ),
        "noncanonical_direct_token_id": add_member_request_with_identity(direct_token_identity),
        "nil_direct_token_id": add_member_request_with_identity(nil_direct_token_identity),
        "trusted_stdio_with_identifier": add_member_request_with_identity(trusted_stdio_identity),
        "unsupported_principal_kind": add_member_request_with_identity(
            unsupported_principal_identity
        ),
    }
    for case_id, payload in cases.items():
        captured: list[httpx.Request] = []
        client = make_client("POST", source_path, 201, member_payload(), captured)
        with client:
            response = client.post(
                f"{_GATEWAY_SWARM_PATH}/{_SWARM_RUN_ID}/members",
                json=payload,
            )

        assert response.status_code == 422, (case_id, response.text)
        assert captured == [], case_id


def test_kill_member_requires_empty_body_and_returns_cascade_members() -> None:
    source_path = f"{_SOURCE_SWARM_PATH}/{_SWARM_RUN_ID}/members/{_MEMBER_ID}/kill"
    gateway_path = f"{_GATEWAY_SWARM_PATH}/{_SWARM_RUN_ID}/members/{_MEMBER_ID}/kill"
    captured: list[httpx.Request] = []
    client = make_client(
        "POST",
        source_path,
        200,
        {"killedMembers": [member_payload(member_state="KILLED")]},
        captured,
    )
    with client:
        response = client.post(gateway_path, json={})

    assert response.status_code == 200, response.text
    assert [member["memberId"] for member in response.json()["killedMembers"]] == [_MEMBER_ID]
    assert decode_json(captured[0].content) == {}
    assert captured[0].headers["authorization"] == "Bearer caller-token"
