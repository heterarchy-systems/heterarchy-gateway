import httpx
from fastapi.testclient import TestClient

from app.shared.types.base_types import JsonValue
from tests.shared.gateway_test_builder import GatewayTestClientBuilder


def _upstream_response(request: httpx.Request) -> httpx.Response:
    if "forge.example.test" in str(request.url):
        return httpx.Response(
            200,
            json={
                "id": "forge-1",
                "name": "Example Forge",
                "description": "Test upstream.",
                "created_at": "2026-09-28T09:30:00Z",
            },
        )
    return httpx.Response(
        200,
        json={"task_id": "task-1", "status": "completed", "result": {"ok": True}},
    )


def _client(*, failure_simulation_enabled: bool = False) -> TestClient:
    return (
        GatewayTestClientBuilder()
        .with_failure_simulation(enabled=failure_simulation_enabled)
        .with_handler(_upstream_response)
        .build_client()
    )


def test_mixed_compose_and_filter_mismatch_record_traces() -> None:
    with _client() as client:
        success_resp = client.get("/mixed/forge-1/tasks/task-1")
        success_trace = client.get(
            f"/diagnostics/traces/{success_resp.headers['X-Trace-ID']}",
        ).json()
        mismatch_resp = client.get(
            "/mixed/forge-1/tasks/task-1",
            params={"forge_name": "Missing"},
        )
        mismatch_trace = client.get(
            f"/diagnostics/traces/{mismatch_resp.headers['X-Trace-ID']}",
        ).json()

    assert success_resp.status_code == 200
    assert success_trace["raw"]["forge"]["created_at"] == "2026-09-28T09:30:00Z"
    assert success_trace["inner_dto"]["forge"]["created_at"] == "2026-09-28T09:30:00Z"
    assert success_trace["public_response"] == success_resp.json()
    assert {event["name"] for event in success_trace["events"]} == {
        "Client -> BFF",
        "BFF -> Client",
        "BFF -> forge",
        "BFF -> orchestration",
        "BFF compose",
    }
    assert mismatch_resp.status_code == 404
    assert mismatch_trace["bff_http_status"] == 404
    assert mismatch_trace["public_response"] is None


def test_contract_catalog_and_validation() -> None:
    validation_cases: dict[str, tuple[str, JsonValue, bool]] = {
        "valid_forge": (
            "forge",
            {
                "id": "forge-1",
                "name": "Example Forge",
                "description": None,
                "created_at": "2026-09-28T09:30:00Z",
            },
            True,
        ),
        "invalid_orchestration": (
            "orchestration",
            {"task_id": 8, "status": "not-a-status", "result": None},
            False,
        ),
    }

    with _client() as client:
        catalog = client.get("/diagnostics/contracts")
        assert catalog.status_code == 200
        schemas = catalog.json()["schemas"]
        assert "created_at" in schemas["forge"]["properties"]
        assert "status" in schemas["orchestration"]["properties"]

        for contract, payload, expected_valid in validation_cases.values():
            result = client.post(
                f"/diagnostics/contracts/{contract}/validate",
                json={"value": payload},
            ).json()
            assert result["valid"] is expected_valid
            if not expected_valid:
                assert ("task_id",) in {tuple(item["loc"]) for item in result["errors"]}


def test_failure_simulation_gate_and_recorded_scenarios() -> None:
    with _client(failure_simulation_enabled=False) as disabled_client:
        forbidden = disabled_client.get(
            "/mixed/forge-1/tasks/task-1",
            headers={"X-BFF-Failure": "forge_500"},
        )
    assert forbidden.status_code == 403

    scenario_expectations: dict[str, tuple[str, str | None, int | None]] = {
        "forge_500": ("BFF -> forge", None, 500),
        "forge_timeout": ("BFF -> forge", None, None),
        "orchestration_unavailable": ("BFF -> orchestration", None, None),
        "invalid_json": ("BFF -> forge", "{invalid json", None),
    }

    with _client(failure_simulation_enabled=True) as enabled_client:
        for scenario, (
            expected_event,
            expected_raw,
            expected_status,
        ) in scenario_expectations.items():
            response = enabled_client.get(
                "/mixed/forge-1/tasks/task-1",
                headers={"X-BFF-Failure": scenario},
            )
            trace = enabled_client.get(
                f"/diagnostics/traces/{response.headers['X-Trace-ID']}",
            ).json()
            assert response.status_code == 502
            assert trace["bff_http_status"] == 502
            failed_event = next(
                event for event in trace["events"] if event["name"] == expected_event
            )
            assert failed_event["status"] == "failed"
            if expected_raw is not None:
                assert failed_event["raw"] == expected_raw
            if expected_status is not None:
                assert failed_event["http_status"] == expected_status
