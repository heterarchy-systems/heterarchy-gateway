"""Keep the declared HTTP surface aligned with the running application's OpenAPI."""

from guardrails._common import load_harness_config

from app.shared.types.base_types import JsonObject
from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder


def test_harness_routes_match_the_public_http_surface() -> None:
    config = load_harness_config()
    declarations = config["public_routes"]
    assert isinstance(declarations, list)
    expected: dict[tuple[str, str], str] = {}
    for declaration in declarations:
        assert isinstance(declaration, dict)
        method = declaration["method"]
        path = declaration["path"]
        identity = declaration["id"]
        assert isinstance(method, str)
        assert isinstance(path, str)
        assert isinstance(identity, str)
        key = (method, path)
        assert key not in expected
        assert identity not in expected.values()
        expected[key] = identity

    with GatewayTestClientBuilder().build_client() as client:
        response = client.get("/openapi.json")
    assert response.status_code == 200
    document = decode_json(response.content)
    assert isinstance(document, dict)
    paths = document["paths"]
    assert isinstance(paths, dict)
    actual: set[tuple[str, str]] = set()
    for path, operations in paths.items():
        assert isinstance(operations, dict)
        actual.update((method.upper(), path) for method in operations)
        for method, operation in operations.items():
            identity = expected[(method.upper(), path)]
            if identity.startswith("forge."):
                assert isinstance(operation, dict)
                responses = operation["responses"]
                assert isinstance(responses, dict)
                for status_code in ("502", "504"):
                    error_response = responses[status_code]
                    assert isinstance(error_response, dict)
                    content = error_response["content"]
                    assert isinstance(content, dict)
                    json_content = content["application/json"]
                    assert isinstance(json_content, dict)
                    schema = json_content["schema"]
                    assert isinstance(schema, dict)
                    assert schema["$ref"] == "#/components/schemas/ForgeErrorResponse"

    assert actual == set(expected)


def test_query_shape_rejections_match_the_documented_validation_response() -> None:
    cases: dict[str, str] = {
        "duplicate_optional_key": "limit=1&limit=2",
        "unknown_key": "limit=1&unknown=value",
    }
    with GatewayTestClientBuilder().build_client() as client:
        for query in cases.values():
            response = client.get(f"/orchestrations/profiles?{query}")
            assert response.status_code == 422
            body = decode_json(response.content)
            assert isinstance(body, dict)
            assert set(body) == {"detail"}
            details = body["detail"]
            assert isinstance(details, list) and details
            for detail in details:
                assert isinstance(detail, dict)
                assert {"loc", "msg", "type"}.issubset(detail)

        document = decode_json(client.get("/openapi.json").content)
    assert isinstance(document, dict)
    paths = document["paths"]
    assert isinstance(paths, dict)
    profile_path = paths["/orchestrations/profiles"]
    assert isinstance(profile_path, dict)
    operation = profile_path["get"]
    assert isinstance(operation, dict)
    responses = operation["responses"]
    assert isinstance(responses, dict)
    validation = responses["422"]
    assert isinstance(validation, dict)
    content = validation["content"]
    assert isinstance(content, dict)
    json_content = content["application/json"]
    assert isinstance(json_content, dict)
    schema = json_content["schema"]
    assert isinstance(schema, dict)
    assert schema["$ref"] == "#/components/schemas/HTTPValidationError"


def _response_schema(
    document: JsonObject,
    path: str,
    method: str,
    status_code: str,
) -> JsonObject:
    """Resolve one operation's JSON response schema from OpenAPI."""
    paths = document["paths"]
    assert isinstance(paths, dict)
    path_item = paths[path]
    assert isinstance(path_item, dict)
    operation = path_item[method]
    assert isinstance(operation, dict)
    responses = operation["responses"]
    assert isinstance(responses, dict)
    response = responses[status_code]
    assert isinstance(response, dict)
    content = response["content"]
    assert isinstance(content, dict)
    media = content["application/json"]
    assert isinstance(media, dict)
    schema = media["schema"]
    assert isinstance(schema, dict)
    return schema


def test_shared_error_response_definitions_match_openapi_status_models() -> None:
    declarations = load_harness_config()["public_routes"]
    assert isinstance(declarations, list)

    forge_models: dict[str, str] = {
        "202": "ForgeFailureEnvelope",
        "400": "ForgeFailureEnvelope",
        "409": "ForgeFailureEnvelope",
        "502": "ForgeErrorResponse",
        "503": "ForgeFailureEnvelope",
        "504": "ForgeErrorResponse",
    }
    orchestration_models: dict[str, str] = {
        "400": "OrchestrationBackendErrorResponse",
        "401": "OrchestrationBackendErrorResponse",
        "403": "OrchestrationBackendErrorResponse",
        "404": "OrchestrationBackendErrorResponse",
        "413": "OrchestrationErrorResponse",
        "429": "OrchestrationBackendErrorResponse",
        "500": "OrchestrationBackendErrorResponse",
        "502": "OrchestrationErrorResponse",
        "503": "OrchestrationBackendErrorResponse",
        "504": "OrchestrationErrorResponse",
    }

    with GatewayTestClientBuilder().build_client() as client:
        document = decode_json(client.get("/openapi.json").content)
    assert isinstance(document, dict)

    for declaration in declarations:
        assert isinstance(declaration, dict)
        identity = declaration["id"]
        path = declaration["path"]
        method = declaration["method"]
        assert isinstance(identity, str)
        assert isinstance(path, str)
        assert isinstance(method, str)
        if identity.startswith("forge."):
            expected = forge_models
        elif identity.startswith("orchestration."):
            expected = orchestration_models
        else:
            continue
        for status_code, model_name in expected.items():
            schema = _response_schema(document, path, method.lower(), status_code)
            assert schema["$ref"] == f"#/components/schemas/{model_name}", identity

    mixed_get = _response_schema(
        document,
        "/mixed/workspaces/{workspace_id}/swarms/{swarm_run_id}/overview",
        "get",
        "403",
    )
    assert {item["$ref"] for item in mixed_get["anyOf"]} == {
        "#/components/schemas/MixedDependencyFailureResponse",
        "#/components/schemas/MixedHttpDetailResponse",
    }
    assert {
        item["$ref"]
        for item in _response_schema(
            document,
            "/mixed/workspaces/{workspace_id}/swarms/{swarm_run_id}/overview",
            "get",
            "404",
        )["anyOf"]
    } == {
        "#/components/schemas/MixedDependencyFailureResponse",
        "#/components/schemas/MixedHttpDetailResponse",
    }

    mixed_post_path = "/mixed/workspaces/{workspace_id}/dags/governance-overview"
    mixed_post_404 = _response_schema(document, mixed_post_path, "post", "404")
    assert mixed_post_404["$ref"] == "#/components/schemas/MixedDependencyFailureResponse"
    mixed_422 = _response_schema(document, mixed_post_path, "post", "422")
    validation_schemas = mixed_422["anyOf"]
    assert isinstance(validation_schemas, list)
    validation_refs = {
        schema["$ref"]
        for schema in validation_schemas
        if isinstance(schema, dict) and "$ref" in schema
    }
    assert "#/components/schemas/MixedDependencyFailureResponse" in validation_refs
    fastapi_validation = next(
        schema
        for schema in validation_schemas
        if isinstance(schema, dict) and schema.get("title") == "HTTPValidationError"
    )
    detail = fastapi_validation["properties"]["detail"]
    assert isinstance(detail, dict)
    validation_issue = detail["items"]
    assert isinstance(validation_issue, dict)
    assert {"input", "ctx"}.issubset(validation_issue["properties"])
    mixed_default = _response_schema(document, mixed_post_path, "post", "default")
    assert mixed_default["$ref"] == "#/components/schemas/MixedDependencyFailureResponse"
