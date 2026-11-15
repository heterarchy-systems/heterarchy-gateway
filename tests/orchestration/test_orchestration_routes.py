import httpx

from tests.shared.gateway_test_builder import GatewayTestClientBuilder, RouteResponseTable


def test_orchestration_lifecycle_routes() -> None:
    recorded_queries: list[dict[str, str]] = []
    routes: RouteResponseTable = {
        ("GET", "/api/v1/tasks"): (
            200,
            {
                "items": [
                    {"task_id": "task-1", "status": "completed", "result": {"ok": True}},
                    {"task_id": "task-2", "status": "queued", "result": None},
                ],
            },
        ),
        ("POST", "/api/v1/workflows/nightly/runs"): (
            200,
            {"task_id": "task-3", "status": "queued"},
        ),
        ("GET", "/api/v1/tasks/task-2"): (
            200,
            {"task_id": "task-2", "status": "queued", "result": None},
        ),
        ("DELETE", "/api/v1/tasks/task-2"): (
            200,
            {"task_id": "task-2", "status": "cancelled"},
        ),
    }

    def record_query(request: httpx.Request) -> None:
        if request.method == "GET" and request.url.path == "/api/v1/tasks":
            recorded_queries.append(dict(request.url.params))

    client = (
        GatewayTestClientBuilder().with_route_table(routes, on_match=record_query).build_client()
    )
    with client:
        listed = client.get("/orchestrations", params={"status": "running"})
        started = client.post(
            "/orchestrations",
            json={"workflow_name": "nightly", "inputs": {"branch": "main"}},
        )
        fetched = client.get("/orchestrations/task-2")
        cancelled = client.delete("/orchestrations/task-2")

    assert listed.status_code == 200
    assert recorded_queries == [{"status": "running"}]
    assert listed.json()[0]["result"] == {"ok": True}
    assert "result" not in listed.json()[1]
    assert started.status_code == 202
    assert started.json() == {"task_id": "task-3", "status": "queued"}
    assert fetched.status_code == 200
    assert fetched.json() == {"task_id": "task-2", "status": "queued"}
    assert cancelled.status_code == 200
    assert cancelled.json() == {"task_id": "task-2", "status": "cancelled"}


def test_orchestration_invalid_status_returns_orchestration_error() -> None:
    client = (
        GatewayTestClientBuilder()
        .with_handler(
            lambda _req: httpx.Response(
                200,
                json={"task_id": "task-1", "status": "bogus", "result": None},
            ),
        )
        .build_client()
    )
    with client:
        response = client.get("/orchestrations/task-1")

    assert response.status_code == 502
    assert response.json()["code"] == "orchestration_invalid_payload"
    assert response.json()["workspace_id"] is None
