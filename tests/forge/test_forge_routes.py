import httpx

from tests.shared.gateway_test_builder import GatewayTestClientBuilder, RouteResponseTable


def test_forge_crud_and_filter_routes() -> None:
    recorded_queries: list[dict[str, str]] = []
    recorded_patches: list[bytes] = []
    routes: RouteResponseTable = {
        ("GET", "/api/v1/forges"): (
            200,
            {
                "items": [
                    {
                        "id": "forge-1",
                        "name": "Alpha Forge",
                        "description": "Primary",
                        "created_at": "2026-09-28T09:30:00Z",
                    },
                ],
            },
        ),
        ("GET", "/api/v1/forges/forge-1"): (
            200,
            {
                "id": "forge-1",
                "name": "Alpha Forge",
                "description": None,
                "created_at": "2026-09-28T09:30:00Z",
            },
        ),
        ("POST", "/api/v1/forges"): (201, {"id": "forge-2", "name": "Beta"}),
        ("PUT", "/api/v1/forges/forge-1"): (200, {"id": "forge-1", "updated": True}),
        ("DELETE", "/api/v1/forges/forge-1"): (200, {"id": "forge-1", "deleted": True}),
    }

    def record_request(request: httpx.Request) -> None:
        if request.method == "GET" and request.url.path == "/api/v1/forges":
            recorded_queries.append(dict(request.url.params))
        elif request.method == "PUT" and request.url.path == "/api/v1/forges/forge-1":
            recorded_patches.append(request.content)

    client = (
        GatewayTestClientBuilder().with_route_table(routes, on_match=record_request).build_client()
    )
    with client:
        listed = client.get("/forges", params={"name": "Alpha", "created_after": "2026-09-01"})
        fetched = client.get("/forges/forge-1")
        created = client.post("/forges", json={"name": "Beta", "description": None})
        updated = client.put("/forges/forge-1", json={"name": "Alpha v2"})
        deleted = client.delete("/forges/forge-1")

    assert listed.status_code == 200
    assert recorded_queries == [{"created_after": "2026-09-01", "name": "Alpha"}]
    assert listed.json()[0]["id"] == "forge-1"
    assert fetched.status_code == 200
    assert fetched.json()["description"] is None
    assert created.status_code == 201
    assert created.json() == {"id": "forge-2", "name": "Beta"}
    assert updated.status_code == 200
    assert recorded_patches == [b'{"name":"Alpha v2"}']
    assert deleted.status_code == 200
    assert deleted.json() == {"id": "forge-1", "deleted": True}


def test_forge_upstream_failure_returns_forge_error_response() -> None:
    client = (
        GatewayTestClientBuilder()
        .with_handler(lambda _req: httpx.Response(503, json={"message": "unavailable"}))
        .build_client()
    )
    with client:
        response = client.get("/forges/forge-1")

    assert response.status_code == 502
    assert response.json() == {
        "code": "forge_http_503",
        "message": "Upstream forge returned HTTP 503",
        "retryable": True,
        "request_id": None,
    }
