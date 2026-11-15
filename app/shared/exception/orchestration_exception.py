"""Unified Orchestration exception and error response contract."""

from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.shared.base_schema import BackendReadError
from app.shared.exception.base_exception import BaseExcept


class OrchestrationErrorResponse(BackendReadError):
    """Sanitized public Orchestration error response."""

    workspace_id: Annotated[
        UUID | None,
        Field(description="Optional Workspace identity associated with the failure."),
    ]


class OrchestrationExcept(BaseExcept):
    """Unified exception for all Orchestration upstream and domain boundary failures."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        workspace_id: UUID | None = None,
    ) -> None:
        """Initialize an Orchestration exception.

        Args:
            status_code: Public HTTP status code to return.
            code: Stable Orchestration error code.
            message: Sanitized Orchestration error message.
            retryable: Whether the caller may safely retry the operation.
            workspace_id: Optional Workspace UUID context.
        Return:
            None.
        """
        super().__init__(status_code, code, message, retryable=retryable)
        self.workspace_id = workspace_id

    def to_orchestration_error_response(self) -> OrchestrationErrorResponse:
        """Build the public Orchestration error response model.

        Args:
            None.
        Return:
            Validated OrchestrationErrorResponse instance.
        """
        result = OrchestrationErrorResponse(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            workspace_id=self.workspace_id,
        )
        return result
