"""Builder-based regressions for Native Swarm board contracts."""

import httpx
from fastapi.testclient import TestClient
from pydantic import JsonValue

from app.shared.types.base_types import JsonObject
from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder, RouteResponseTable

_WORKSPACE_ID = "00000000-0000-0000-0000-000000000101"
_RUN_ID = "00000000-0000-0000-0000-000000000102"
_MESSAGE_ID = "00000000-0000-0000-0000-000000000103"
_OTHER_MESSAGE_ID = "00000000-0000-0000-0000-000000000104"
_CHANNEL_ID = "00000000-0000-0000-0000-000000000105"
_OTHER_CHANNEL_ID = "00000000-0000-0000-0000-000000000106"
_AUTHOR_ID = "00000000-0000-0000-0000-000000000107"
_VERIFIER_ID = "00000000-0000-0000-0000-000000000108"
_OTHER_VERIFIER_ID = "00000000-0000-0000-0000-000000000109"
_REQUEST_ID = "00000000-0000-0000-0000-000000000110"
_OTHER_REQUEST_ID = "00000000-0000-0000-0000-000000000111"
_PANEL_ID = "00000000-0000-0000-0000-000000000112"
_OTHER_PANEL_ID = "00000000-0000-0000-0000-000000000113"
_DIGEST = "1" + "0" * 63
_ZERO_DIGEST = "0" * 64
_BASE_PATH = f"/orchestrations/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}"
_BASE_TEMPLATE = "/orchestrations/workspaces/{workspace_id}/swarms/{swarm_run_id}"


def _message_payload(
    *,
    message_id: str = _MESSAGE_ID,
    workspace_id: str = _WORKSPACE_ID,
    swarm_run_id: str = _RUN_ID,
    sequence: int = 1,
    channel_id: str = _CHANNEL_ID,
    author_member_id: str | None = None,
    author_epoch: int | None = None,
    body: str = "Board update",
) -> JsonObject:
    """Build a fresh canonical source message with legal skip fields omitted.

    Args:
        message_id: Source message UUID.
        workspace_id: Source Workspace UUID.
        swarm_run_id: Source Swarm run UUID.
        sequence: Source board sequence.
        channel_id: Source channel UUID.
        author_member_id: Optional source member UUID.
        author_epoch: Optional source author attempt epoch.
        body: Source message body.
    Return:
        Fresh source-shaped message object.
    """
    result: JsonObject = {
        "messageId": message_id,
        "workspaceId": workspace_id,
        "sequence": sequence,
        "swarmRunId": swarm_run_id,
        "channelId": channel_id,
        "channelName": "main",
        "authorRosterName": "System" if author_member_id is None else "worker",
        "body": body,
        "submittedAtMs": 20,
    }
    if author_member_id is not None:
        result["authorMemberId"] = author_member_id
    if author_epoch is not None:
        result["authorEpoch"] = author_epoch
    return result


def _run_payload(
    *,
    workspace_id: str = _WORKSPACE_ID,
    swarm_run_id: str = _RUN_ID,
    title: str = "Board Run",
    revision: int = 1,
    created_at_ms: int = 10,
    updated_at_ms: int = 11,
    allow_worker_all_mention: bool = False,
) -> JsonObject:
    """Build one fresh source Swarm run while omitting skipped nullable keys.

    Args:
        workspace_id: Source Workspace UUID.
        swarm_run_id: Source Swarm run UUID.
        title: Source run title.
        revision: Source run revision.
        created_at_ms: Source creation time.
        updated_at_ms: Source update time.
        allow_worker_all_mention: Source run mention policy.
    Return:
        Fresh source-shaped run object.
    """
    result: JsonObject = {
        "swarmRunId": swarm_run_id,
        "workspaceId": workspace_id,
        "title": title,
        "mode": {"kind": "STANDALONE"},
        "state": "ACTIVE",
        "maxMembers": 4,
        "maxSpawnDepth": 2,
        "maxTotalTurns": 12,
        "totalTurnsUsed": 1,
        "requiredVerifierQuorum": 1,
        "allowWorkerAllMention": allow_worker_all_mention,
        "baselineCommitOid": "a" * 40,
        "baselineTreeBlake3Hex": _DIGEST,
        "stallNudgeCount": 0,
        "revision": revision,
        "createdAtMs": created_at_ms,
        "updatedAtMs": updated_at_ms,
        "replayed": False,
    }
    return result


def _post_message_response(
    *,
    message: JsonObject | None = None,
    replayed: bool = False,
    woken_member_ids: list[str] | None = None,
    coalesced_member_ids: list[str] | None = None,
) -> JsonObject:
    """Build one fresh source post-message response.

    Args:
        message: Source message or None to create the normal fixture.
        replayed: Source idempotency replay flag.
        woken_member_ids: Source member UUIDs woken by the post.
        coalesced_member_ids: Source member UUIDs with coalesced doorbells.
    Return:
        Fresh source-shaped post response.
    """
    woken: list[JsonValue] = []
    coalesced: list[JsonValue] = []
    if woken_member_ids is not None:
        woken.extend(woken_member_ids)
    if coalesced_member_ids is not None:
        coalesced.extend(coalesced_member_ids)
    result: JsonObject = {
        "message": _message_payload() if message is None else message,
        "wokenMemberIds": woken,
        "coalescedDoorbellMemberIds": coalesced,
        "replayed": replayed,
    }
    return result


def _panel_payload(
    *,
    panel_id: str = _PANEL_ID,
    workspace_id: str = _WORKSPACE_ID,
    swarm_run_id: str = _RUN_ID,
    required_quorum: int = 1,
    replayed: bool = False,
) -> JsonObject:
    """Build one fresh canonical source verification panel.

    Args:
        panel_id: Source panel UUID.
        workspace_id: Source Workspace UUID.
        swarm_run_id: Source Swarm run UUID.
        required_quorum: Source verifier quorum.
        replayed: Source idempotency replay flag.
    Return:
        Fresh source-shaped panel object.
    """
    result: JsonObject = {
        "panelId": panel_id,
        "swarmRunId": swarm_run_id,
        "workspaceId": workspace_id,
        "requiredQuorum": required_quorum,
        "autoCreated": False,
        "seats": [],
        "createdAtMs": 20,
        "replayed": replayed,
    }
    return result


def _verdict_payload(
    *,
    verdict_id: str = "00000000-0000-0000-0000-000000000114",
    request_id: str = _REQUEST_ID,
    panel_id: str = _PANEL_ID,
    swarm_run_id: str = _RUN_ID,
    verifier_member_id: str = _VERIFIER_ID,
    outcome: str = "ACCEPTED",
    reviewed_digest: str = _DIGEST,
    replayed: bool = False,
) -> JsonObject:
    """Build one fresh source canonical verdict record.

    Args:
        verdict_id: Source verdict UUID.
        request_id: Source idempotency UUID.
        panel_id: Source panel UUID.
        swarm_run_id: Source run UUID.
        verifier_member_id: Source verifier UUID.
        outcome: Source canonical outcome.
        reviewed_digest: Source reviewed diff digest.
        replayed: Source idempotency replay flag.
    Return:
        Fresh source-shaped verdict object.
    """
    result: JsonObject = {
        "verdictId": verdict_id,
        "requestId": request_id,
        "panelId": panel_id,
        "swarmRunId": swarm_run_id,
        "verifierMemberId": verifier_member_id,
        "outcome": outcome,
        "reviewedDiffDigestHex": reviewed_digest,
        "rationale": "Reviewed the candidate.",
        "recordedAtMs": 20,
        "replayed": replayed,
    }
    return result


def _gate_payload() -> JsonObject:
    """Build one fresh verified convergence gate.

    Args:
        None.
    Return:
        Source-shaped convergence gate with one accepted verdict.
    """
    result: JsonObject = {
        "panelId": _PANEL_ID,
        "swarmRunId": _RUN_ID,
        "convergedDiffDigestHex": _DIGEST,
        "requiredQuorum": 1,
        "acceptedVerdicts": [_verdict_payload()],
    }
    return result


def _convergence_payload(
    *,
    run: JsonObject | None = None,
    settled: bool = False,
    gate: JsonObject | None = None,
) -> JsonObject:
    """Build one fresh source convergence or settlement response.

    Args:
        run: Source run or None to create the normal fixture.
        settled: Source settled flag.
        gate: Optional source quorum gate.
    Return:
        Fresh source-shaped convergence response.
    """
    result: JsonObject = {
        "run": _run_payload() if run is None else run,
        "settled": settled,
    }
    if gate is not None:
        result["gate"] = gate
    return result


def _page_payload(
    messages: list[JsonValue],
    *,
    next_after_sequence: int | None = None,
    has_more: bool = False,
) -> JsonObject:
    """Build a fresh source page with next cursor omitted when absent.

    Args:
        messages: Source ordered board messages.
        next_after_sequence: Optional source cursor.
        has_more: Source continuation flag.
    Return:
        Fresh source-shaped board page.
    """
    result: JsonObject = {"messages": messages, "hasMore": has_more}
    if next_after_sequence is not None:
        result["nextAfterSequence"] = next_after_sequence
    return result


def _stall_payload(
    *,
    action: str = "NOOP",
    run_state: str | None = None,
    working_members: int | None = None,
    target_member_id: str | None = None,
    run: JsonObject | None = None,
) -> JsonObject:
    """Build a fresh stall report with actual source skip fields omitted.

    Args:
        action: Source action string.
        run_state: Optional canonical source run state.
        working_members: Optional source working member count.
        target_member_id: Optional source target UUID.
        run: Optional source run state.
    Return:
        Fresh source-shaped stall report.
    """
    stopped_members: list[JsonValue] = []
    result: JsonObject = {"action": action, "stoppedMembers": stopped_members}
    if run_state is not None:
        result["runState"] = run_state
    if working_members is not None:
        result["workingMembers"] = working_members
    if target_member_id is not None:
        result["targetMemberId"] = target_member_id
    if run is not None:
        result["run"] = run
    return result


def _client(
    method: str,
    path: str,
    status_code: int,
    payload: JsonValue,
    captured: list[httpx.Request],
) -> TestClient:
    """Build one Gateway client and capture its mocked upstream request.

    Args:
        method: Upstream HTTP method.
        path: Upstream route path.
        status_code: Mocked source status.
        payload: Mocked source JSON body.
        captured: Mutable request observation list.
    Return:
        Built Gateway TestClient.
    """
    routes: RouteResponseTable = {(method, path): (status_code, payload)}
    result = (
        GatewayTestClientBuilder().with_route_table(routes, on_match=captured.append).build_client()
    )
    return result


def _post_message_request(
    *,
    channel_id: str | None = None,
    author_member_id: str | None = None,
) -> JsonObject:
    """Build a Gateway post request with required nullable optionals.

    Args:
        channel_id: Optional requested channel UUID.
        author_member_id: Optional requested author UUID.
    Return:
        Public Gateway request body.
    """
    result: JsonObject = {
        "messageId": _MESSAGE_ID,
        "channelId": channel_id,
        "authorMemberId": author_member_id,
        "body": "Board update",
    }
    return result


def _panel_request() -> JsonObject:
    """Build a valid panel creation request.

    Args:
        None.
    Return:
        Public Gateway panel request body.
    """
    result: JsonObject = {
        "requestId": _REQUEST_ID,
        "authorMemberIds": [_AUTHOR_ID],
        "verifierMemberIds": [_VERIFIER_ID],
        "requiredQuorum": 1,
    }
    return result


def _verdict_request(
    *,
    panel_id: str | None,
    outcome: str,
) -> JsonObject:
    """Build a valid verdict request with a required nullable panel ID.

    Args:
        panel_id: Explicit panel UUID or None for source selection.
        outcome: One source-accepted verdict spelling.
    Return:
        Public Gateway verdict request body.
    """
    result: JsonObject = {
        "requestId": _REQUEST_ID,
        "panelId": panel_id,
        "verifierMemberId": _VERIFIER_ID,
        "outcome": outcome,
        "reviewedDiffDigestHex": _DIGEST,
        "rationale": "Reviewed the candidate.",
    }
    return result


def _converge_request(
    *,
    target_state: str | None,
    stage_candidate_only: bool = False,
) -> JsonObject:
    """Build a convergence request with required nullable target state.

    Args:
        target_state: Optional source-accepted convergence target.
        stage_candidate_only: Whether to stage without settlement.
    Return:
        Public Gateway convergence request body.
    """
    result: JsonObject = {
        "requestId": _REQUEST_ID,
        "convergedCommitOid": "a" * 40,
        "convergedTreeBlake3Hex": _DIGEST,
        "convergedDiffDigestHex": _DIGEST,
        "targetState": target_state,
        "stageCandidateOnly": stage_candidate_only,
    }
    return result


def _expect_source_body(request: httpx.Request) -> JsonValue:
    """Decode the exact mocked upstream request JSON body.

    Args:
        request: Captured request emitted by Gateway.
    Return:
        Typed decoded JSON request value.
    """
    result = decode_json(request.content)
    return result


def test_post_message_preserves_optional_fields_and_replay_status() -> None:
    cases: dict[str, tuple[int, str | None, str | None, bool]] = {
        "created_without_optional_fields": (201, None, None, False),
        "replayed_with_explicit_channel_and_author": (200, _CHANNEL_ID, _AUTHOR_ID, True),
    }
    for case_id, (expected_status, channel_id, author_member_id, replayed) in cases.items():
        message = _message_payload(
            channel_id=_CHANNEL_ID if channel_id is None else channel_id,
            author_member_id=author_member_id,
            author_epoch=1 if author_member_id is not None else None,
        )
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/messages",
            expected_status,
            _post_message_response(message=message, replayed=replayed),
            captured,
        )
        with client:
            response = client.post(
                f"{_BASE_PATH}/messages",
                json=_post_message_request(
                    channel_id=channel_id,
                    author_member_id=author_member_id,
                ),
            )
        assert response.status_code == expected_status, (case_id, response.text)
        assert response.json()["replayed"] is replayed, case_id
        assert len(captured) == 1, case_id
        expected_body: JsonObject = {"messageId": _MESSAGE_ID, "body": "Board update"}
        if channel_id is not None:
            expected_body["channelId"] = channel_id
        if author_member_id is not None:
            expected_body["authorMemberId"] = author_member_id
        assert _expect_source_body(captured[0]) == expected_body, case_id


def test_post_message_rejects_source_correlation_and_replay_mismatches() -> None:
    cases: dict[str, tuple[int, JsonValue]] = {
        "wrong_message_id": (
            201,
            _post_message_response(message=_message_payload(message_id=_OTHER_MESSAGE_ID)),
        ),
        "foreign_workspace": (
            201,
            _post_message_response(message=_message_payload(workspace_id=_OTHER_MESSAGE_ID)),
        ),
        "foreign_run": (
            201,
            _post_message_response(message=_message_payload(swarm_run_id=_OTHER_MESSAGE_ID)),
        ),
        "zero_sequence": (
            201,
            _post_message_response(message=_message_payload(sequence=0)),
        ),
        "wrong_explicit_channel": (
            201,
            _post_message_response(message=_message_payload(channel_id=_OTHER_CHANNEL_ID)),
        ),
        "wrong_author": (
            201,
            _post_message_response(
                message=_message_payload(author_member_id=_OTHER_VERIFIER_ID, author_epoch=1),
            ),
        ),
        "replay_status_mismatch": (
            201,
            _post_message_response(replayed=True),
        ),
    }
    for case_id, (upstream_status, payload) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/messages",
            upstream_status,
            payload,
            captured,
        )
        with client:
            response = client.post(
                f"{_BASE_PATH}/messages",
                json=_post_message_request(
                    channel_id=_CHANNEL_ID,
                    author_member_id=_AUTHOR_ID,
                ),
            )
        assert response.status_code == 502, (case_id, response.text)


def test_read_board_page_forwards_optional_query_and_normalizes_cursor() -> None:
    large_messages: list[JsonValue] = [
        _message_payload(
            sequence=sequence,
            message_id=f"00000000-0000-0000-0000-{sequence:012x}",
        )
        for sequence in range(1, 10)
    ]
    cases: dict[str, tuple[str, int, int, int | None, JsonValue]] = {
        "filtered_page": (
            "?sinceSequence=4&channelId=" + _CHANNEL_ID + "&limit=2",
            6,
            1,
            5,
            _page_payload(
                [_message_payload(sequence=5, author_member_id=_AUTHOR_ID, author_epoch=2)],
                next_after_sequence=5,
                has_more=True,
            ),
        ),
        "defaulted_page": (
            "",
            0,
            1,
            None,
            _page_payload([_message_payload(sequence=1)]),
        ),
        "large_parallel_page": (
            "?limit=9",
            0,
            9,
            9,
            _page_payload(large_messages, next_after_sequence=9),
        ),
    }
    for case_id, (query, cursor, expected_count, next_sequence, payload) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "GET",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/messages",
            200,
            payload,
            captured,
        )
        with client:
            response = client.get(f"{_BASE_PATH}/messages{query}")
        assert response.status_code == 200, (case_id, response.text)
        assert len(response.json()["messages"]) == expected_count, case_id
        assert len(captured) == 1, case_id
        if query:
            assert captured[0].url.query.decode() == query[1:], case_id
        else:
            assert captured[0].url.query == b"", case_id
        assert response.json().get("nextAfterSequence") == next_sequence, case_id
        if case_id == "large_parallel_page":
            sequences = [message["sequence"] for message in response.json()["messages"]]
            assert sequences == list(range(1, 10)), (case_id, cursor)


def test_read_board_page_rejects_bad_order_scope_channel_and_cursor() -> None:
    cases: dict[str, tuple[str, int, JsonValue]] = {
        "at_cursor": (
            "?sinceSequence=5",
            200,
            _page_payload([_message_payload(sequence=5)]),
        ),
        "foreign_workspace": (
            "",
            200,
            _page_payload([_message_payload(workspace_id=_OTHER_MESSAGE_ID)]),
        ),
        "foreign_run": (
            "",
            200,
            _page_payload([_message_payload(swarm_run_id=_OTHER_MESSAGE_ID)]),
        ),
        "wrong_channel": (
            "?channelId=" + _CHANNEL_ID,
            200,
            _page_payload([_message_payload(channel_id=_OTHER_CHANNEL_ID)]),
        ),
        "out_of_order": (
            "",
            200,
            _page_payload([_message_payload(sequence=2), _message_payload(sequence=1)]),
        ),
        "too_many": (
            "?limit=1",
            200,
            _page_payload([_message_payload(sequence=1), _message_payload(sequence=2)]),
        ),
        "numeric_boolean_sequence": (
            "",
            200,
            _page_payload([_message_payload(sequence=True)]),
        ),
    }
    for case_id, (query, upstream_status, payload) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "GET",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/messages",
            upstream_status,
            payload,
            captured,
        )
        with client:
            response = client.get(f"{_BASE_PATH}/messages{query}")
        assert response.status_code == 502, (case_id, response.text)


def test_read_board_page_rejects_duplicate_and_unknown_query_keys() -> None:
    queries = {
        "duplicate_cursor": "sinceSequence=1&sinceSequence=2",
        "unknown_key": "other=1",
    }
    for case_id, query in queries.items():
        captured: list[httpx.Request] = []
        client = _client(
            "GET",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/messages",
            200,
            _page_payload([]),
            captured,
        )
        with client:
            response = client.get(f"{_BASE_PATH}/messages?{query}")
        assert response.status_code == 422, case_id
        assert not captured, case_id


def test_panel_create_preserves_replay_status_and_echoes() -> None:
    cases: dict[str, tuple[int, bool]] = {
        "created": (201, False),
        "replayed": (200, True),
    }
    for case_id, (expected_status, replayed) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/panels",
            expected_status,
            _panel_payload(replayed=replayed),
            captured,
        )
        with client:
            response = client.post(f"{_BASE_PATH}/panels", json=_panel_request())
        assert response.status_code == expected_status, (case_id, response.text)
        assert response.json()["replayed"] is replayed, case_id
        assert len(captured) == 1, case_id
        assert _expect_source_body(captured[0]) == {
            "requestId": _REQUEST_ID,
            "authorMemberIds": [_AUTHOR_ID],
            "verifierMemberIds": [_VERIFIER_ID],
            "requiredQuorum": 1,
        }, case_id


def test_panel_create_rejects_id_scope_quorum_and_status_mismatch() -> None:
    cases: dict[str, tuple[int, JsonValue]] = {
        "nil_panel_id": (201, _panel_payload(panel_id="00000000-0000-0000-0000-000000000000")),
        "foreign_workspace": (201, _panel_payload(workspace_id=_OTHER_MESSAGE_ID)),
        "foreign_run": (201, _panel_payload(swarm_run_id=_OTHER_MESSAGE_ID)),
        "wrong_quorum": (201, _panel_payload(required_quorum=2)),
        "replayed_wrong_status": (201, _panel_payload(replayed=True)),
    }
    for case_id, (upstream_status, payload) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/panels",
            upstream_status,
            payload,
            captured,
        )
        with client:
            response = client.post(f"{_BASE_PATH}/panels", json=_panel_request())
        assert response.status_code == 502, (case_id, response.text)


def test_verdict_panel_omission_and_source_outcome_aliases() -> None:
    cases: dict[str, tuple[int, str | None, str, bool]] = {
        "new_without_panel_lowercase": (201, None, "accepted", False),
        "replayed_with_panel_camel_case": (200, _PANEL_ID, "needsChanges", True),
    }
    for case_id, (expected_status, panel_id, outcome, replayed) in cases.items():
        expected_panel = _PANEL_ID if panel_id is None else panel_id
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/verdicts",
            expected_status,
            _verdict_payload(
                panel_id=expected_panel,
                outcome="NEEDS_CHANGES" if replayed else "ACCEPTED",
                replayed=replayed,
            ),
            captured,
        )
        with client:
            response = client.post(
                f"{_BASE_PATH}/verdicts",
                json=_verdict_request(panel_id=panel_id, outcome=outcome),
            )
        assert response.status_code == expected_status, (case_id, response.text)
        assert response.json()["outcome"] == ("NEEDS_CHANGES" if replayed else "ACCEPTED"), case_id
        expected_body: JsonObject = {
            "requestId": _REQUEST_ID,
            "verifierMemberId": _VERIFIER_ID,
            "outcome": "NEEDS_CHANGES" if replayed else "ACCEPTED",
            "reviewedDiffDigestHex": _DIGEST,
            "rationale": "Reviewed the candidate.",
        }
        if panel_id is not None:
            expected_body["panelId"] = panel_id
        assert _expect_source_body(captured[0]) == expected_body, case_id


def test_verdict_rejects_response_echo_and_numeric_boolean_mismatches() -> None:
    numeric_boolean_verdict = _verdict_payload()
    numeric_boolean_verdict["recordedAtMs"] = True
    cases: dict[str, tuple[int, JsonValue]] = {
        "nil_verdict_id": (
            201,
            _verdict_payload(verdict_id="00000000-0000-0000-0000-000000000000"),
        ),
        "wrong_request_id": (201, _verdict_payload(request_id=_OTHER_REQUEST_ID)),
        "wrong_run_id": (201, _verdict_payload(swarm_run_id=_OTHER_MESSAGE_ID)),
        "wrong_verifier": (201, _verdict_payload(verifier_member_id=_OTHER_VERIFIER_ID)),
        "nil_panel_id": (
            201,
            _verdict_payload(panel_id="00000000-0000-0000-0000-000000000000"),
        ),
        "wrong_requested_panel": (201, _verdict_payload(panel_id=_OTHER_PANEL_ID)),
        "wrong_replay_status": (201, _verdict_payload(replayed=True)),
        "numeric_boolean_time": (201, numeric_boolean_verdict),
    }
    for case_id, (upstream_status, payload) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/verdicts",
            upstream_status,
            payload,
            captured,
        )
        with client:
            response = client.post(
                f"{_BASE_PATH}/verdicts",
                json=_verdict_request(panel_id=_PANEL_ID, outcome="ACCEPTED"),
            )
        assert response.status_code == 502, (case_id, response.text)


def test_converge_omits_null_target_and_normalizes_source_alias() -> None:
    cases: dict[str, tuple[str | None, str]] = {
        "no_target": (None, "a" * 40),
        "source_camel_target": ("candidateReady", "a" * 40),
        "preserved_trimmed_uppercase_oid": (None, f" {'A' * 40} "),
    }
    for case_id, (target_state, commit_oid) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/converge",
            200,
            _convergence_payload(settled=False),
            captured,
        )
        request_body = _converge_request(target_state=target_state)
        request_body["convergedCommitOid"] = commit_oid
        with client:
            response = client.post(
                f"{_BASE_PATH}/converge",
                json=request_body,
            )
        assert response.status_code == 200, (case_id, response.text)
        assert response.json()["settled"] is False, case_id
        expected_body: JsonObject = {
            "requestId": _REQUEST_ID,
            "convergedCommitOid": commit_oid,
            "convergedTreeBlake3Hex": _DIGEST,
            "convergedDiffDigestHex": _DIGEST,
            "stageCandidateOnly": False,
        }
        if target_state is not None:
            expected_body["targetState"] = "CANDIDATE_READY"
        assert _expect_source_body(captured[0]) == expected_body, case_id


def test_converge_rejects_foreign_or_invalid_source_run_and_candidate_pair() -> None:
    numeric_boolean_run = _convergence_payload()
    numeric_run = numeric_boolean_run["run"]
    assert isinstance(numeric_run, dict)
    numeric_run["allowWorkerAllMention"] = 1
    cases: dict[str, tuple[JsonValue, JsonObject]] = {
        "foreign_run": (
            _convergence_payload(run=_run_payload(swarm_run_id=_OTHER_MESSAGE_ID)),
            _converge_request(target_state=None),
        ),
        "invalid_run_update_time": (
            _convergence_payload(run=_run_payload(created_at_ms=20, updated_at_ms=19)),
            _converge_request(target_state=None),
        ),
        "numeric_boolean_run_flag": (
            numeric_boolean_run,
            _converge_request(target_state=None),
        ),
    }
    for case_id, (payload, request_body) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/converge",
            200,
            payload,
            captured,
        )
        with client:
            response = client.post(f"{_BASE_PATH}/converge", json=request_body)
        assert response.status_code == 502, (case_id, response.text)


def test_converge_rejects_source_invalid_stage_settled_combination() -> None:
    captured: list[httpx.Request] = []
    client = GatewayTestClientBuilder().build_client()
    with client:
        response = client.post(
            f"{_BASE_PATH}/converge",
            json=_converge_request(target_state="settled", stage_candidate_only=True),
        )
    assert response.status_code == 422
    assert not captured

    invalid_requests: dict[str, JsonObject] = {
        "zero_digest": _converge_request(target_state=None),
        "invalid_commit_oid": _converge_request(target_state=None),
    }
    invalid_requests["zero_digest"]["convergedDiffDigestHex"] = _ZERO_DIGEST
    invalid_requests["invalid_commit_oid"]["convergedCommitOid"] = "not-an-oid"
    for case_id, request_body in invalid_requests.items():
        client = GatewayTestClientBuilder().build_client()
        with client:
            invalid_response = client.post(f"{_BASE_PATH}/converge", json=request_body)
        assert invalid_response.status_code == 422, case_id


def test_settle_requires_settled_run_and_abort_sends_empty_json_body() -> None:
    cases: dict[str, tuple[str, int, JsonValue, JsonObject]] = {
        "settle": (
            "POST",
            200,
            _convergence_payload(settled=True, gate=_gate_payload()),
            dict(requestId=_REQUEST_ID),
        ),
        "abort": (
            "POST",
            200,
            _run_payload(),
            dict(),
        ),
    }
    for case_id, (method, expected_status, payload, request_body) in cases.items():
        leaf = "settle" if case_id == "settle" else "abort"
        captured: list[httpx.Request] = []
        client = _client(
            method,
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/{leaf}",
            expected_status,
            payload,
            captured,
        )
        with client:
            response = client.post(f"{_BASE_PATH}/{leaf}", json=request_body)
        assert response.status_code == expected_status, (case_id, response.text)
        assert len(captured) == 1, case_id
        assert _expect_source_body(captured[0]) == request_body, case_id
        if case_id == "settle":
            assert response.json()["settled"] is True

    captured = []
    client = _client(
        "POST",
        f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/settle",
        200,
        _convergence_payload(settled=False),
        captured,
    )
    with client:
        response = client.post(f"{_BASE_PATH}/settle", json={"requestId": _REQUEST_ID})
    assert response.status_code == 502


def test_stall_check_omits_null_thresholds_and_allows_zero_nudge_limit() -> None:
    cases: dict[str, tuple[JsonObject, JsonObject]] = {
        "all_null": (
            dict(
                stallGraceMs=None,
                maxStallNudges=None,
                maxPingPongStreak=None,
                maxMemberTurns=None,
                observedAtMs=None,
            ),
            dict(action="NOOP"),
        ),
        "some_thresholds": (
            dict(
                stallGraceMs=10,
                maxStallNudges=0,
                maxPingPongStreak=2,
                maxMemberTurns=3,
                observedAtMs=0,
            ),
            _stall_payload(
                run_state="ACTIVE",
                working_members=1,
                target_member_id=_AUTHOR_ID,
                run=_run_payload(),
            ),
        ),
    }
    for case_id, (request_body, response_body) in cases.items():
        captured: list[httpx.Request] = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/stall-check",
            200,
            response_body,
            captured,
        )
        with client:
            response = client.post(f"{_BASE_PATH}/stall-check", json=request_body)
        assert response.status_code == 200, (case_id, response.text)
        assert response.json()["action"] == "NOOP", case_id
        expected_body: JsonObject = {}
        if case_id == "some_thresholds":
            expected_body = dict(
                stallGraceMs=10,
                maxStallNudges=0,
                maxPingPongStreak=2,
                maxMemberTurns=3,
                observedAtMs=0,
            )
        assert _expect_source_body(captured[0]) == expected_body, case_id


def test_stall_check_rejects_zero_thresholds_and_corrupt_source_report() -> None:
    invalid_requests = {
        "zero_grace": dict(
            stallGraceMs=0,
            maxStallNudges=None,
            maxPingPongStreak=None,
            maxMemberTurns=None,
            observedAtMs=None,
        ),
        "zero_ping_pong": dict(
            stallGraceMs=None,
            maxStallNudges=None,
            maxPingPongStreak=0,
            maxMemberTurns=None,
            observedAtMs=None,
        ),
        "zero_member_turns": dict(
            stallGraceMs=None,
            maxStallNudges=None,
            maxPingPongStreak=None,
            maxMemberTurns=0,
            observedAtMs=None,
        ),
        "negative_observed_time": dict(
            stallGraceMs=None,
            maxStallNudges=None,
            maxPingPongStreak=None,
            maxMemberTurns=None,
            observedAtMs=-1,
        ),
    }
    for case_id, request_body in invalid_requests.items():
        captured: list[httpx.Request] = []
        client = GatewayTestClientBuilder().build_client()
        with client:
            response = client.post(f"{_BASE_PATH}/stall-check", json=request_body)
        assert response.status_code == 422, (case_id, response.text)
        assert not captured, case_id

    invalid_responses: dict[str, JsonObject] = {
        "empty_action": dict(action="", stoppedMembers=[]),
        "foreign_run": _stall_payload(run=_run_payload(swarm_run_id=_OTHER_MESSAGE_ID)),
        "numeric_boolean_count": dict(
            action="NOOP",
            workingMembers=True,
            stoppedMembers=[],
        ),
    }
    for case_id, payload in invalid_responses.items():
        captured = []
        client = _client(
            "POST",
            f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/stall-check",
            200,
            payload,
            captured,
        )
        with client:
            response = client.post(
                f"{_BASE_PATH}/stall-check",
                json=dict(
                    stallGraceMs=None,
                    maxStallNudges=None,
                    maxPingPongStreak=None,
                    maxMemberTurns=None,
                    observedAtMs=None,
                ),
            )
        assert response.status_code == 502, (case_id, response.text)


def test_board_routes_preserve_typed_domain_errors_and_document_transport_bounds() -> None:
    captured: list[httpx.Request] = []
    client = _client(
        "POST",
        f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/converge",
        409,
        {"code": "SWARM_CONFLICT", "message": "conflict", "retryable": False},
        captured,
    )
    with client:
        response = client.post(
            f"{_BASE_PATH}/converge",
            json=_converge_request(target_state=None),
        )
    assert response.status_code == 409
    assert response.json() == {
        "code": "SWARM_CONFLICT",
        "message": "conflict",
        "retryable": False,
    }

    captured = []
    client = _client(
        "GET",
        f"/v1/workspaces/{_WORKSPACE_ID}/swarms/{_RUN_ID}/messages",
        404,
        {"code": "NOT_FOUND", "message": "Board missing", "retryable": False},
        captured,
    )
    with client:
        missing_response = client.get(f"{_BASE_PATH}/messages")
    assert missing_response.status_code == 404
    assert missing_response.json() == {
        "code": "NOT_FOUND",
        "message": "Board missing",
        "retryable": False,
    }

    client = GatewayTestClientBuilder().build_client()
    with client:
        schema_response = client.get("/openapi.json")
    assert schema_response.status_code == 200
    paths = schema_response.json()["paths"]
    operations = {
        ("post", f"{_BASE_TEMPLATE}/messages"): {"200", "201"},
        ("get", f"{_BASE_TEMPLATE}/messages"): {"200"},
        ("post", f"{_BASE_TEMPLATE}/panels"): {"200", "201"},
        ("post", f"{_BASE_TEMPLATE}/verdicts"): {"200", "201"},
        ("post", f"{_BASE_TEMPLATE}/converge"): {"200"},
        ("post", f"{_BASE_TEMPLATE}/settle"): {"200"},
        ("post", f"{_BASE_TEMPLATE}/abort"): {"200"},
        ("post", f"{_BASE_TEMPLATE}/stall-check"): {"200"},
    }
    for (method, path), success_statuses in operations.items():
        response_codes = set(paths[path][method]["responses"])
        assert success_statuses <= response_codes, (method, path, response_codes)
        assert {"404", "409", "413", "502", "504"} <= response_codes, (
            method,
            path,
            response_codes,
        )
