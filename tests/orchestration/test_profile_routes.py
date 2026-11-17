"""Builder-based regression coverage for the Agent Profile HTTP contracts."""

import httpx
from fastapi.testclient import TestClient
from pydantic import JsonValue

from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder, RouteResponseTable

_PROFILE_ID = "00000000-0000-0000-0000-000000000001"
_CREATE_REQUEST_ID = "00000000-0000-0000-0000-000000000002"
_MUTATION_REQUEST_ID = "00000000-0000-0000-0000-000000000003"


def profile_payload(
    *,
    profile_id: str = _PROFILE_ID,
    profile_request_id: str = _CREATE_REQUEST_ID,
    provider_family: str = "unbound",
    lifecycle_state: str = "active",
    creation_origin: str = "user_manual",
    revision: int = 1,
    stable_name: str = "profile-create-replay",
    display_name: str = "Profile create replay",
    preferred_model: str | None = None,
    preferred_reasoning: str | None = None,
    base_capabilities: tuple[str, ...] = ("verification",),
    created_at_ms: int = 10,
    updated_at_ms: int | None = None,
    last_used_at_ms: int | None = None,
    execution_preference: JsonValue | None = None,
    include_execution_preference: bool = False,
) -> JsonValue:
    """Build the exact Orchestration Profile fixture shape.

    Args:
        provider_family: Source provider family label.
        lifecycle_state: Source durable lifecycle label.
        creation_origin: Source Profile audit origin.
        revision: Source Profile revision.
        stable_name: Source stable Profile name.
        display_name: Source Profile display name.
        preferred_model: Source preferred model or null.
        preferred_reasoning: Source preferred reasoning or null.
        base_capabilities: Source Profile capabilities.
        created_at_ms: Source creation time.
        updated_at_ms: Source update time or creation time when omitted.
        last_used_at_ms: Source last-use time or null.
        execution_preference: Optional source execution preference.
        include_execution_preference: Whether to include the skip-serialized field.
    Return:
        Source Profile response fixture.
    """
    update_time = created_at_ms if updated_at_ms is None else updated_at_ms
    profile: dict[str, JsonValue] = {
        "profileId": profile_id,
        "requestId": profile_request_id,
        "stableName": stable_name,
        "displayName": display_name,
        "providerFamily": provider_family,
        "preferredModel": preferred_model,
        "preferredReasoning": preferred_reasoning,
        "baseCapabilities": list(base_capabilities),
        "lifecycleState": lifecycle_state,
        "creationOrigin": creation_origin,
        "createdAtMs": created_at_ms,
        "updatedAtMs": update_time,
        "lastUsedAtMs": last_used_at_ms,
        "revision": revision,
    }
    if include_execution_preference:
        profile["executionPreference"] = execution_preference
    result: JsonValue = profile
    return result


def create_outcome_payload(
    *,
    created: bool,
    provider_family: str,
    profile_request_id: str = _CREATE_REQUEST_ID,
    execution_preference: JsonValue | None = None,
) -> JsonValue:
    """Build a source create or exact replay response fixture.

    Args:
        created: Whether the source created a new Profile.
        provider_family: Source Profile provider family.
        execution_preference: Optional reusable CLI execution preference.
    Return:
        Source create outcome wrapper.
    """
    result: JsonValue = {
        "profile": profile_payload(
            provider_family=provider_family,
            profile_request_id=profile_request_id,
            execution_preference=execution_preference,
            include_execution_preference=execution_preference is not None,
        ),
        "created": created,
    }
    return result


def mutation_payload(
    *,
    request_id: str = _MUTATION_REQUEST_ID,
    profile_id: str = _PROFILE_ID,
    expected_revision: int = 1,
    kind: str = "update",
    profile_revision: int | None = None,
    lifecycle_state: str = "active",
    display_name: str = "Profile create replay",
    preferred_model: str | None = None,
    preferred_reasoning: str | None = None,
    base_capabilities: tuple[str, ...] = ("verification",),
    execution_preference: JsonValue | None = None,
    include_execution_preference: bool = False,
) -> JsonValue:
    """Build one source mutation receipt fixture.

    Args:
        request_id: Source mutation identity.
        profile_id: Source Profile identity.
        expected_revision: Echoed request revision.
        kind: Source mutation kind.
        profile_revision: Source result revision; defaults to next revision.
        lifecycle_state: Source Profile lifecycle state.
        display_name: Source Profile display name.
        preferred_model: Source preferred model or null.
        preferred_reasoning: Source preferred reasoning or null.
        base_capabilities: Source Profile capabilities.
        execution_preference: Optional source execution preference.
        include_execution_preference: Whether to include the skip-serialized field.
    Return:
        Source Profile mutation response.
    """
    result: JsonValue = {
        "requestId": request_id,
        "expectedRevision": expected_revision,
        "kind": kind,
        "profile": profile_payload(
            profile_id=profile_id,
            revision=expected_revision + 1 if profile_revision is None else profile_revision,
            lifecycle_state=lifecycle_state,
            display_name=display_name,
            preferred_model=preferred_model,
            preferred_reasoning=preferred_reasoning,
            base_capabilities=base_capabilities,
            execution_preference=execution_preference,
            include_execution_preference=include_execution_preference,
        ),
        "replayed": False,
    }
    return result


def make_client(
    method: str,
    path: str,
    status_code: int,
    payload: JsonValue,
    captured: list[httpx.Request],
) -> TestClient:
    """Build one isolated source fixture client.

    Args:
        method: One source HTTP method.
        path: One source path.
        status_code: One source response status.
        payload: One source response body.
        captured: Requests recorded for this isolated fixture.
    Return:
        Gateway TestClient using the single source fixture.
    """
    routes: RouteResponseTable = {(method, path): (status_code, payload)}
    client = (
        GatewayTestClientBuilder().with_route_table(routes, on_match=captured.append).build_client()
    )
    return client


def create_request_payload(execution_preference: JsonValue | None = None) -> JsonValue:
    """Build the required public create body, including nullable fields.

    Args:
        execution_preference: Optional reusable CLI preference.
    Return:
        Public create request body.
    """
    result: JsonValue = {
        "requestId": _CREATE_REQUEST_ID,
        "stableName": "profile-create-replay",
        "displayName": "Profile create replay",
        "preferredModel": None,
        "preferredReasoning": None,
        "baseCapabilities": ["verification"],
        "executionPreference": execution_preference,
    }
    return result


def profile_update_request_payload(
    *,
    display_name: str,
    preferred_model: str | None,
    preferred_reasoning: str | None,
    base_capabilities: tuple[str, ...],
    execution_preference: JsonValue | None,
) -> JsonValue:
    """Build a required-field-complete Profile configuration request.

    Args:
        display_name: Requested display name.
        preferred_model: Requested model or null.
        preferred_reasoning: Requested reasoning or null.
        base_capabilities: Requested reusable capability labels.
        execution_preference: Requested execution preference or null.
    Return:
        Public Profile configuration request body.
    """
    result: JsonValue = {
        "requestId": _MUTATION_REQUEST_ID,
        "expectedRevision": 1,
        "displayName": display_name,
        "preferredModel": preferred_model,
        "preferredReasoning": preferred_reasoning,
        "baseCapabilities": list(base_capabilities),
        "executionPreference": execution_preference,
    }
    return result


def execution_preference_payload(
    *,
    preferred_model: str = "gpt-5.6-luna",
    capabilities: tuple[str, ...] = ("backend",),
    preferred_reasoning: str | None = None,
    role_prompt_digest_hex: str | None = None,
) -> JsonValue:
    """Build a valid nullable-field-complete source preference fixture.

    Args:
        preferred_model: Source preference model.
        capabilities: Source preference capability labels.
        preferred_reasoning: Source reasoning value or null.
        role_prompt_digest_hex: Source digest value or null.
    Return:
        Source execution preference with explicit nullable fields.
    """
    result: JsonValue = {
        "cliEngine": "codex",
        "preferredModel": preferred_model,
        "preferredReasoning": preferred_reasoning,
        "capabilities": list(capabilities),
        "rolePromptDigestHex": role_prompt_digest_hex,
    }
    return result


def test_profile_create_preserves_new_and_exact_replay_statuses() -> None:
    cases: dict[str, tuple[int, bool, str, JsonValue | None]] = {
        "new_profile_with_preference": (
            201,
            True,
            "unbound",
            execution_preference_payload(),
        ),
        "exact_replay": (200, False, "chatgpt", None),
    }
    for case_id, (expected_status, created, provider_family, preference) in cases.items():
        captured: list[httpx.Request] = []
        payload = create_outcome_payload(
            created=created,
            provider_family=provider_family,
            execution_preference=preference,
        )
        client = make_client(
            "POST",
            "/internal/v1/agent-profiles",
            expected_status,
            payload,
            captured,
        )
        with client:
            response = client.post(
                "/orchestrations/profiles",
                json=create_request_payload(preference),
            )

        assert response.status_code == expected_status, (case_id, response.text)
        assert response.json()["created"] is created, case_id
        assert response.json()["profile"]["providerFamily"] == provider_family, case_id
        assert "executionPreference" in response.json()["profile"], case_id
        assert response.json()["profile"]["executionPreference"] == preference, case_id
        assert len(captured) == 1, case_id
        assert captured[0].url.path == "/internal/v1/agent-profiles", case_id
        assert decode_json(captured[0].content) == create_request_payload(preference), case_id


def test_profile_list_returns_a_root_array_and_forwards_limit() -> None:
    captured: list[httpx.Request] = []
    profiles: JsonValue = [
        profile_payload(include_execution_preference=False),
        profile_payload(
            profile_id="00000000-0000-0000-0000-000000000004",
            profile_request_id="00000000-0000-0000-0000-000000000005",
            stable_name="other-profile",
            display_name="Other profile",
            include_execution_preference=False,
        ),
    ]
    client = make_client(
        "GET",
        "/internal/v1/agent-profiles",
        200,
        profiles,
        captured,
    )
    with client:
        response = client.get("/orchestrations/profiles?limit=8")
        default_response = client.get("/orchestrations/profiles")

    assert response.status_code == 200
    assert default_response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 2
    assert response.json()[0]["profileId"] == _PROFILE_ID
    assert response.json()[0]["executionPreference"] is None
    assert len(captured) == 2
    assert captured[0].url.path == "/internal/v1/agent-profiles"
    assert captured[0].url.query == b"limit=8"
    assert captured[1].url.path == "/internal/v1/agent-profiles"
    assert captured[1].url.query == b""


def test_profile_list_rejects_out_of_bounds_and_unknown_query_keys() -> None:
    queries = {"out_of_bounds": "limit=65", "unknown": "other=1"}
    for query in queries.values():
        client = GatewayTestClientBuilder().build_client()
        with client:
            response = client.get(f"/orchestrations/profiles?{query}")
        assert response.status_code == 422, query


def test_profile_list_rejects_duplicate_source_identities() -> None:
    cases: dict[str, JsonValue] = {
        "duplicate_profile_id": [
            profile_payload(profile_request_id=_CREATE_REQUEST_ID),
            profile_payload(profile_request_id="00000000-0000-0000-0000-000000000006"),
        ],
        "duplicate_request_id": [
            profile_payload(profile_id=_PROFILE_ID),
            profile_payload(profile_id="00000000-0000-0000-0000-000000000006"),
        ],
    }
    for case_id, payload in cases.items():
        captured: list[httpx.Request] = []
        client = make_client("GET", "/internal/v1/agent-profiles", 200, payload, captured)
        with client:
            response = client.get("/orchestrations/profiles")

        assert response.status_code == 502, case_id
        assert response.json()["code"] == "orchestration_invalid_payload", case_id


def test_profile_list_accepts_distinct_source_identities() -> None:
    captured: list[httpx.Request] = []
    payload: JsonValue = [
        profile_payload(),
        profile_payload(
            profile_id="00000000-0000-0000-0000-000000000006",
            profile_request_id="00000000-0000-0000-0000-000000000007",
            stable_name="another-profile",
            display_name="Another Profile",
        ),
    ]
    client = make_client("GET", "/internal/v1/agent-profiles", 200, payload, captured)
    with client:
        response = client.get("/orchestrations/profiles")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_profile_list_rejects_response_above_requested_limit() -> None:
    captured: list[httpx.Request] = []
    payload: JsonValue = [
        profile_payload(),
        profile_payload(
            profile_id="00000000-0000-0000-0000-000000000006",
            profile_request_id="00000000-0000-0000-0000-000000000007",
        ),
    ]
    client = make_client("GET", "/internal/v1/agent-profiles", 200, payload, captured)
    with client:
        response = client.get("/orchestrations/profiles?limit=1")

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_invalid_payload"


def test_profile_rejects_source_invalid_snapshot_projections() -> None:
    cases: dict[str, JsonValue] = {
        "nil_profile_id": profile_payload(profile_id="00000000-0000-0000-0000-000000000000"),
        "nil_request_id": profile_payload(
            profile_request_id="00000000-0000-0000-0000-000000000000",
        ),
        "zero_revision": profile_payload(revision=0),
        "updated_before_created": profile_payload(created_at_ms=10, updated_at_ms=9),
        "negative_last_used": profile_payload(last_used_at_ms=-1),
        "duplicate_preference_capabilities": profile_payload(
            execution_preference=execution_preference_payload(capabilities=("read", "read")),
            include_execution_preference=True,
        ),
        "zero_role_prompt_digest": profile_payload(
            execution_preference=execution_preference_payload(
                role_prompt_digest_hex="0" * 64,
            ),
            include_execution_preference=True,
        ),
        "empty_preference_model": profile_payload(
            execution_preference=execution_preference_payload(preferred_model=""),
            include_execution_preference=True,
        ),
        "oversized_preference_reasoning": profile_payload(
            execution_preference=execution_preference_payload(preferred_reasoning="r" * 129),
            include_execution_preference=True,
        ),
        "too_many_preference_capabilities": profile_payload(
            execution_preference=execution_preference_payload(
                capabilities=tuple(f"capability-{index}" for index in range(33)),
            ),
            include_execution_preference=True,
        ),
        "oversized_preference_capability": profile_payload(
            execution_preference=execution_preference_payload(capabilities=("c" * 65,)),
            include_execution_preference=True,
        ),
        "uppercase_role_prompt_digest": profile_payload(
            execution_preference=execution_preference_payload(
                role_prompt_digest_hex="AB" * 32,
            ),
            include_execution_preference=True,
        ),
        "invalid_provider_family": profile_payload(provider_family="unknown"),
        "invalid_lifecycle_state": profile_payload(lifecycle_state="online"),
        "invalid_creation_origin": profile_payload(
            creation_origin="unexpected",
        ),
    }
    for case_id, payload in cases.items():
        captured: list[httpx.Request] = []
        client = make_client(
            "GET",
            f"/internal/v1/agent-profiles/{_PROFILE_ID}",
            200,
            payload,
            captured,
        )
        with client:
            response = client.get(f"/orchestrations/profiles/{_PROFILE_ID}")

        assert response.status_code == 502, case_id
        assert response.json()["code"] == "orchestration_invalid_payload", case_id


def test_profile_get_returns_the_direct_profile_body() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        "GET",
        f"/internal/v1/agent-profiles/{_PROFILE_ID}",
        200,
        profile_payload(include_execution_preference=False),
        captured,
    )
    with client:
        response = client.get(f"/orchestrations/profiles/{_PROFILE_ID}")

    assert response.status_code == 200
    assert response.json()["profileId"] == _PROFILE_ID
    assert "profile" not in response.json()
    assert response.json()["executionPreference"] is None
    assert len(captured) == 1
    assert captured[0].url.path == f"/internal/v1/agent-profiles/{_PROFILE_ID}"


def test_profile_update_disable_and_retire_forward_source_contracts() -> None:
    cases: dict[str, tuple[str, str, str, JsonValue, str, int]] = {
        "update": (
            "PUT",
            f"/internal/v1/agent-profiles/{_PROFILE_ID}/configuration",
            "/configuration",
            {
                "requestId": _MUTATION_REQUEST_ID,
                "expectedRevision": 1,
                "displayName": "Profile create replay",
                "preferredModel": None,
                "preferredReasoning": None,
                "baseCapabilities": ["verification"],
                "executionPreference": None,
            },
            "active",
            2,
        ),
        "disable": (
            "POST",
            f"/internal/v1/agent-profiles/{_PROFILE_ID}/disable",
            "/disable",
            {"requestId": _MUTATION_REQUEST_ID, "expectedRevision": 1},
            "disabled",
            2,
        ),
        "retire": (
            "POST",
            f"/internal/v1/agent-profiles/{_PROFILE_ID}/retire",
            "/retire",
            {"requestId": _MUTATION_REQUEST_ID, "expectedRevision": 1},
            "retired",
            2,
        ),
        "disable_noop": (
            "POST",
            f"/internal/v1/agent-profiles/{_PROFILE_ID}/disable",
            "/disable",
            {"requestId": _MUTATION_REQUEST_ID, "expectedRevision": 1},
            "disabled",
            1,
        ),
    }
    for kind, (
        method,
        source_path,
        gateway_suffix,
        request_body,
        lifecycle_state,
        profile_revision,
    ) in cases.items():
        captured: list[httpx.Request] = []
        source_kind = "disable" if kind == "disable_noop" else kind
        payload = mutation_payload(
            expected_revision=1,
            kind=source_kind,
            profile_revision=profile_revision,
            lifecycle_state=lifecycle_state,
        )
        client = make_client(method, source_path, 200, payload, captured)
        with client:
            if kind == "update":
                response = client.put(
                    f"/orchestrations/profiles/{_PROFILE_ID}/configuration",
                    json=request_body,
                )
            else:
                response = client.post(
                    f"/orchestrations/profiles/{_PROFILE_ID}{gateway_suffix}",
                    json=request_body,
                )

        assert response.status_code == 200, (kind, response.text)
        assert response.json()["kind"] == source_kind, kind
        assert response.json()["requestId"] == _MUTATION_REQUEST_ID, kind
        assert response.json()["profile"]["profileId"] == _PROFILE_ID, kind
        assert len(captured) == 1, kind
        assert captured[0].url.path == source_path, kind
        assert decode_json(captured[0].content) == request_body, kind


def test_profile_update_accepts_source_sorted_configuration_and_preference() -> None:
    request_preference = execution_preference_payload(
        preferred_model="model-a",
        capabilities=("write", "read"),
        preferred_reasoning="high",
        role_prompt_digest_hex="12" * 32,
    )
    request_body = profile_update_request_payload(
        display_name="Updated Profile",
        preferred_model="model-main",
        preferred_reasoning="max",
        base_capabilities=("zeta", "alpha"),
        execution_preference=request_preference,
    )
    response_preference = execution_preference_payload(
        preferred_model="model-a",
        capabilities=("read", "write"),
        preferred_reasoning="high",
        role_prompt_digest_hex="12" * 32,
    )
    payload = mutation_payload(
        kind="update",
        profile_revision=2,
        display_name="Updated Profile",
        preferred_model="model-main",
        preferred_reasoning="max",
        base_capabilities=("alpha", "zeta"),
        execution_preference=response_preference,
        include_execution_preference=True,
    )
    captured: list[httpx.Request] = []
    client = make_client(
        "PUT",
        f"/internal/v1/agent-profiles/{_PROFILE_ID}/configuration",
        200,
        payload,
        captured,
    )
    with client:
        response = client.put(
            f"/orchestrations/profiles/{_PROFILE_ID}/configuration",
            json=request_body,
        )

    assert response.status_code == 200
    assert response.json()["profile"]["baseCapabilities"] == ["alpha", "zeta"]
    assert response.json()["profile"]["executionPreference"]["capabilities"] == [
        "read",
        "write",
    ]
    assert decode_json(captured[0].content) == request_body


def test_profile_update_rejects_source_response_configuration_mismatches() -> None:
    request_preference = execution_preference_payload(
        preferred_model="model-a",
        capabilities=("write", "read"),
        preferred_reasoning="high",
        role_prompt_digest_hex="12" * 32,
    )
    request_body = profile_update_request_payload(
        display_name="Updated Profile",
        preferred_model="model-main",
        preferred_reasoning="max",
        base_capabilities=("zeta", "alpha"),
        execution_preference=request_preference,
    )
    good_preference = execution_preference_payload(
        preferred_model="model-a",
        capabilities=("read", "write"),
        preferred_reasoning="high",
        role_prompt_digest_hex="12" * 32,
    )
    cases: dict[str, JsonValue] = {
        "stale_revision": mutation_payload(
            kind="update",
            profile_revision=1,
            display_name="Updated Profile",
            preferred_model="model-main",
            preferred_reasoning="max",
            base_capabilities=("alpha", "zeta"),
            execution_preference=good_preference,
            include_execution_preference=True,
        ),
        "wrong_display_name": mutation_payload(
            kind="update",
            profile_revision=2,
            display_name="Old display",
            preferred_model="model-main",
            preferred_reasoning="max",
            base_capabilities=("alpha", "zeta"),
            execution_preference=good_preference,
            include_execution_preference=True,
        ),
        "wrong_preferred_model": mutation_payload(
            kind="update",
            profile_revision=2,
            display_name="Updated Profile",
            preferred_model="old-model",
            preferred_reasoning="max",
            base_capabilities=("alpha", "zeta"),
            execution_preference=good_preference,
            include_execution_preference=True,
        ),
        "unsorted_base_capabilities": mutation_payload(
            kind="update",
            profile_revision=2,
            display_name="Updated Profile",
            preferred_model="model-main",
            preferred_reasoning="max",
            base_capabilities=("zeta", "alpha"),
            execution_preference=good_preference,
            include_execution_preference=True,
        ),
        "wrong_preference": mutation_payload(
            kind="update",
            profile_revision=2,
            display_name="Updated Profile",
            preferred_model="model-main",
            preferred_reasoning="max",
            base_capabilities=("alpha", "zeta"),
            execution_preference=execution_preference_payload(
                preferred_model="old-model",
                capabilities=("read", "write"),
                preferred_reasoning="high",
                role_prompt_digest_hex="12" * 32,
            ),
            include_execution_preference=True,
        ),
        "unsorted_preference_capabilities": mutation_payload(
            kind="update",
            profile_revision=2,
            display_name="Updated Profile",
            preferred_model="model-main",
            preferred_reasoning="max",
            base_capabilities=("alpha", "zeta"),
            execution_preference=request_preference,
            include_execution_preference=True,
        ),
    }
    for case_id, payload in cases.items():
        captured: list[httpx.Request] = []
        client = make_client(
            "PUT",
            f"/internal/v1/agent-profiles/{_PROFILE_ID}/configuration",
            200,
            payload,
            captured,
        )
        with client:
            response = client.put(
                f"/orchestrations/profiles/{_PROFILE_ID}/configuration",
                json=request_body,
            )

        assert response.status_code == 502, case_id
        assert response.json()["code"] == "orchestration_invalid_payload", case_id


def test_profile_lifecycle_rejects_wrong_target_state_and_revision() -> None:
    cases: dict[str, JsonValue] = {
        "disable_wrong_state": mutation_payload(
            kind="disable",
            profile_revision=1,
            lifecycle_state="active",
        ),
        "retire_wrong_revision": mutation_payload(
            kind="retire",
            profile_revision=3,
            lifecycle_state="retired",
        ),
    }
    for case_id, payload in cases.items():
        kind = "disable" if case_id == "disable_wrong_state" else "retire"
        captured: list[httpx.Request] = []
        client = make_client(
            "POST",
            f"/internal/v1/agent-profiles/{_PROFILE_ID}/{kind}",
            200,
            payload,
            captured,
        )
        with client:
            response = client.post(
                f"/orchestrations/profiles/{_PROFILE_ID}/{kind}",
                json={"requestId": _MUTATION_REQUEST_ID, "expectedRevision": 1},
            )

        assert response.status_code == 502, case_id
        assert response.json()["code"] == "orchestration_invalid_payload", case_id


def test_profile_rejects_missing_required_nullable_fields() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        "POST",
        "/internal/v1/agent-profiles",
        201,
        create_outcome_payload(
            created=True,
            provider_family="unbound",
            execution_preference={
                "cliEngine": "codex",
                "preferredModel": "gpt-5.6-luna",
                "capabilities": ["backend"],
            },
        ),
        captured,
    )
    with client:
        response = client.post(
            "/orchestrations/profiles",
            json=create_request_payload(execution_preference_payload()),
        )

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_invalid_payload"


def test_profile_create_requires_all_nullable_request_keys() -> None:
    client = GatewayTestClientBuilder().build_client()
    with client:
        response = client.post(
            "/orchestrations/profiles",
            json={
                "requestId": _CREATE_REQUEST_ID,
                "stableName": "profile-create-replay",
                "displayName": "Profile create replay",
                "baseCapabilities": ["verification"],
            },
        )

    assert response.status_code == 422


def test_profile_create_checks_source_request_echo_and_provider_contract() -> None:
    cases: dict[str, JsonValue] = {
        "wrong_request_echo": create_outcome_payload(
            created=True,
            provider_family="unbound",
            profile_request_id="00000000-0000-0000-0000-000000000099",
        ),
        "new_profile_bound_to_provider": create_outcome_payload(
            created=True,
            provider_family="chatgpt",
        ),
    }
    for case_id, payload in cases.items():
        captured: list[httpx.Request] = []
        client = make_client(
            "POST",
            "/internal/v1/agent-profiles",
            201,
            payload,
            captured,
        )
        with client:
            response = client.post(
                "/orchestrations/profiles",
                json=create_request_payload(),
            )

        assert response.status_code == 502, case_id
        assert response.json()["code"] == "orchestration_invalid_payload", case_id


def test_profile_get_checks_source_path_identity_echo() -> None:
    captured: list[httpx.Request] = []
    client = make_client(
        "GET",
        f"/internal/v1/agent-profiles/{_PROFILE_ID}",
        200,
        profile_payload(profile_id="00000000-0000-0000-0000-000000000099"),
        captured,
    )
    with client:
        response = client.get(f"/orchestrations/profiles/{_PROFILE_ID}")

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_invalid_payload"


def test_profile_mutation_checks_all_source_identity_echoes() -> None:
    cases: dict[str, JsonValue] = {
        "wrong_request_id": mutation_payload(
            request_id="00000000-0000-0000-0000-000000000099",
        ),
        "wrong_profile_id": mutation_payload(
            profile_id="00000000-0000-0000-0000-000000000099",
        ),
        "wrong_expected_revision": mutation_payload(expected_revision=2),
        "wrong_kind": mutation_payload(kind="disable"),
    }
    for case_id, payload in cases.items():
        captured: list[httpx.Request] = []
        client = make_client(
            "PUT",
            f"/internal/v1/agent-profiles/{_PROFILE_ID}/configuration",
            200,
            payload,
            captured,
        )
        with client:
            response = client.put(
                f"/orchestrations/profiles/{_PROFILE_ID}/configuration",
                json={
                    "requestId": _MUTATION_REQUEST_ID,
                    "expectedRevision": 1,
                    "displayName": "Profile create replay",
                    "preferredModel": None,
                    "preferredReasoning": None,
                    "baseCapabilities": ["verification"],
                    "executionPreference": None,
                },
            )

        assert response.status_code == 502, case_id
        assert response.json()["code"] == "orchestration_invalid_payload", case_id
