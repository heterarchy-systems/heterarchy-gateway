"""Shared typed failure mapping for Mixed request-owned fanout."""

import asyncio

from fastapi import status
from pydantic import TypeAdapter

from app.forge.application.inner_dto.forge_envelope_dto import (
    ForgeCommandFailureEnvelopeDto,
    ForgeCommandOutcomeDto,
    ForgeCommandSuccessEnvelopeDto,
)
from app.mixed_module.application.inner_dto.mixed_dependency_failure_inner_dto import (
    ForgeGatewayFailureDto,
    ForgeSourceFailureDto,
    MixedDependencyFailureDto,
    MixedDependencyFailureSetDto,
    MixedGatewayTimeoutFailureDto,
    OrchestrationGatewayFailureDto,
    OrchestrationSourceFailureDto,
)
from app.mixed_module.exceptions.mixed_exceptions import MixedDependencyFailureError
from app.orchestration.application.inner_dto.orchestration_outcome_dto import (
    OrchestrationOutcomeDto,
)
from app.orchestration.exceptions.orchestration_exceptions import (
    OrchestrationBackendErrorResponse,
)
from app.shared.exception import ForgeExcept, OrchestrationExcept
from app.shared.ingredient_element.gateway.upstream_reply_enums import UpstreamReplyKind


def require_forge_success[ResultDictT](
    outcome: ForgeCommandOutcomeDto[ResultDictT],
) -> ForgeCommandSuccessEnvelopeDto[ResultDictT]:
    """Return a Forge success envelope or raise its exact source rejection.

    Args:
        outcome: Status-aware Forge command result.
    Return:
        Typed success envelope with the original request identity.
    """
    response = outcome.response
    if isinstance(response, ForgeCommandFailureEnvelopeDto):
        failure = ForgeSourceFailureDto(
            status_code=outcome.status_code,
            response=response,
        )
        raise MixedDependencyFailureError(failure=failure)
    result = response
    return result


def require_orchestration_success[ResultDictT](
    outcome: OrchestrationOutcomeDto[ResultDictT],
    result_adapter: TypeAdapter[ResultDictT],
) -> ResultDictT:
    """Return a typed Orchestration result or raise its original error body.

    Args:
        outcome: Status-aware Orchestration result.
        result_adapter: Operation-specific closed TypedDict validator.
    Return:
        Operation result dictionary validated at the adapter boundary.
    """
    response = outcome.response
    if outcome.body_kind is UpstreamReplyKind.ERROR:
        backend_error = OrchestrationBackendErrorResponse.model_validate(response)
        failure = OrchestrationSourceFailureDto(
            status_code=outcome.status_code,
            response=backend_error.to_inner_dto(),
        )
        raise MixedDependencyFailureError(failure=failure)
    result = result_adapter.validate_python(response, strict=True)
    return result


def forge_gateway_failure(error: ForgeExcept) -> MixedDependencyFailureError:
    """Preserve the original Forge exception status and request identity.

    Args:
        error: Typed Forge transport or response-boundary exception.
    Return:
        Mixed failure that triggers sibling cancellation.
    """
    response = error.to_forge_error_response()
    failure = ForgeGatewayFailureDto(
        status_code=error.status_code,
        code=response.code,
        message=response.message,
        retryable=response.retryable,
        request_id=response.request_id,
    )
    result = MixedDependencyFailureError(failure=failure)
    return result


def orchestration_gateway_failure(
    error: OrchestrationExcept,
) -> MixedDependencyFailureError:
    """Preserve the original Orchestration exception and Workspace identity.

    Args:
        error: Typed Orchestration transport or response-boundary exception.
    Return:
        Mixed failure that triggers sibling cancellation.
    """
    response = error.to_orchestration_error_response()
    failure = OrchestrationGatewayFailureDto(
        status_code=error.status_code,
        code=response.code,
        message=response.message,
        retryable=response.retryable,
        workspace_id=response.workspace_id,
    )
    result = MixedDependencyFailureError(failure=failure)
    return result


def gateway_deadline_failure() -> MixedDependencyFailureError:
    """Create a Gateway-owned deadline failure without backend attribution.

    Args:
        None.
    Return:
        Typed 504 failure for the complete Mixed request deadline.
    """
    failure = MixedGatewayTimeoutFailureDto(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        code="mixed_request_timeout",
        message="Mixed backend reads exceeded the Gateway request deadline",
        retryable=True,
    )
    result = MixedDependencyFailureError(failure=failure)
    return result


def dependency_failure_set(
    errors: tuple[MixedDependencyFailureError, ...],
) -> MixedDependencyFailureSetDto:
    """Collect typed child failures in backend order after TaskGroup joins.

    Args:
        errors: Caught typed child errors from the completed TaskGroup.
    Return:
        Typed error response. Forge status takes precedence if both legs fail.
    """
    failures: tuple[MixedDependencyFailureDto, ...] = tuple(
        sorted(
            (error.failure for error in errors),
            key=lambda failure: failure.to_dict()["backend"].value,
        )
    )
    result = MixedDependencyFailureSetDto(
        status_code=failures[0].status_code,
        failures=failures,
    )
    return result


def dependency_errors(
    errors: ExceptionGroup[MixedDependencyFailureError],
) -> tuple[MixedDependencyFailureError, ...]:
    """Flatten matching TaskGroup failures while preserving unexpected groups.

    Args:
        errors: ExceptionGroup selected by ``except* MixedDependencyFailureError``.
    Return:
        Flat typed failures after TaskGroup cancellation and join.
    """
    result: list[MixedDependencyFailureError] = []
    for error in errors.exceptions:
        if isinstance(error, MixedDependencyFailureError):
            result.append(error)
        else:
            result.extend(dependency_errors(errors=error))
    return tuple(result)


def completed_task_result[ResultT](task: asyncio.Task[ResultT] | None) -> ResultT:
    """Read one result after its owning TaskGroup has completed successfully.

    Args:
        task: Task handle captured inside the owning TaskGroup.
    Return:
        The completed task result.
    """
    if task is None:
        raise RuntimeError("TaskGroup completed without creating a result task")
    result = task.result()
    return result
