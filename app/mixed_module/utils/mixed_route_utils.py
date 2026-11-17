"""Trace, cancellation, and HTTP response handling for Mixed routes."""

import asyncio
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import HTTPException, Request, Response, status
from fastapi.exceptions import RequestValidationError

from app.mixed_module.application.inner_dto.mixed_dependency_failure_inner_dto import (
    MixedDependencyFailureSetDto,
)
from app.mixed_module.application.inner_dto.mixed_swarm_overview_inner_dto import (
    MixedSwarmOverviewInnerDto,
)
from app.mixed_module.application.mixed_application_utils import (
    dependency_failure_set,
    gateway_deadline_failure,
)
from app.mixed_module.application.mixed_dag_governance_app import (
    MixedDagGovernanceApplication,
)
from app.mixed_module.application.mixed_swarm_overview_app import (
    MixedSwarmOverviewApplication,
)
from app.mixed_module.exceptions.mixed_exceptions import (
    MixedDependencyFailureResponse,
    MixedRequestContextError,
)
from app.mixed_module.schema.mixed_dag_governance_schema import (
    MixedDagGovernanceRequest,
    MixedDagGovernanceResponse,
)
from app.mixed_module.schema.mixed_swarm_overview_schema import (
    MixedSwarmOverviewResponse,
)
from app.mixed_module.schema.types.mixed_types import MixedRequestValidationIssue
from app.shared.api_calling_box.forge_calling import ForgeCalling
from app.shared.api_calling_box.orchestration_calling import OrchestrationCalling
from app.shared.diagnostics.request_trace import FailureScenario, RequestTrace, TraceStore
from app.shared.filter_module.mixed_module_filter import MixedSwarmOverviewFilter
from app.shared.ingredient_element.gateway.mixed_enums import MixedDependencyFailureTagEnum
from app.shared.ingredient_element.gateway.request_trace_enums import UpstreamOutcome
from app.shared.settings_modules.gateway_settings import GatewayRuntimeSettings
from app.shared.types.upstream_payload import model_to_json_value
from app.shared.utils.query_validation import checked_query_filter


class MixedRouteExecutor:
    """Own request tracing, deadline, and response handling for Mixed reads."""

    def __init__(
        self,
        forge_calling: ForgeCalling,
        orchestration_calling: OrchestrationCalling,
        runtime_settings: GatewayRuntimeSettings,
        trace_store: TraceStore,
    ) -> None:
        """Bind the request-specific callers and runtime policies.

        Args:
            forge_calling: Caller carrying the Forge authorization header.
            orchestration_calling: Caller carrying the Orchestration header.
            runtime_settings: Timeout and development simulation policy.
            trace_store: Bounded request trace store.
        Return:
            None.
        """
        self._forge_calling = forge_calling
        self._orchestration_calling = orchestration_calling
        self._runtime_settings = runtime_settings
        self._trace_store = trace_store

    def _record_trace(self, trace: RequestTrace) -> None:
        """Persist one completed Mixed request trace.

        Args:
            trace: Completed request trace.
        Return:
            None.
        """
        self._trace_store.record(snapshot=trace.snapshot())

    def _check_failure_simulation(
        self,
        failure_scenario: FailureScenario | None,
        trace: RequestTrace,
    ) -> None:
        """Reject disabled failure injection before opening either backend call.

        Args:
            failure_scenario: Optional development failure scenario.
            trace: Request trace to finish for a forbidden simulation.
        Return:
            None when the request may proceed.
        """
        if failure_scenario is not None and not self._runtime_settings.failure_simulation_enabled:
            trace.finish(status=status.HTTP_403_FORBIDDEN, inner_dto=None, public_response=None)
            self._record_trace(trace=trace)
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                detail="Failure simulation is disabled",
                headers={"X-Trace-ID": trace.trace_id},
            )

    @staticmethod
    def _request_validation_issue(error: MixedRequestContextError) -> RequestValidationError:
        """Convert a path/body identity mismatch into FastAPI's standard 422 body.

        Args:
            error: Typed preflight rejection raised before upstream fanout.
        Return:
            FastAPI validation error retaining the rejected request location.
        """
        issue = MixedRequestValidationIssue(
            type="value_error",
            loc=error.location,
            msg=error.message,
            input=error.rejected_value,
        )
        result = RequestValidationError([issue])
        return result

    @staticmethod
    def _record_failure_outcomes(
        trace: RequestTrace,
        failure: MixedDependencyFailureSetDto,
    ) -> None:
        """Mark source rejections and unknown Forge outcomes in the trace.

        Args:
            trace: Request trace containing upstream exchanges.
            failure: Typed dependency failure set returned by the composition.
        Return:
            None.
        """
        for item in failure.failures:
            details = item.to_dict()
            outcome = (
                UpstreamOutcome.UNKNOWN
                if details["kind"] is MixedDependencyFailureTagEnum.FORGE_SOURCE
                and details["status_code"] == status.HTTP_202_ACCEPTED
                else UpstreamOutcome.FAILED
            )
            trace.record_upstream_outcome(
                service_name=details["backend"].value,
                outcome=outcome,
                error=f"Mixed dependency returned {details['kind'].value}",
            )

    def _failure_response(
        self,
        failure: MixedDependencyFailureSetDto,
        response: Response,
        trace: RequestTrace,
        stage_started: float,
    ) -> MixedDependencyFailureResponse:
        """Validate and record typed source or Gateway dependency failures.

        Args:
            failure: Failure DTOs retaining each status and response body.
            response: HTTP response whose status follows fixed backend order.
            trace: Current request trace.
            stage_started: Monotonic start of the composition stage.
        Return:
            Validated public failure response.
        """
        public_response = MixedDependencyFailureResponse.model_validate(failure.to_dict())
        self._record_failure_outcomes(trace=trace, failure=failure)
        trace.record_stage(name="BFF compose", started=stage_started, status="failed")
        response.status_code = failure.status_code
        response.headers["X-Trace-ID"] = trace.trace_id
        public_json = model_to_json_value(model=public_response)
        trace.finish(status=failure.status_code, inner_dto=public_json, public_response=public_json)
        self._record_trace(trace=trace)
        result = public_response
        return result

    def _timeout_failure(
        self,
        response: Response,
        trace: RequestTrace,
        stage_started: float,
    ) -> MixedDependencyFailureResponse:
        """Return the Gateway-owned overall request deadline response.

        Args:
            response: HTTP response whose status becomes 504.
            trace: Request trace after child cancellation and join completed.
            stage_started: Monotonic start of the composition stage.
        Return:
            Sanitized Gateway timeout response without a backend attribution.
        """
        failure = dependency_failure_set(errors=(gateway_deadline_failure(),))
        result = self._failure_response(
            failure=failure, response=response, trace=trace, stage_started=stage_started
        )
        return result

    async def execute_swarm_overview(
        self,
        request: Request,
        response: Response,
        workspace_id: UUID,
        swarm_run_id: UUID,
        filters: MixedSwarmOverviewFilter,
        failure_scenario: FailureScenario | None,
    ) -> MixedSwarmOverviewResponse | MixedDependencyFailureResponse:
        """Execute the filtered Mixed Swarm overview request.

        Args:
            request: Incoming request retaining the original query multimap.
            response: HTTP response for trace and upstream source status.
            workspace_id: Workspace identity selected by the route path.
            swarm_run_id: Swarm identity selected by the route path.
            filters: Required Forge caller context and optional observations.
            failure_scenario: Optional development failure injection.
        Return:
            Validated overview or preserved dependency failure response.
        """
        trace = RequestTrace(trace_id=str(uuid4()))
        response.headers["X-Trace-ID"] = trace.trace_id
        self._check_failure_simulation(failure_scenario=failure_scenario, trace=trace)
        try:
            checked_query_filter(request=request, filters=filters)
        except RequestValidationError:
            trace.finish(
                status=status.HTTP_422_UNPROCESSABLE_CONTENT, inner_dto=None, public_response=None
            )
            self._record_trace(trace=trace)
            raise
        application = MixedSwarmOverviewApplication(
            forge_calling=self._forge_calling.with_trace(
                trace=trace, failure_scenario=failure_scenario
            ),
            orchestration_calling=self._orchestration_calling.with_trace(
                trace=trace, failure_scenario=failure_scenario
            ),
        )
        stage_started = perf_counter()
        try:
            async with asyncio.timeout(self._runtime_settings.http_timeout_seconds):
                outcome = await application.execute(
                    workspace_id=workspace_id, swarm_run_id=swarm_run_id, filters=filters
                )
        except TimeoutError:
            result = self._timeout_failure(
                response=response, trace=trace, stage_started=stage_started
            )
            return result
        match outcome:
            case MixedDependencyFailureSetDto():
                result = self._failure_response(
                    failure=outcome, response=response, trace=trace, stage_started=stage_started
                )
                return result
            case MixedSwarmOverviewInnerDto() if not outcome.matches_filter:
                public_response = MixedSwarmOverviewResponse.model_validate(outcome.to_dict())
                inner_json = model_to_json_value(model=public_response)
                trace.record_stage(name="BFF compose", started=stage_started, status="success")
                trace.finish(
                    status=status.HTTP_404_NOT_FOUND, inner_dto=inner_json, public_response=None
                )
                self._record_trace(trace=trace)
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail="No Swarm overview matches the requested observations",
                    headers={"X-Trace-ID": trace.trace_id},
                )
            case MixedSwarmOverviewInnerDto():
                result = MixedSwarmOverviewResponse.model_validate(outcome.to_dict())
                trace.record_stage(name="BFF compose", started=stage_started, status="success")
                public_json = model_to_json_value(model=result)
                trace.finish(
                    status=status.HTTP_200_OK, inner_dto=public_json, public_response=public_json
                )
                self._record_trace(trace=trace)
                return result

    async def execute_dag_governance(
        self,
        response: Response,
        workspace_id: UUID,
        request: MixedDagGovernanceRequest,
        failure_scenario: FailureScenario | None,
    ) -> MixedDagGovernanceResponse | MixedDependencyFailureResponse:
        """Execute the Mixed independent DAG and governance read request.

        Args:
            response: HTTP response for trace and upstream source status.
            workspace_id: Workspace identity selected by the route path.
            request: Caller-owned Forge context and governance key.
            failure_scenario: Optional development failure injection.
        Return:
            Validated governance view or preserved dependency failures.
        """
        trace = RequestTrace(trace_id=str(uuid4()))
        response.headers["X-Trace-ID"] = trace.trace_id
        self._check_failure_simulation(failure_scenario=failure_scenario, trace=trace)
        application = MixedDagGovernanceApplication(
            forge_calling=self._forge_calling.with_trace(
                trace=trace, failure_scenario=failure_scenario
            ),
            orchestration_calling=self._orchestration_calling.with_trace(
                trace=trace, failure_scenario=failure_scenario
            ),
        )
        stage_started = perf_counter()
        try:
            async with asyncio.timeout(self._runtime_settings.http_timeout_seconds):
                outcome = await application.execute(workspace_id=workspace_id, request=request)
        except MixedRequestContextError as error:
            validation_error = self._request_validation_issue(error=error)
            trace.record_stage(
                name="BFF request", started=stage_started, status="failed", error=error.message
            )
            trace.finish(
                status=status.HTTP_422_UNPROCESSABLE_CONTENT, inner_dto=None, public_response=None
            )
            self._record_trace(trace=trace)
            raise validation_error from error
        except TimeoutError:
            result = self._timeout_failure(
                response=response, trace=trace, stage_started=stage_started
            )
            return result
        match outcome:
            case MixedDependencyFailureSetDto():
                result = self._failure_response(
                    failure=outcome, response=response, trace=trace, stage_started=stage_started
                )
                return result
            case _:
                result = MixedDagGovernanceResponse.model_validate(outcome.to_dict())
                trace.record_stage(name="BFF compose", started=stage_started, status="success")
                public_json = model_to_json_value(model=result)
                trace.finish(
                    status=status.HTTP_200_OK, inner_dto=public_json, public_response=public_json
                )
                self._record_trace(trace=trace)
                return result
