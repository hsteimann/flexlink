"""Logging middleware for HTTP request/response tracking."""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses.

    Logs:
    - Incoming request (method, path, client IP)
    - Outgoing response (status code, duration)
    - Request/response metadata
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        """
        Process request and log details.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/endpoint in chain

        Returns:
            HTTP response
        """
        # Generate request ID for tracking
        request_id = id(request)

        # Log incoming request
        start_time = time.time()
        client_host = request.client.host if request.client else "unknown"

        logger.info(
            f"→ [{request_id}] {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client": client_host,
            },
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log exception
            duration = time.time() - start_time
            logger.error(
                f"✗ [{request_id}] {request.method} {request.url.path} "
                f"failed after {duration:.3f}s: {e}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration": duration,
                    "error": str(e),
                },
            )
            raise

        # Log response
        duration = time.time() - start_time
        log_level = logging.INFO if response.status_code < 400 else logging.WARNING

        logger.log(
            log_level,
            f"← [{request_id}] {request.method} {request.url.path} "
            f"{response.status_code} ({duration:.3f}s)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration": duration,
            },
        )

        return response
