"""Async HTTP client wrapper for FlexLink API."""

import logging
from typing import Any

import httpx

from flexlink.models.logs import LogsResponse
from flexlink.models.pipeline import (
    PipelineExecutionResult,
    PipelineRunHistoryRecord,
    PipelineRunStatus,
)

logger = logging.getLogger(__name__)


class FlexLinkAPIError(Exception):
    """Base exception for FlexLink API errors."""

    def __init__(self, message: str, status_code: int | None = None, response: Any = None):
        """
        Initialize API error.

        Args:
            message: Error message
            status_code: HTTP status code if available
            response: Response data if available
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class PipelineNotFoundError(FlexLinkAPIError):
    """Pipeline not found error (404)."""

    pass


class APIConnectionError(FlexLinkAPIError):
    """API connection error."""

    pass


class FlexLinkAPIClient:
    """Async HTTP client for interacting with FlexLink API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize API client.

        Args:
            base_url: Base URL of FlexLink API
        """
        self.base_url = base_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "FlexLinkAPIClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get HTTP client, raising error if not initialized."""
        if self._client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return self._client

    def _handle_error(self, error: Exception, operation: str) -> None:
        """
        Handle HTTP errors and convert to custom exceptions.

        Args:
            error: The exception that occurred
            operation: Description of the operation being performed

        Raises:
            PipelineNotFoundError: For 404 errors on pipeline operations
            APIConnectionError: For connection errors
            FlexLinkAPIError: For other HTTP errors
        """
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code == 404 and "pipeline" in operation.lower():
                raise PipelineNotFoundError(
                    f"Pipeline not found: {operation}",
                    status_code=status_code,
                    response=error.response.json() if error.response.content else None
                ) from error
            else:
                raise FlexLinkAPIError(
                    f"API error during {operation}: HTTP {status_code}",
                    status_code=status_code,
                    response=error.response.json() if error.response.content else None
                ) from error
        elif isinstance(error, (httpx.ConnectError, httpx.TimeoutException)):
            raise APIConnectionError(
                f"Failed to connect to API during {operation}: {error}"
            ) from error
        else:
            raise FlexLinkAPIError(f"Unexpected error during {operation}: {error}") from error

    async def list_pipelines(self) -> dict[str, Any]:
        """
        List all pipelines with schedule metadata.

        Returns:
            Pipeline list response

        Raises:
            FlexLinkAPIError: On API errors
            APIConnectionError: On connection failures
        """
        try:
            response = await self.client.get("/api/v1/pipelines")
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except Exception as e:
            self._handle_error(e, "listing pipelines")
            raise  # This line won't be reached but satisfies type checker

    async def get_pipeline(self, name: str) -> dict[str, Any]:
        """
        Get detailed pipeline configuration.

        Args:
            name: Pipeline name

        Returns:
            Pipeline detail response

        Raises:
            PipelineNotFoundError: If pipeline doesn't exist
            FlexLinkAPIError: On other API errors
            APIConnectionError: On connection failures
        """
        try:
            response = await self.client.get(f"/api/v1/pipelines/{name}")
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except Exception as e:
            self._handle_error(e, f"getting pipeline '{name}'")
            raise  # This line won't be reached but satisfies type checker

    async def execute_pipeline(self, name: str, background: bool = True) -> dict[str, Any]:
        """
        Execute a pipeline.

        Args:
            name: Pipeline name
            background: Run in background mode (default: True)

        Returns:
            Execution response with run_id

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
        """
        params = {"background": "true" if background else "false"}
        response = await self.client.post(f"/api/v1/pipelines/{name}/run", params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def get_run_status(self, run_id: str) -> PipelineRunStatus:
        """
        Poll execution status.

        Args:
            run_id: Pipeline run ID

        Returns:
            Run status information

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
        """
        response = await self.client.get(f"/api/v1/pipelines/runs/{run_id}")
        response.raise_for_status()
        data = response.json()
        return PipelineRunStatus(**data)

    async def get_pipeline_runs(
        self,
        name: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PipelineRunHistoryRecord]:
        """
        List historical runs for a pipeline (paginated).

        Args:
            name: Pipeline name
            limit: Maximum number of runs to return (default: 50)
            offset: Number of runs to skip (default: 0)

        Returns:
            List of historical run records

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
        """
        params = {"limit": limit, "offset": offset}
        response = await self.client.get(f"/api/v1/pipelines/{name}/runs", params=params)
        response.raise_for_status()
        data = response.json()
        return [PipelineRunHistoryRecord(**record) for record in data.get("runs", [])]

    async def get_run_logs(
        self,
        name: str,
        run_id: str,
        limit: int = 1000,
    ) -> LogsResponse:
        """
        Retrieve execution logs.

        Args:
            name: Pipeline name
            run_id: Pipeline run ID
            limit: Maximum number of log entries (default: 1000)

        Returns:
            Logs response with log entries

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
        """
        params = {"limit": limit}
        response = await self.client.get(
            f"/api/v1/pipelines/{name}/runs/{run_id}/logs",
            params=params,
        )
        response.raise_for_status()
        data = response.json()
        return LogsResponse(**data)

    async def list_connectors(self) -> dict[str, Any]:
        """
        List available connectors.

        Returns:
            Connectors list response

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
        """
        response = await self.client.get("/api/v1/connectors")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def list_schedules(self) -> dict[str, Any]:
        """
        List scheduled pipelines with next run times.

        Returns:
            Schedules list response

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
        """
        response = await self.client.get("/api/v1/pipelines/schedules")
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    async def get_run_result(self, run_id: str) -> PipelineExecutionResult:
        """
        Get full execution result for a completed run.

        Args:
            run_id: Pipeline run ID

        Returns:
            Execution result with steps and metadata

        Raises:
            httpx.HTTPStatusError: On 4xx/5xx responses
        """
        response = await self.client.get(f"/api/v1/pipelines/runs/{run_id}")
        response.raise_for_status()
        data = response.json()

        # If the run is completed, fetch full result
        if data.get("status") in ["completed", "success", "failed", "partial"]:
            # Try to get full result from history endpoint
            # Note: This may need adjustment based on actual API implementation
            return PipelineExecutionResult(**data)

        # If still running, return minimal data
        raise ValueError(f"Run {run_id} is not completed yet")
