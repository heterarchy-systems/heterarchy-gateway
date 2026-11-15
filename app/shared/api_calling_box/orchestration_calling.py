"""Orchestration API caller inheriting BaseCalling."""

from collections.abc import Mapping
from typing import override
from urllib.parse import quote

import httpx

from app.shared.api_calling_box.base_calling import BaseCalling
from app.shared.diagnostics.request_trace import FailureScenario, RequestTrace
from app.shared.exception import OrchestrationExcept
from app.shared.types.base_types import JsonObject


class OrchestrationCalling(BaseCalling):
    """HTTP caller for the upstream Orchestration service."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        trace: RequestTrace | None = None,
        failure_scenario: FailureScenario | None = None,
    ) -> None:
        """Initialize the orchestration API caller.

        Args:
            client: Shared asynchronous HTTP client.
            base_url: Root URL for the upstream Orchestration API.
            trace: Optional request-scoped trace recorder.
            failure_scenario: Optional development failure injection.
        Return:
            None.
        """
        super().__init__(
            client,
            base_url,
            "orchestration",
            trace,
            failure_scenario,
        )

    async def start_workflow(
        self,
        workflow_name: str,
        inputs: JsonObject,
    ) -> JsonObject:
        """Start an upstream workflow.

        Args:
            workflow_name: Name of the workflow to start.
            inputs: JSON input object passed to the workflow.
        Return:
            Decoded workflow-start response.
        """
        workflow_path = quote(workflow_name, safe="")
        payload = await self.post_json(
            f"/workflows/{workflow_path}/runs",
            {"inputs": inputs},
        )
        return payload

    async def fetch_task(self, task_id: str) -> JsonObject:
        """Fetch one orchestration task.

        Args:
            task_id: Identifier of the task to fetch.
        Return:
            Decoded task JSON object.
        """
        payload = await self.fetch_json(f"/tasks/{quote(task_id, safe='')}")
        return payload

    async def fetch_tasks(self, params: Mapping[str, str]) -> JsonObject:
        """Fetch orchestration tasks matching query parameters.

        Args:
            params: Configured orchestration query parameters.
        Return:
            Decoded orchestration-list response object.
        """
        payload = await self.fetch_json("/tasks", params=params)
        return payload

    async def cancel_task(self, task_id: str) -> JsonObject:
        """Cancel one orchestration task.

        Args:
            task_id: Identifier of the task to cancel.
        Return:
            Decoded cancellation response.
        """
        payload = await self.delete_json(f"/tasks/{quote(task_id, safe='')}")
        return payload

    def with_trace(
        self,
        trace: RequestTrace,
        failure_scenario: FailureScenario | None = None,
    ) -> OrchestrationCalling:
        """Create a request-traced Orchestration caller sharing this client and base URL.

        Args:
            trace: Request-scoped trace recorder.
            failure_scenario: Optional development failure injection scenario.
        Return:
            Configured OrchestrationCalling bound to the trace.
        """
        caller = OrchestrationCalling(
            self._client,
            self._base_url,
            trace=trace,
            failure_scenario=failure_scenario,
        )
        return caller

    @override
    def _build_upstream_exception(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool,
    ) -> OrchestrationExcept:
        """Construct an OrchestrationExcept for upstream Orchestration failures.

        Args:
            status_code: Public HTTP status code to emit.
            code: Stable machine-readable error code.
            message: Sanitized error explanation.
            retryable: Whether callers may retry the failed request.
        Return:
            Structured OrchestrationExcept instance.
        """
        result = OrchestrationExcept(
            status_code,
            code,
            message,
            retryable=retryable,
        )
        return result


OrchestrationCall = OrchestrationCalling
