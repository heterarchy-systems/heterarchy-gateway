"""Unbound diagnostics factory; composition supplies supported contracts and storage."""

from collections.abc import Mapping
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from app.shared.base_schema import StrictSchemaModel
from app.shared.diagnostics.request_trace import (
    ContractIssue,
    ContractValidationResponse,
    TraceSnapshot,
    TraceStore,
)
from app.shared.ingredient_element.gateway.request_trace_enums import ContractName
from app.shared.types.base_types import JsonObject, JsonValue
from app.shared.types.json_contract import encode_json

_SCHEMA_ADAPTER = TypeAdapter(JsonObject)


class SchemaCatalogResponse(StrictSchemaModel):
    """Only contracts actually supplied by composition are advertised."""

    schemas: Annotated[JsonObject, Field(description="Registered JSON Schema contracts.")]


class ValidationPayload(StrictSchemaModel):
    """Untrusted JSON enclosed in an explicit diagnostics request contract."""

    value: Annotated[
        JsonValue, Field(description="Value to validate against the selected contract.")
    ]


def create_diagnostics_router(
    contracts: Mapping[ContractName, type[BaseModel]],
) -> APIRouter:
    """Create diagnostics from explicit contracts without importing private feature DTOs.

    Args:
        contracts: Supported public contracts supplied by composition.
    Return:
        Router to mount only behind the project's diagnostics access policy.
    """
    registry = dict(contracts)
    router = APIRouter(prefix="/diagnostics", tags=["diagnostics"], route_class=DishkaRoute)

    @router.get("/contracts", response_model=SchemaCatalogResponse)
    async def contracts_route() -> SchemaCatalogResponse:
        schemas: JsonObject = {
            name.value: _SCHEMA_ADAPTER.validate_python(model.model_json_schema())
            for name, model in registry.items()
        }
        return SchemaCatalogResponse(schemas=schemas)

    @router.post("/contracts/{contract}/validate", response_model=ContractValidationResponse)
    async def validate_contract_route(
        contract: ContractName, payload: ValidationPayload
    ) -> ContractValidationResponse:
        model = registry.get(contract)
        if model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Contract is not bound"
            )
        try:
            model.model_validate_json(encode_json(value=payload.value))
            result = ContractValidationResponse(contract=contract, valid=True, errors=[])
        except ValidationError as error:
            issues = [
                ContractIssue(
                    loc=[str(part) for part in item["loc"]],
                    message=item["msg"],
                    type=item["type"],
                )
                for item in error.errors()
            ]
            result = ContractValidationResponse(contract=contract, valid=False, errors=issues)
        return result

    @router.get("/traces/{trace_id}", response_model=TraceSnapshot)
    async def trace_route(
        trace_id: str,
        store: FromDishka[TraceStore],
    ) -> TraceSnapshot:
        snapshot = store.find(trace_id=trace_id)
        if snapshot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Trace not found or expired"
            )
        return snapshot

    return router
