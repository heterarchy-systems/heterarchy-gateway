"""Diagnostics bind the concrete contracts implemented by the Gateway."""

from guardrails._common import load_harness_config

from app.shared.types.base_types import JsonValue
from app.shared.types.json_contract import decode_json
from tests.shared.gateway_test_builder import GatewayTestClientBuilder


def test_diagnostics_catalog_matches_registered_operations_and_compositions() -> None:
    config = load_harness_config()
    expected: set[str] = set()
    for section in ("bff_operations", "bff_compositions"):
        declarations = config[section]
        assert isinstance(declarations, list)
        for declaration in declarations:
            assert isinstance(declaration, dict)
            identity = declaration["id"]
            assert isinstance(identity, str)
            expected.add(identity)

    with GatewayTestClientBuilder().build_client() as client:
        response = client.get("/diagnostics/contracts")
        assert response.status_code == 200
        payload = decode_json(response.content)
        assert isinstance(payload, dict)
        schemas = payload["schemas"]
        assert isinstance(schemas, dict)
        assert set(schemas) == expected
        forge = schemas["forge.location_list"]
        profiles = schemas["orchestration.profile_list"]
        assert isinstance(forge, dict) and isinstance(profiles, dict)
        required = forge["required"]
        assert isinstance(required, list)
        assert "request_id" in required
        assert profiles["type"] == "array"


def test_diagnostics_validate_concrete_envelopes_root_arrays_and_reject_fake_contracts() -> None:
    cases: dict[str, tuple[str, JsonValue, bool, str | None]] = {
        "forge_success": (
            "forge.location_list",
            {
                "forge_api": 1,
                "request_id": "11111111-1111-1111-1111-111111111111",
                "ok": True,
                "result": {"entries": []},
            },
            True,
            None,
        ),
        "forge_numeric_boolean": (
            "forge.location_list",
            {
                "forge_api": 1,
                "request_id": "11111111-1111-1111-1111-111111111111",
                "ok": 1,
                "result": {"entries": []},
            },
            False,
            "ok",
        ),
        "profile_array": ("orchestration.profile_list", [], True, None),
        "profile_wrong_root": ("orchestration.profile_list", {}, False, None),
    }
    with GatewayTestClientBuilder().build_client() as client:
        for contract, value, valid, invalid_field in cases.values():
            response = client.post(
                f"/diagnostics/contracts/{contract}/validate", json={"value": value}
            )
            assert response.status_code == 200
            payload = decode_json(response.content)
            assert isinstance(payload, dict)
            assert payload["valid"] is valid
            errors = payload["errors"]
            assert isinstance(errors, list)
            assert bool(errors) is not valid
            if invalid_field is not None:
                assert any(
                    isinstance(error, dict) and error["loc"] == [invalid_field] for error in errors
                )
        for retired in ("forge", "orchestration"):
            response = client.post(f"/diagnostics/contracts/{retired}/validate", json={"value": {}})
            assert response.status_code == 422
        assert client.get("/mixed/forge-1/tasks/task-1").status_code == 404
