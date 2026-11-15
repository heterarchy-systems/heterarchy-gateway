"""Unified Forge exception and error response contract."""

from typing import Annotated
from uuid import UUID

from pydantic import Field

from app.shared.base_schema import BackendReadError
from app.shared.exception.base_exception import BaseExcept


class ForgeErrorResponse(BackendReadError):
    """Sanitized public Forge error response preserving optional request correlation."""

    request_id: Annotated[
        UUID | None,
        Field(description="Logical Forge request correlation UUID when available."),
    ]


class ForgeExcept(BaseExcept):
    """Unified exception for all Forge upstream and domain boundary failures."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        request_id: UUID | None = None,
    ) -> None:
        """Initialize a Forge exception.

        Args:
            status_code: Public HTTP status code to return.
            code: Stable Forge error code.
            message: Sanitized Forge error message.
            retryable: Whether the caller may safely retry the operation.
            request_id: Optional Forge correlation UUID.
        Return:
            None.
        """
        super().__init__(status_code, code, message, retryable=retryable)
        self.request_id = request_id

    def to_forge_error_response(self) -> ForgeErrorResponse:
        """Build the public Forge error response model.

        Args:
            None.
        Return:
            Validated ForgeErrorResponse instance.
        """
        result = ForgeErrorResponse(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
            request_id=self.request_id,
        )
        return result
