"""Common status-aware transport boundary for Orchestration contracts."""

from collections.abc import Callable, Mapping
from http import HTTPStatus
from uuid import UUID

from fastapi import status
from pydantic import JsonValue, ValidationError

from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.exceptions.orchestration_exceptions import (
    OrchestrationBackendErrorResponse,
)
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.exception import OrchestrationExcept
from app.shared.ingredient_element.gateway.upstream_reply_enums import UpstreamReplyKind
from app.shared.types.json_contract import validate_json_object
from app.shared.types.upstream_exchange import (
    DEFAULT_UPSTREAM_EXCHANGE_POLICY,
    UpstreamExchangePolicy,
    UpstreamJsonExchange,
)

ORCHESTRATION_SWARM_EXCHANGE_POLICY = UpstreamExchangePolicy(
    max_response_bytes=2_097_152,
    max_request_bytes=131_072,
    timeout_seconds=None,
)


async def execute_orchestration_operation[ResultDictT, BodyValueT](
    calling: OrchestrationCalling,
    method: str,
    path: str,
    parse_result: Callable[[JsonValue], ResultDictT],
    *,
    body: Mapping[str, BodyValueT] | None = None,
    params: Mapping[str, str] | None = None,
    result_statuses: tuple[int, ...] = (status.HTTP_200_OK,),
    validate_result_status: Callable[[int, ResultDictT], None] | None = None,
    workspace_id: UUID | None = None,
    exchange_policy: UpstreamExchangePolicy = DEFAULT_UPSTREAM_EXCHANGE_POLICY,
) -> OrchestrationOutcomeDto[ResultDictT]:
    """Forward one operation and distinguish its declared result and error contracts.

    Args:
        calling: Request-scoped backend caller.
        method: Source HTTP method.
        path: Source path including its fixed API prefix.
        parse_result: Operation-owned source-to-DTO parser with scope checks.
        body: Typed JSON command payload when required.
        params: Serialized query filter with source wire aliases.
        result_statuses: Statuses whose bodies can carry the operation result.
        validate_result_status: Source protocol association between result and HTTP status.
        workspace_id: Caller workspace used for local transport error correlation.
        exchange_policy: Request-local byte bounds and deadline.
    Return:
        The original status and an exact typed result or backend error body.
    """
    json_body = validate_json_object(value=body) if body is not None else None
    try:
        exchange = await calling.execute_json_exchange(
            method=method,
            path=path,
            body=json_body,
            params=params,
            policy=exchange_policy,
        )
    except OrchestrationExcept as error:
        raise OrchestrationExcept(
            status_code=error.status_code,
            code=error.code,
            message=error.message,
            retryable=error.retryable,
            workspace_id=workspace_id,
        ) from error

    result = _parse_exchange(
        exchange=exchange,
        parse_result=parse_result,
        result_statuses=result_statuses,
        validate_result_status=validate_result_status,
        workspace_id=workspace_id,
    )
    return result


def _parse_exchange[ResultDictT](
    exchange: UpstreamJsonExchange,
    parse_result: Callable[[JsonValue], ResultDictT],
    result_statuses: tuple[int, ...],
    validate_result_status: Callable[[int, ResultDictT], None] | None,
    workspace_id: UUID | None,
) -> OrchestrationOutcomeDto[ResultDictT]:
    if exchange.status_code in result_statuses:
        try:
            response = parse_result(exchange.payload)
            if validate_result_status is not None:
                validate_result_status(exchange.status_code, response)
        except (ValidationError, ValueError) as error:
            if exchange.status_code < status.HTTP_400_BAD_REQUEST:
                raise _invalid_reply(workspace_id=workspace_id) from error
        else:
            result = OrchestrationOutcomeDto[ResultDictT](
                status_code=exchange.status_code,
                body_kind=UpstreamReplyKind.RESULT,
                response=response,
            )
            return result

    try:
        error_status = HTTPStatus(exchange.status_code)
        if error_status < HTTPStatus.BAD_REQUEST:
            raise ValueError("Unexpected upstream response status")
        backend_error = OrchestrationBackendErrorResponse.model_validate(exchange.payload)
    except (ValidationError, ValueError) as error:
        raise _invalid_reply(workspace_id=workspace_id) from error
    result = OrchestrationOutcomeDto[ResultDictT](
        status_code=exchange.status_code,
        body_kind=UpstreamReplyKind.ERROR,
        response=backend_error.to_inner_dto().to_dict(),
    )
    return result


def _invalid_reply(workspace_id: UUID | None) -> OrchestrationExcept:
    result = OrchestrationExcept(
        status_code=status.HTTP_502_BAD_GATEWAY,
        code="orchestration_invalid_payload",
        message="Upstream orchestration returned an invalid operation response",
        retryable=False,
        workspace_id=workspace_id,
    )
    return result
