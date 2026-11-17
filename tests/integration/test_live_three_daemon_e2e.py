"""Exercise the real Source HTTP services through the local Gateway only."""

import asyncio
import time
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from pydantic import JsonValue

from app.shared.types.base_types import JsonObject
from app.shared.types.json_contract import decode_json
from tests.shared.live_three_daemon_builder import (
    LiveThreeDaemonBuilder,
    LiveThreeDaemonContext,
)


def _json_object(value: JsonValue, case_name: str) -> JsonObject:
    if not isinstance(value, dict):
        raise AssertionError(f"{case_name} did not return a JSON object")
    result: JsonObject = value
    return result


def _text_field(payload: JsonObject, field: str, case_name: str) -> str:
    value = payload[field]
    if not isinstance(value, str):
        raise AssertionError(f"{case_name}.{field} must be text")
    result = value
    return result


def _integer_field(payload: JsonObject, field: str, case_name: str) -> int:
    value = payload[field]
    if not isinstance(value, int) or isinstance(value, bool):
        raise AssertionError(f"{case_name}.{field} must be an integer")
    result = value
    return result


def _assert_worker_artifact(
    context: LiveThreeDaemonContext,
    worktree_path: str,
) -> None:
    """Verify the worker wrote inside its leased, scratch-owned Git worktree.

    Args:
        context: Test-owned Source directories.
        worktree_path: Path returned by the Orchestration dispatch receipt.
    Return:
        None when the isolated Source worktree contains the expected artifact.
    """
    isolated_worktree = Path(worktree_path).resolve()
    fixture_root = context.fixture_root.resolve()
    expected_worktree_root = context.worktree_root.resolve()
    assert isolated_worktree.is_relative_to(fixture_root), (
        f"Source committed worktree {isolated_worktree} escaped fixture root {fixture_root}"
    )
    assert isolated_worktree.is_relative_to(expected_worktree_root), (
        f"Source committed worktree {isolated_worktree} escaped expected temp root "
        f"{expected_worktree_root}"
    )
    assert not isolated_worktree.is_relative_to(context.workspace_root.resolve()), (
        f"Source committed worktree {isolated_worktree} is inside the original workspace"
    )
    assert not isolated_worktree.is_relative_to(Path("/Volumes/256.SSD/RustBuild")), (
        f"Source committed worktree {isolated_worktree} is inside the RustBuild directory"
    )
    assert (isolated_worktree / "e2e7_settled.txt").read_text() == "east-west worker output\n"
    assert not (context.workspace_root / "e2e7_settled.txt").exists()


def _read_settled_artifact(workspace_root: Path) -> str:
    """Read the Source file after cross-backend settlement applied its tree.

    Args:
        workspace_root: Forge Workspace registered by this test fixture.
    Return:
        Canonical file content produced by the local worker fixture.
    """
    result = (workspace_root / "e2e7_settled.txt").read_text()
    return result


def _json_response(response: httpx.Response, expected_status: int, case_name: str) -> JsonObject:
    assert response.status_code == expected_status, f"{case_name}: {response.text}"
    result = _json_object(decode_json(response.content), case_name)
    return result


def _profile_request(stable_name: str, display_name: str) -> JsonObject:
    result: JsonObject = {
        "requestId": str(uuid4()),
        "stableName": stable_name,
        "displayName": display_name,
        "preferredModel": "gpt-6-luna",
        "preferredReasoning": "medium",
        "baseCapabilities": ["verification", "rust"],
        "executionPreference": {
            "cliEngine": "codex",
            "preferredModel": "gpt-6-luna",
            "preferredReasoning": "medium",
            "capabilities": ["verification", "rust"],
            "rolePromptDigestHex": None,
        },
    }
    return result


def _member_request(
    profile_id: str,
    principal_id: str,
    role_kind: str,
    workspace_mode: str,
    roster_name: str,
    parent_member_id: str | None,
) -> JsonObject:
    result: JsonObject = {
        "memberId": str(uuid4()),
        "rosterName": roster_name,
        "roleKind": role_kind,
        "parentMemberId": parent_member_id,
        "workspaceMode": workspace_mode,
        "worktreePath": None,
        "identity": {
            "profileId": profile_id,
            "participantId": str(uuid4()),
            "principal": {"kind": "direct_token", "id": principal_id},
        },
        "initialChannels": [],
    }
    return result


async def _collect_realtime_events(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
    connected: asyncio.Event,
    new_event: asyncio.Event,
    observed_kinds: list[str],
    event_ids: list[str],
) -> None:
    path = f"/orchestrations/workspaces/{context.workspace_id}/events"
    async with client.stream(
        "GET",
        path,
        headers={"Authorization": context.orchestration_authorization},
    ) as response:
        assert response.status_code == 200, await response.aread()
        assert response.headers["content-type"].startswith("text/event-stream")
        connected.set()
        async for line in response.aiter_lines():
            if line.startswith("id:"):
                event_ids.append(line[3:].strip())
            elif line.startswith("data:"):
                payload = _json_object(decode_json(line[5:].strip().encode("utf-8")), "SSE data")
                kind = payload.get("kind")
                if isinstance(kind, str):
                    observed_kinds.append(kind)
                    new_event.set()


async def _create_profiles(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
) -> tuple[str, str]:
    headers = {"Authorization": context.orchestration_authorization}
    requests: dict[str, JsonObject] = {
        "worker": _profile_request(f"live-worker-{uuid4().hex}", "Gateway E2E Worker"),
        "verifier": _profile_request(f"live-verifier-{uuid4().hex}", "Gateway E2E Verifier"),
    }
    profiles: dict[str, str] = {}
    for role, payload in requests.items():
        response = await client.post("/orchestrations/profiles", headers=headers, json=payload)
        body = _json_response(response, 201, f"profile_{role}")
        profile = _json_object(body["profile"], f"profile_{role}.profile")
        profiles[role] = _text_field(profile, "profileId", f"profile_{role}")
    return profiles["worker"], profiles["verifier"]


async def _register_workspace_scope(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
) -> JsonObject:
    response = await client.post(
        "/orchestrations/workspaces/scopes",
        headers={"Authorization": context.orchestration_authorization},
        json={
            "requestId": str(uuid4()),
            "expectedRevision": 0,
            "scope": {
                "workspaceId": context.workspace_id,
                "locationId": context.location_id,
                "locationRevision": context.location_revision,
                "workspaceRevision": context.workspace_revision,
                "locator": context.locator,
            },
        },
    )
    body = _json_response(response, 200, "workspace_scope_register")
    assert body["workspaceId"] == context.workspace_id
    assert body["locator"] == context.locator
    return body


async def _create_swarm_run(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
) -> str:
    response = await client.post(
        f"/orchestrations/workspaces/{context.workspace_id}/swarms",
        headers={"Authorization": context.orchestration_authorization},
        json={
            "requestId": str(uuid4()),
            "title": f"Gateway East-West {uuid4()}",
            "mode": {"kind": "STANDALONE", "hybridTarget": None},
            "maxMembers": 8,
            "maxSpawnDepth": 3,
            "maxTotalTurns": 16,
            "requiredVerifierQuorum": 1,
            "allowWorkerAllMention": False,
            "baselineCommitOid": "0123456789abcdef0123456789abcdef01234567",
            "baselineTreeBlake3Hex": "b" * 64,
            "scope": {
                "workspaceId": context.workspace_id,
                "locationId": context.location_id,
                "locationRevision": context.location_revision,
                "workspaceRevision": context.workspace_revision,
                "locator": context.locator,
            },
        },
    )
    body = _json_response(response, 201, "swarm_create")
    run = _json_object(body["run"], "swarm_create.run")
    main_channel = _json_object(body["mainChannel"], "swarm_create.mainChannel")
    assert main_channel["swarmRunId"] == run["swarmRunId"]
    result = _text_field(run, "swarmRunId", "swarm_create.run")
    return result


async def _add_members(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
    run_id: str,
    worker_profile_id: str,
    verifier_profile_id: str,
) -> tuple[str, str, str]:
    base = f"/orchestrations/workspaces/{context.workspace_id}/swarms/{run_id}/members"
    headers = {"Authorization": context.orchestration_authorization}
    coordinator_request = _member_request(
        worker_profile_id,
        str(uuid4()),
        "coordinator",
        "inherit",
        "gateway-coordinator",
        None,
    )
    coordinator_response = await client.post(base, headers=headers, json=coordinator_request)
    coordinator_body = _json_response(coordinator_response, 201, "swarm_coordinator_add")
    coordinator_id = _text_field(coordinator_body, "memberId", "swarm_coordinator_add")

    worker_request = _member_request(
        worker_profile_id,
        str(uuid4()),
        "worker",
        "share",
        "gateway-worker",
        coordinator_id,
    )
    worker_response = await client.post(base, headers=headers, json=worker_request)
    worker_body = _json_response(worker_response, 201, "swarm_worker_add")
    worker_id = _text_field(worker_body, "memberId", "swarm_worker_add")

    verifier_request = _member_request(
        verifier_profile_id,
        str(uuid4()),
        "verifier",
        "inherit",
        "gateway-verifier",
        None,
    )
    verifier_response = await client.post(base, headers=headers, json=verifier_request)
    verifier_body = _json_response(verifier_response, 201, "swarm_verifier_add")
    verifier_id = _text_field(verifier_body, "memberId", "swarm_verifier_add")
    return coordinator_id, worker_id, verifier_id


async def _create_verification_panel(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
    run_id: str,
    worker_id: str,
    verifier_id: str,
) -> str:
    response = await client.post(
        f"/orchestrations/workspaces/{context.workspace_id}/swarms/{run_id}/panels",
        headers={"Authorization": context.orchestration_authorization},
        json={
            "requestId": str(uuid4()),
            "authorMemberIds": [worker_id],
            "verifierMemberIds": [verifier_id],
            "requiredQuorum": 1,
        },
    )
    body = _json_response(response, 201, "swarm_panel_create")
    result = _text_field(body, "panelId", "swarm_panel_create")
    return result


async def _dispatch_share_worker(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
    run_id: str,
    worker_id: str,
) -> str:
    now_ms = int(time.time() * 1000)
    response = await client.post(
        f"/orchestrations/workspaces/{context.workspace_id}/swarms/{run_id}"
        f"/members/{worker_id}/turns/dispatch",
        headers={"Authorization": context.orchestration_authorization},
        json={
            "snapshotRequestId": str(uuid4()),
            "snapshotId": str(uuid4()),
            "activityId": context.activity_id,
            "defaultWorktreePath": "",
            "leaseId": str(uuid4()),
            "leaseRevision": 1,
            "leaseExpiresAtMs": now_ms + 300_000,
            "mcpGrant": None,
            "permissions": {
                "allowWorkspaceWrite": True,
                "allowLocalShell": True,
                "allowNetwork": False,
            },
            "timeouts": {
                "startupTimeoutMs": 5_000,
                "executionTimeoutMs": 15_000,
                "terminationGraceMs": 2_000,
            },
            "dispatchedAtMs": now_ms,
            "cleanExitOutputCommitOid": None,
            "cleanExitOutputTreeBlake3Hex": None,
            "forgeSessionId": context.session_id,
        },
    )
    body = _json_response(response, 200, "swarm_turn_dispatch")
    disposition = _json_object(body["disposition"], "swarm_turn_dispatch.disposition")
    member = _json_object(disposition["member"], "swarm_turn_dispatch.disposition.member")
    snapshot = _json_object(body["committedSnapshot"], "swarm_turn_dispatch.committedSnapshot")
    assert disposition["kind"] == "COMPLETED"
    assert member["lastOutputCommitOid"] is not None
    assert member["lastOutputTreeBlake3Hex"] is not None
    worktree_path = _text_field(snapshot, "worktreePath", "swarm_turn_dispatch.committedSnapshot")
    return worktree_path


async def _forge_converge(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
    run_id: str,
) -> str:
    response = await client.post(
        f"/orchestrations/workspaces/{context.workspace_id}/swarms/{run_id}/forge-converge",
        headers={"Authorization": context.orchestration_authorization},
        json={
            "requestId": str(uuid4()),
            "sessionId": context.session_id,
            "candidateMemberIds": [],
            "stageCandidateOnly": True,
        },
    )
    body = _json_response(response, 200, "forge_converge")
    run = _json_object(body["run"], "forge_converge.run")
    assert run["state"] == "CANDIDATE_READY"
    changed_files = body["changedFiles"]
    assert isinstance(changed_files, list) and "e2e7_settled.txt" in changed_files
    result = _text_field(run, "convergedDiffDigestHex", "forge_converge.run")
    return result


async def _record_verifier_verdict(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
    run_id: str,
    panel_id: str,
    verifier_id: str,
    reviewed_diff_digest: str,
) -> None:
    response = await client.post(
        f"/orchestrations/workspaces/{context.workspace_id}/swarms/{run_id}/verdicts",
        headers={"Authorization": context.orchestration_authorization},
        json={
            "requestId": str(uuid4()),
            "panelId": panel_id,
            "verifierMemberId": verifier_id,
            "outcome": "ACCEPTED",
            "reviewedDiffDigestHex": reviewed_diff_digest,
            "rationale": "Verified the isolated worker output and merged diff.",
        },
    )
    body = _json_response(response, 201, "swarm_verdict_record")
    assert body["outcome"] == "ACCEPTED"


async def _forge_settle(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
    run_id: str,
) -> JsonObject:
    response = await client.post(
        f"/orchestrations/workspaces/{context.workspace_id}/swarms/{run_id}/forge-settle",
        headers={"Authorization": context.orchestration_authorization},
        json={
            "requestId": str(uuid4()),
            "sessionId": context.session_id,
            "activityId": context.activity_id,
            "coordinatorAgentId": context.coordinator_agent_id,
            "outboxMigrationId": context.outbox_migration_id,
            "outboxAfterSequence": 0,
            "purgeEphemeral": False,
        },
    )
    body = _json_response(response, 200, "forge_settle")
    run = _json_object(body["run"], "forge_settle.run")
    assert run["state"] == "SETTLED"
    assert body["purgedEphemeral"] is False
    sync = _json_object(body["outboxSync"], "forge_settle.outboxSync")
    assert sync["appliedCount"] == 1
    assert sync["swarmSettledCount"] == 1
    result = body
    return result


async def _sync_autonomy_outbox(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
) -> JsonObject:
    response = await client.post(
        f"/orchestrations/workspaces/{context.workspace_id}/autonomy-outbox/sync",
        headers={"Authorization": context.orchestration_authorization},
        json={
            "migrationId": context.outbox_migration_id,
            "afterSequence": 0,
            "limit": None,
        },
    )
    body = _json_response(response, 200, "autonomy_outbox_sync_replay")
    return body


async def _mixed_swarm_overview(
    client: httpx.AsyncClient,
    context: LiveThreeDaemonContext,
    run_id: str,
) -> JsonObject:
    response = await client.get(
        f"/mixed/workspaces/{context.workspace_id}/swarms/{run_id}/overview",
        params={
            "forge_request_id": str(uuid4()),
            "workspace_revision": str(context.workspace_revision),
            "location_id": context.location_id,
            "expected_revision": str(context.location_revision),
            "relative_root": context.relative_root,
            "run_state": "SETTLED",
            "settled_only": "true",
        },
        headers={
            "X-Forge-Authorization": context.forge_authorization,
            "X-Orchestration-Authorization": context.orchestration_authorization,
        },
    )
    if response.status_code != 200:
        trace_id = response.headers.get("X-Trace-ID")
        if trace_id is not None:
            trace_response = await client.get(f"/diagnostics/traces/{trace_id}")
            if trace_response.status_code == 200:
                trace = _json_object(decode_json(trace_response.content), "overview trace")
                raise AssertionError(
                    f"mixed overview filter rejected observed projections: {trace.get('inner_dto')}"
                )
    body = _json_response(response, 200, "mixed_swarm_overview")
    forge = _json_object(body["forge"], "mixed_swarm_overview.forge")
    result = _json_object(forge["result"], "mixed_swarm_overview.forge.result")
    receipt = _json_object(result["receipt"], "mixed_swarm_overview.forge.receipt")
    assert receipt["state"] == "applied"
    assert result["workspace_id"] == context.workspace_id
    assert result["swarm_run_id"] == run_id
    return body


@pytest.mark.asyncio
async def test_live_three_daemon_east_west_lifecycle_uses_gateway_http_only(
    tmp_path: Path,
) -> None:
    """Run a real Forge, Source Orchestration host, and Gateway lifecycle.

    Args:
        tmp_path: Isolated pytest scratch directory for Source state and logs.
    Return:
        None after Gateway settlement, kind-six synchronization, and SSE proof.
    """
    builder = LiveThreeDaemonBuilder(tmp_path / "gateway-live-three-daemon")
    event_task: asyncio.Task[None] | None = None
    new_event = asyncio.Event()
    try:
        context = await builder.start()
        async with httpx.AsyncClient(
            base_url=context.gateway_origin,
            timeout=httpx.Timeout(45.0, read=60.0),
        ) as client:
            connected = asyncio.Event()
            observed_kinds: list[str] = []
            event_ids: list[str] = []
            event_task = asyncio.create_task(
                _collect_realtime_events(
                    client,
                    context,
                    connected,
                    new_event,
                    observed_kinds,
                    event_ids,
                )
            )
            await asyncio.wait_for(connected.wait(), timeout=20)

            worker_profile_id, verifier_profile_id = await _create_profiles(client, context)
            scope = await _register_workspace_scope(client, context)
            assert scope["active"] is True
            run_id = await _create_swarm_run(client, context)
            _, worker_id, verifier_id = await _add_members(
                client,
                context,
                run_id,
                worker_profile_id,
                verifier_profile_id,
            )
            panel_id = await _create_verification_panel(
                client,
                context,
                run_id,
                worker_id,
                verifier_id,
            )

            message_response = await client.post(
                f"/orchestrations/workspaces/{context.workspace_id}/swarms/{run_id}/messages",
                headers={"Authorization": context.orchestration_authorization},
                json={
                    "messageId": str(uuid4()),
                    "channelId": None,
                    "authorMemberId": None,
                    "body": "@gateway-worker create e2e7_settled.txt",
                },
            )
            message_body = _json_response(message_response, 201, "swarm_message_post")
            assert worker_id in message_body["wokenMemberIds"]

            worktree_path = await _dispatch_share_worker(
                client,
                context,
                run_id,
                worker_id,
            )
            await asyncio.to_thread(_assert_worker_artifact, context, worktree_path)

            reviewed_diff_digest = await _forge_converge(client, context, run_id)
            await _record_verifier_verdict(
                client,
                context,
                run_id,
                panel_id,
                verifier_id,
                reviewed_diff_digest,
            )
            settlement = await _forge_settle(client, context, run_id)
            assert settlement["outboxSequence"] == 1
            repeated_sync = await _sync_autonomy_outbox(client, context)
            assert _integer_field(repeated_sync, "appliedCount", "autonomy_outbox_sync_replay") == 0
            assert (
                _integer_field(
                    repeated_sync,
                    "swarmSettledCount",
                    "autonomy_outbox_sync_replay",
                )
                == 0
            )
            assert (
                _integer_field(
                    repeated_sync,
                    "lastSequence",
                    "autonomy_outbox_sync_replay",
                )
                >= 1
            )
            settled_contents = await asyncio.to_thread(
                _read_settled_artifact,
                context.workspace_root,
            )
            assert settled_contents == "east-west worker output\n"
            overview = await _mixed_swarm_overview(client, context, run_id)
            assert overview["workspaceId"] == context.workspace_id
            assert overview["swarmRunId"] == run_id

            expected_kinds = [
                "workspace_scope_changed",
                "swarm_run_changed",
                "swarm_member_state_changed",
                "swarm_board_message_posted",
                "swarm_verdict_recorded",
                "settlement_projected",
            ]
            deadline = asyncio.get_running_loop().time() + 35
            while not all(kind in observed_kinds for kind in expected_kinds):
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise AssertionError(f"Timed out waiting for realtime kinds: {observed_kinds}")
                await asyncio.wait_for(new_event.wait(), remaining)
                new_event.clear()
            assert all(kind in observed_kinds for kind in expected_kinds)
            assert event_ids
            assert all(":" in event_id for event_id in event_ids)
    finally:
        await builder.stop_after_reader(event_task)
