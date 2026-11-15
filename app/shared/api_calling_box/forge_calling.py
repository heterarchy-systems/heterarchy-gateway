"""Forge API caller inheriting BaseCalling."""

from collections.abc import Mapping
from typing import override
from urllib.parse import quote

import httpx

from app.shared.api_calling_box.base_calling import BaseCalling
from app.shared.diagnostics.request_trace import FailureScenario, RequestTrace
from app.shared.exception import ForgeExcept
from app.shared.types.base_types import JsonObject


class ForgeCalling(BaseCalling):
    """HTTP caller for the upstream Forge service."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        trace: RequestTrace | None = None,
        failure_scenario: FailureScenario | None = None,
    ) -> None:
        """Initialize the Forge API caller.

        Args:
            client: Shared asynchronous HTTP client.
            base_url: Root URL for the upstream Forge API.
            trace: Optional request-scoped trace recorder.
            failure_scenario: Optional development failure injection.
        Return:
            None.
        """
        super().__init__(
            client,
            base_url,
            "forge",
            trace,
            failure_scenario,
        )

    async def fetch_forge(self, forge_id: str) -> JsonObject:
        """Fetch one forge from the upstream API.

        Args:
            forge_id: Identifier of the forge to fetch.
        Return:
            Decoded forge JSON object.
        """
        payload = await self.fetch_json(f"/forges/{quote(forge_id, safe='')}")
        return payload

    async def fetch_forges(self, params: Mapping[str, str]) -> JsonObject:
        """Fetch a filtered forge list from the upstream API.

        Args:
            params: Configured forge-list query parameters.
        Return:
            Decoded forge-list response object.
        """
        payload = await self.fetch_json("/forges", params=params)
        return payload

    async def create_forge(self, body: JsonObject) -> JsonObject:
        """Create a forge resource on the upstream API.

        Args:
            body: JSON payload for creating the forge.
        Return:
            Decoded forge creation response object.
        """
        payload = await self.post_json("/forges", body)
        return payload

    async def update_forge(self, forge_id: str, body: JsonObject) -> JsonObject:
        """Update an existing forge resource on the upstream API.

        Args:
            forge_id: Identifier of the forge to update.
            body: JSON payload for updating the forge.
        Return:
            Decoded forge update response object.
        """
        payload = await self.put_json(f"/forges/{quote(forge_id, safe='')}", body)
        return payload

    async def delete_forge(self, forge_id: str) -> JsonObject:
        """Delete a forge resource on the upstream API.

        Args:
            forge_id: Identifier of the forge to delete.
        Return:
            Decoded forge deletion response object.
        """
        payload = await self.delete_json(f"/forges/{quote(forge_id, safe='')}")
        return payload

    def with_trace(
        self,
        trace: RequestTrace,
        failure_scenario: FailureScenario | None = None,
    ) -> ForgeCalling:
        """Create a request-traced Forge caller sharing this client and base URL.

        Args:
            trace: Request-scoped trace recorder.
            failure_scenario: Optional development failure injection scenario.
        Return:
            Configured ForgeCalling bound to the trace.
        """
        caller = ForgeCalling(
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
    ) -> ForgeExcept:
        """Construct a ForgeExcept for upstream Forge failures.

        Args:
            status_code: Public HTTP status code to emit.
            code: Stable machine-readable error code.
            message: Sanitized error explanation.
            retryable: Whether callers may retry the failed request.
        Return:
            Structured ForgeExcept instance.
        """
        result = ForgeExcept(
            status_code,
            code,
            message,
            retryable=retryable,
        )
        return result


ForgeCall = ForgeCalling
