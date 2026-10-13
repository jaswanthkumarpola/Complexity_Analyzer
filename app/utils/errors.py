"""
Centralized error types and HTTP exception helpers.
"""
from __future__ import annotations

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class AnalysisError(Exception):
    """Raised when the analysis pipeline encounters a non-recoverable error."""

    def __init__(self, message: str, code: str = "ANALYSIS_ERROR") -> None:
        super().__init__(message)
        self.code = code


class ProviderError(Exception):
    """
    Raised when the AI provider is misconfigured or its call fails
    (missing key, timeout, auth failure, bad request, malformed/truncated output).
    `status_code` is the HTTP status the API layer should return.
    """

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


async def analysis_error_handler(
    request: Request, exc: AnalysisError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": str(exc), "code": exc.code, "detail": str(exc)},
    )


async def generic_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    # Never expose stack traces to the browser
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "An internal error occurred.",
            "detail": "An internal error occurred. Check application logs for details.",
        },
    )