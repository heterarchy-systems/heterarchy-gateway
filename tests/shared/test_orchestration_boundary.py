"""Regression coverage for typed Orchestration exchange and query boundaries."""

import asyncio
from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import httpx
import pytest
from fastapi import status
from pydantic import Field, TypeAdapter
from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette.types import Scope
from typing_extensions import TypedDict

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.application.inner_dto.types.orchestration_outcome_types import (
    OrchestrationBackendErrorDict,
)
from app.orchestration.application.orchestration_command_utils import (
    execute_orchestration_operation,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import OrchestrationExcept
from app.shared.filter_module.base_filter import BaseFilter
from app.shared.ingredient_element.gateway.upstream_reply_enums import (
    UpstreamReplyKind,
)
from app.shared.types.base_types import JsonValue
from app.shared.utils.query_validation import checked_query_filter, query_shape_matches

_WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")


class _ProbeResultDict(TypedDict, total=True, closed=True):
    """Small typed operation result for the shared boundary tests."""

    count: int
    enabled: bool


_PROBE_RESULT_ADAPTER: TypeAdapter[_ProbeResultDict] = TypeAdapter(_ProbeResultDict)


class _ProbeQueryFilter(BaseFilter):
    """Query fields with distinct Python and Source wire names."""

    page_size: Annotated[int, Field(alias="pageSize", description="Result page size.")]
    page_cursor: Annotated[
        str | None,
        Field(alias="pageCursor", description="Optional continuation cursor."),
    ] = None


@pytest.fixture
def request_factory() -> Callable[[str], Request]:
    """Build a Starlette request retaining the original encoded query string."""

    def build_request(query: str) -> Request:
        scope: Scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/probe",
            "raw_path": b"/probe",
            "query_string": query.encode("utf-8"),
            "headers": [],
            "server": ("test", 80),
            "client": ("127.0.0.1", 1234),
        }
        result = Request(scope)
        return result

    return build_request


def _parse_probe_result(payload: JsonValue) -> _ProbeResultDict:
    """Validate a strict typed result without wrapping it in an application DTO."""
    result = _PROBE_RESULT_ADAPTER.validate_python(payload, strict=True)
    return result


def _json_response_handler(
    status_code: int,
    payload: JsonValue,
) -> Callable[[httpx.Request], httpx.Response]:
    """Build an isolated MockTransport response for one source exchange."""

    def handler(request: httpx.Request) -> httpx.Response:
        result = httpx.Response(status_code, json=payload, request=request)
        return result

    return handler


def _run_operation(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    result_statuses: tuple[int, ...] = (status.HTTP_200_OK,),
    workspace_id: UUID | None = None,
) -> OrchestrationOutcomeDto[_ProbeResultDict]:
    """Exercise one real caller against a fresh in-memory HTTP transport."""

    async def exercise() -> OrchestrationOutcomeDto[_ProbeResultDict]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            calling = OrchestrationCalling(client, "https://orchestration.test")
            result = await execute_orchestration_operation(
                calling,
                "GET",
                "/probe",
                _parse_probe_result,
                result_statuses=result_statuses,
                workspace_id=workspace_id,
            )
            return result

    outcome = asyncio.run(exercise())
    return outcome


def test_orchestration_operation_preserves_source_result_status_and_typed_body() -> None:
    success_payload: JsonValue = {"count": 7, "enabled": True}
    cases: dict[str, int] = {
        "read": status.HTTP_200_OK,
        "created": status.HTTP_201_CREATED,
    }

    for _case_name, status_code in cases.items():
        outcome = _run_operation(
            _json_response_handler(status_code, success_payload),
            result_statuses=(status.HTTP_200_OK, status.HTTP_201_CREATED),
        )
        assert outcome.status_code == status_code
        assert outcome.body_kind is UpstreamReplyKind.RESULT
        assert outcome.response == success_payload


def test_orchestration_conflict_can_be_a_domain_result_or_backend_error_fallback() -> None:
    result_payload: JsonValue = {"count": 3, "enabled": False}
    error_payload: JsonValue = {
        "code": "CONFLICT",
        "message": "The revision changed.",
        "retryable": False,
    }
    expected_error: OrchestrationBackendErrorDict = {
        "code": "CONFLICT",
        "message": "The revision changed.",
        "retryable": False,
    }
    cases: dict[
        str,
        tuple[
            JsonValue,
            UpstreamReplyKind,
            _ProbeResultDict | OrchestrationBackendErrorDict,
        ],
    ] = {
        "domain result": (
            result_payload,
            UpstreamReplyKind.RESULT,
            {"count": 3, "enabled": False},
        ),
        "backend error": (error_payload, UpstreamReplyKind.ERROR, expected_error),
    }

    for _case_name, (payload, expected_kind, expected_body) in cases.items():
        outcome = _run_operation(
            _json_response_handler(status.HTTP_409_CONFLICT, payload),
            result_statuses=(status.HTTP_200_OK, status.HTTP_409_CONFLICT),
        )
        assert outcome.status_code == status.HTTP_409_CONFLICT
        assert outcome.body_kind is expected_kind
        assert outcome.response == expected_body


def test_orchestration_backend_error_statuses_pass_through() -> None:
    cases: dict[int, str] = {
        status.HTTP_401_UNAUTHORIZED: "AUTH_FAILED",
        status.HTTP_404_NOT_FOUND: "TASK_NOT_FOUND",
        status.HTTP_503_SERVICE_UNAVAILABLE: "DEPENDENCY_UNAVAILABLE",
    }

    for status_code, code in cases.items():
        payload: JsonValue = {
            "code": code,
            "message": "The backend rejected the request.",
            "retryable": status_code == status.HTTP_503_SERVICE_UNAVAILABLE,
        }
        outcome = _run_operation(_json_response_handler(status_code, payload))
        assert outcome.status_code == status_code
        assert outcome.body_kind is UpstreamReplyKind.ERROR
        assert outcome.response == payload


def test_malformed_or_unexpected_orchestration_replies_become_correlated_502s() -> None:
    cases: dict[str, tuple[int, JsonValue]] = {
        "boolean is not an integer result": (
            status.HTTP_200_OK,
            {"count": True, "enabled": True},
        ),
        "integer is not a boolean result": (
            status.HTTP_200_OK,
            {"count": 4, "enabled": 1},
        ),
        "fraction is not an integer result": (
            status.HTTP_200_OK,
            {"count": 4.5, "enabled": True},
        ),
        "incomplete backend error": (
            status.HTTP_400_BAD_REQUEST,
            {"code": "INVALID_INPUT"},
        ),
        "unexpected accepted response": (
            status.HTTP_202_ACCEPTED,
            {
                "code": "UNKNOWN_OUTCOME",
                "message": "The command outcome is unknown.",
                "retryable": False,
            },
        ),
    }

    for _case_name, (status_code, payload) in cases.items():
        with pytest.raises(OrchestrationExcept) as error:
            _run_operation(
                _json_response_handler(status_code, payload),
                workspace_id=_WORKSPACE_ID,
            )
        assert error.value.status_code == status.HTTP_502_BAD_GATEWAY
        assert error.value.workspace_id == _WORKSPACE_ID


def test_orchestration_transport_errors_keep_workspace_correlation() -> None:
    def unavailable_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    with pytest.raises(OrchestrationExcept) as error:
        _run_operation(unavailable_handler, workspace_id=_WORKSPACE_ID)

    assert error.value.status_code == status.HTTP_502_BAD_GATEWAY
    assert error.value.workspace_id == _WORKSPACE_ID


def test_query_shape_matches_required_optional_unknown_and_duplicate_keys() -> None:
    cases: dict[str, tuple[str, bool]] = {
        "required key": ("limit=20", True),
        "optional key": ("limit=20&cursor=next", True),
        "missing required key": ("cursor=next", False),
        "unknown key": ("limit=20&unexpected=true", False),
        "duplicate required key": ("limit=20&limit=30", False),
        "duplicate optional key": ("limit=20&cursor=next&cursor=last", False),
    }

    for _case_name, (query, expected) in cases.items():
        result = query_shape_matches(
            QueryParams(query),
            required=("limit",),
            optional=("cursor",),
        )
        assert result is expected


def test_checked_query_filter_retains_validated_wire_aliases(
    request_factory: Callable[[str], Request],
) -> None:
    cases: dict[str, tuple[str, dict[str, str], dict[str, str]]] = {
        "both aliases": (
            "pageSize=5&pageCursor=resume-1",
            {"pageSize": "5", "pageCursor": "resume-1"},
            {"pageSize": "5", "pageCursor": "resume-1"},
        ),
        "omitted optional alias": (
            "pageSize=5",
            {"pageSize": "5"},
            {"pageSize": "5"},
        ),
    }

    for _case_name, (query, input_values, expected_wire_values) in cases.items():
        filters = _ProbeQueryFilter.model_validate(input_values)
        result = checked_query_filter(request_factory(query), filters)
        assert result is filters
        assert result.to_query_params() == expected_wire_values
