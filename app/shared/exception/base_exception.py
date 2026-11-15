"""Shared base exception and error response contract for Gateway BFF."""

from typing import Annotated

from pydantic import Field

from app.shared.base_schema import BackendReadError


class BaseExcept(Exception):
    """Base exception carrying HTTP status and sanitized error metadata."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
    ) -> None:
        """Initialize a structured gateway exception.

        Args:
            status_code: Public HTTP status code to return.
            code: Machine-readable error code.
            message: Sanitized human-readable error message.
            retryable: Whether the caller may safely retry the operation.
        Return:
            None.
        """
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)

    def to_error_response(self) -> BackendReadError:
        """Convert the exception into a validated public error schema.

        Args:
            None.
        Return:
            Sanitized BackendReadError response model.
        """
        result = BackendReadError(
            code=self.code,
            message=self.message,
            retryable=self.retryable,
        )
        return result


class GatewayErrorResponse(BackendReadError):
    """Standard public error response payload."""

    service: Annotated[
        str | None,
        Field(description="Upstream service associated with the error, if any."),
    ]
