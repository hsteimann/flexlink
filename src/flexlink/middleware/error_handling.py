"""Error handling middleware for global exception handling."""

import logging

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.

    Catches exceptions and returns appropriate HTTP responses:
    - ValueError -> 400 Bad Request
    - KeyError -> 404 Not Found
    - Exception -> 500 Internal Server Error
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        """
        Process request with error handling.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            HTTP response (may be error response)
        """
        try:
            return await call_next(request)
        except ValueError as e:
            # Validation errors -> 400
            logger.error(f"Validation error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Validation error", "detail": str(e)},
            )
        except KeyError as e:
            # Missing resource -> 404
            logger.error(f"Resource not found: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": "Resource not found", "detail": str(e)},
            )
        except PermissionError as e:
            # Permission denied -> 403
            logger.error(f"Permission denied: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"error": "Permission denied", "detail": str(e)},
            )
        except Exception as e:
            # Unexpected errors -> 500
            logger.exception(f"Unexpected error: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred",
                },
            )
