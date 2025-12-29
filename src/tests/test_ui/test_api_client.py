"""Unit tests for FlexLink API client."""

from datetime import UTC, datetime

import httpx
import pytest
import respx

from flexlink.models.logs import LogsResponse
from flexlink.models.pipeline import (
    PipelineRunHistoryRecord,
    PipelineRunStatus,
    TaskStatus,
)
from flexlink.ui.api_client import (
    APIConnectionError,
    FlexLinkAPIClient,
    FlexLinkAPIError,
    PipelineNotFoundError,
)


@pytest.fixture
def base_url() -> str:
    """Base URL for API client."""
    return "http://localhost:8000"


@pytest.fixture
async def api_client(base_url: str) -> FlexLinkAPIClient:
    """Create API client instance."""
    return FlexLinkAPIClient(base_url=base_url)


@pytest.mark.asyncio
async def test_client_context_manager(base_url: str) -> None:
    """Test async context manager initialization and cleanup."""
    client = FlexLinkAPIClient(base_url=base_url)

    # Client should not be initialized before context
    with pytest.raises(RuntimeError, match="Client not initialized"):
        _ = client.client

    # Client should be initialized within context
    async with client as api:
        assert api._client is not None
        assert isinstance(api._client, httpx.AsyncClient)
        assert api.client.base_url == httpx.URL(base_url)

    # Client should be cleaned up after context
    assert client._client is None


@pytest.mark.asyncio
@respx.mock
async def test_list_pipelines_success(api_client: FlexLinkAPIClient) -> None:
    """Test successful listing of pipelines."""
    # Mock response
    mock_response = {
        "pipelines": [
            {
                "name": "test-pipeline",
                "description": "Test pipeline",
                "enabled": True,
                "schedule": None,
                "tags": ["test"],
            },
            {
                "name": "scheduled-pipeline",
                "description": "Pipeline with schedule",
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "type": "cron",
                    "expression": "0 */6 * * *",
                    "next_run": "2025-01-01T00:00:00Z",
                },
                "tags": ["scheduled"],
            },
        ],
        "count": 2,
    }

    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Execute
    async with api_client:
        result = await api_client.list_pipelines()

    # Verify
    assert result["count"] == 2
    assert len(result["pipelines"]) == 2
    assert result["pipelines"][0]["name"] == "test-pipeline"
    assert result["pipelines"][1]["schedule"] is not None


@pytest.mark.asyncio
@respx.mock
async def test_get_pipeline_success(api_client: FlexLinkAPIClient) -> None:
    """Test successful retrieval of pipeline details."""
    # Mock response
    mock_response = {
        "name": "test-pipeline",
        "description": "Test pipeline",
        "version": "1.0",
        "enabled": True,
        "steps": [
            {
                "name": "extract",
                "type": "extract",
                "connector": "test-source",
                "method": "GET",
                "path": "/data",
            },
            {
                "name": "load",
                "type": "load",
                "connector": "test-output",
            },
        ],
        "tags": ["test"],
    }

    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines/test-pipeline").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Execute
    async with api_client:
        result = await api_client.get_pipeline("test-pipeline")

    # Verify
    assert result["name"] == "test-pipeline"
    assert result["version"] == "1.0"
    assert len(result["steps"]) == 2
    assert result["steps"][0]["type"] == "extract"


@pytest.mark.asyncio
@respx.mock
async def test_get_pipeline_not_found(api_client: FlexLinkAPIClient) -> None:
    """Test 404 handling when pipeline doesn't exist."""
    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines/nonexistent").mock(
        return_value=httpx.Response(
            404, json={"detail": "Pipeline 'nonexistent' not found"}
        )
    )

    # Execute and verify exception
    async with api_client:
        with pytest.raises(PipelineNotFoundError) as exc_info:
            await api_client.get_pipeline("nonexistent")

        assert exc_info.value.status_code == 404
        assert "nonexistent" in str(exc_info.value)


@pytest.mark.asyncio
@respx.mock
async def test_execute_pipeline_foreground(api_client: FlexLinkAPIClient) -> None:
    """Test synchronous pipeline execution."""
    # Mock response
    mock_response = {
        "run_id": "test-run-123",
        "pipeline_name": "test-pipeline",
        "status": "success",
        "started_at": "2025-01-01T10:00:00Z",
        "completed_at": "2025-01-01T10:00:05Z",
        "duration_seconds": 5.0,
        "steps": [
            {
                "step_name": "extract",
                "status": "success",
                "duration_seconds": 2.0,
                "records_processed": 100,
            },
            {
                "step_name": "load",
                "status": "success",
                "duration_seconds": 3.0,
                "records_processed": 100,
            },
        ],
        "metadata": {
            "records_extracted": 100,
            "records_transformed": 0,
            "records_loaded": 100,
        },
    }

    # Setup mock
    respx.post(
        "http://localhost:8000/api/v1/pipelines/test-pipeline/run",
        params={"background": "false"},
    ).mock(return_value=httpx.Response(200, json=mock_response))

    # Execute
    async with api_client:
        result = await api_client.execute_pipeline("test-pipeline", background=False)

    # Verify
    assert result["run_id"] == "test-run-123"
    assert result["status"] == "success"
    assert result["duration_seconds"] == 5.0
    assert len(result["steps"]) == 2


@pytest.mark.asyncio
@respx.mock
async def test_execute_pipeline_background(api_client: FlexLinkAPIClient) -> None:
    """Test background pipeline execution."""
    # Mock response
    mock_response = {
        "run_id": "bg-run-456",
        "pipeline_name": "test-pipeline",
        "status": "queued",
        "started_at": None,
        "completed_at": None,
    }

    # Setup mock
    respx.post(
        "http://localhost:8000/api/v1/pipelines/test-pipeline/run",
        params={"background": "true"},
    ).mock(return_value=httpx.Response(200, json=mock_response))

    # Execute
    async with api_client:
        result = await api_client.execute_pipeline("test-pipeline", background=True)

    # Verify
    assert result["run_id"] == "bg-run-456"
    assert result["status"] == "queued"
    assert result["started_at"] is None


@pytest.mark.asyncio
@respx.mock
async def test_get_run_status_queued(api_client: FlexLinkAPIClient) -> None:
    """Test polling queued run status."""
    # Mock response
    mock_response = {
        "run_id": "test-run-123",
        "pipeline_name": "test-pipeline",
        "status": "queued",
        "started_at": None,
        "completed_at": None,
        "duration_seconds": None,
        "error_message": None,
    }

    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines/runs/test-run-123").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Execute
    async with api_client:
        result = await api_client.get_run_status("test-run-123")

    # Verify
    assert isinstance(result, PipelineRunStatus)
    assert result.run_id == "test-run-123"
    assert result.status == TaskStatus.QUEUED
    assert result.started_at is None


@pytest.mark.asyncio
@respx.mock
async def test_get_run_status_running(api_client: FlexLinkAPIClient) -> None:
    """Test polling running status."""
    # Mock response
    started_time = datetime.now(UTC)
    mock_response = {
        "run_id": "test-run-123",
        "pipeline_name": "test-pipeline",
        "status": "running",
        "started_at": started_time.isoformat(),
        "completed_at": None,
        "duration_seconds": None,
        "error_message": None,
    }

    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines/runs/test-run-123").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Execute
    async with api_client:
        result = await api_client.get_run_status("test-run-123")

    # Verify
    assert isinstance(result, PipelineRunStatus)
    assert result.status == TaskStatus.RUNNING
    assert result.started_at is not None
    assert result.completed_at is None


@pytest.mark.asyncio
@respx.mock
async def test_get_run_status_completed(api_client: FlexLinkAPIClient) -> None:
    """Test polling completed status."""
    # Mock response
    started_time = datetime.now(UTC)
    completed_time = datetime.now(UTC)
    mock_response = {
        "run_id": "test-run-123",
        "pipeline_name": "test-pipeline",
        "status": "completed",
        "started_at": started_time.isoformat(),
        "completed_at": completed_time.isoformat(),
        "duration_seconds": 5.2,
        "error_message": None,
    }

    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines/runs/test-run-123").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Execute
    async with api_client:
        result = await api_client.get_run_status("test-run-123")

    # Verify
    assert isinstance(result, PipelineRunStatus)
    assert result.status == TaskStatus.COMPLETED
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.duration_seconds == 5.2


@pytest.mark.asyncio
@respx.mock
async def test_get_run_status_failed(api_client: FlexLinkAPIClient) -> None:
    """Test polling failed status with error message."""
    # Mock response
    started_time = datetime.now(UTC)
    completed_time = datetime.now(UTC)
    mock_response = {
        "run_id": "test-run-123",
        "pipeline_name": "test-pipeline",
        "status": "failed",
        "started_at": started_time.isoformat(),
        "completed_at": completed_time.isoformat(),
        "duration_seconds": 2.1,
        "error_message": "Connection timeout",
    }

    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines/runs/test-run-123").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Execute
    async with api_client:
        result = await api_client.get_run_status("test-run-123")

    # Verify
    assert isinstance(result, PipelineRunStatus)
    assert result.status == TaskStatus.FAILED
    assert result.error_message == "Connection timeout"


@pytest.mark.asyncio
@respx.mock
async def test_get_pipeline_runs_success(api_client: FlexLinkAPIClient) -> None:
    """Test retrieving pipeline run history."""
    # Mock response
    mock_response = {
        "runs": [
            {
                "run_id": "run-1",
                "pipeline_name": "test-pipeline",
                "status": "success",
                "started_at": "2025-01-01T10:00:00Z",
                "completed_at": "2025-01-01T10:00:05Z",
                "duration_seconds": 5.0,
                "records_extracted": 100,
                "records_transformed": 0,
                "records_loaded": 100,
                "validation_errors": 0,
                "triggered_by": "manual",
            },
            {
                "run_id": "run-2",
                "pipeline_name": "test-pipeline",
                "status": "failed",
                "started_at": "2025-01-01T09:00:00Z",
                "completed_at": "2025-01-01T09:00:02Z",
                "duration_seconds": 2.0,
                "records_extracted": 0,
                "records_transformed": 0,
                "records_loaded": 0,
                "validation_errors": 0,
                "error_message": "Connection failed",
                "triggered_by": "schedule",
            },
        ]
    }

    # Setup mock
    respx.get(
        "http://localhost:8000/api/v1/pipelines/test-pipeline/runs",
        params={"limit": 50, "offset": 0},
    ).mock(return_value=httpx.Response(200, json=mock_response))

    # Execute
    async with api_client:
        result = await api_client.get_pipeline_runs("test-pipeline")

    # Verify
    assert isinstance(result, list)
    assert len(result) == 2
    assert all(isinstance(r, PipelineRunHistoryRecord) for r in result)
    assert result[0].run_id == "run-1"
    assert result[0].status == "success"
    assert result[1].status == "failed"
    assert result[1].error_message == "Connection failed"


@pytest.mark.asyncio
@respx.mock
async def test_get_pipeline_runs_pagination(api_client: FlexLinkAPIClient) -> None:
    """Test pagination for run history."""
    # Mock response
    mock_response = {
        "runs": [
            {
                "run_id": f"run-{i}",
                "pipeline_name": "test-pipeline",
                "status": "success",
                "started_at": "2025-01-01T10:00:00Z",
                "completed_at": "2025-01-01T10:00:05Z",
                "duration_seconds": 5.0,
                "records_extracted": 100,
                "records_transformed": 0,
                "records_loaded": 100,
                "validation_errors": 0,
                "triggered_by": "manual",
            }
            for i in range(10, 20)
        ]
    }

    # Setup mock
    respx.get(
        "http://localhost:8000/api/v1/pipelines/test-pipeline/runs",
        params={"limit": 10, "offset": 10},
    ).mock(return_value=httpx.Response(200, json=mock_response))

    # Execute
    async with api_client:
        result = await api_client.get_pipeline_runs(
            "test-pipeline", limit=10, offset=10
        )

    # Verify
    assert len(result) == 10
    assert result[0].run_id == "run-10"


@pytest.mark.asyncio
@respx.mock
async def test_get_run_logs_success(api_client: FlexLinkAPIClient) -> None:
    """Test retrieving execution logs."""
    # Mock response
    mock_response = {
        "run_id": "test-run-123",
        "pipeline_name": "test-pipeline",
        "logs": [
            {
                "timestamp": "2025-01-01T10:00:00Z",
                "level": "INFO",
                "logger": "flexlink.core",
                "message": "Pipeline started",
            },
            {
                "timestamp": "2025-01-01T10:00:05Z",
                "level": "INFO",
                "logger": "flexlink.core",
                "message": "Pipeline completed successfully",
            },
        ],
        "total_entries": 2,
    }

    # Setup mock
    respx.get(
        "http://localhost:8000/api/v1/pipelines/test-pipeline/runs/test-run-123/logs",
        params={"limit": 1000},
    ).mock(return_value=httpx.Response(200, json=mock_response))

    # Execute
    async with api_client:
        result = await api_client.get_run_logs("test-pipeline", "test-run-123")

    # Verify
    assert isinstance(result, LogsResponse)
    assert result.run_id == "test-run-123"
    assert result.total_entries == 2
    assert len(result.logs) == 2
    assert result.logs[0].level == "INFO"
    assert result.logs[0].message == "Pipeline started"


@pytest.mark.asyncio
@respx.mock
async def test_get_run_logs_with_limit(api_client: FlexLinkAPIClient) -> None:
    """Test retrieving logs with custom limit."""
    # Mock response
    mock_response = {
        "run_id": "test-run-123",
        "pipeline_name": "test-pipeline",
        "logs": [
            {
                "timestamp": f"2025-01-01T10:00:{i:02d}Z",
                "level": "INFO",
                "logger": "flexlink.core",
                "message": f"Log entry {i}",
            }
            for i in range(100)
        ],
        "total_entries": 100,
    }

    # Setup mock
    respx.get(
        "http://localhost:8000/api/v1/pipelines/test-pipeline/runs/test-run-123/logs",
        params={"limit": 100},
    ).mock(return_value=httpx.Response(200, json=mock_response))

    # Execute
    async with api_client:
        result = await api_client.get_run_logs(
            "test-pipeline", "test-run-123", limit=100
        )

    # Verify
    assert result.total_entries == 100
    assert len(result.logs) == 100


@pytest.mark.asyncio
@respx.mock
async def test_list_connectors_success(api_client: FlexLinkAPIClient) -> None:
    """Test listing available connectors."""
    # Mock response
    mock_response = {
        "connectors": [
            {
                "name": "http-source",
                "type": "http",
                "category": "source",
            },
            {
                "name": "postgres-target",
                "type": "postgresql",
                "category": "target",
            },
        ],
        "count": 2,
    }

    # Setup mock
    respx.get("http://localhost:8000/api/v1/connectors").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Execute
    async with api_client:
        result = await api_client.list_connectors()

    # Verify
    assert result["count"] == 2
    assert len(result["connectors"]) == 2


@pytest.mark.asyncio
@respx.mock
async def test_list_schedules_success(api_client: FlexLinkAPIClient) -> None:
    """Test listing scheduled pipelines."""
    # Mock response
    mock_response = {
        "schedules": [
            {
                "pipeline_name": "hourly-pipeline",
                "next_run_time": "2025-01-01T11:00:00Z",
                "schedule_type": "IntervalTrigger",
            },
            {
                "pipeline_name": "daily-pipeline",
                "next_run_time": "2025-01-02T00:00:00Z",
                "schedule_type": "CronTrigger",
            },
        ],
        "count": 2,
    }

    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines/schedules").mock(
        return_value=httpx.Response(200, json=mock_response)
    )

    # Execute
    async with api_client:
        result = await api_client.list_schedules()

    # Verify
    assert result["count"] == 2
    assert len(result["schedules"]) == 2


@pytest.mark.asyncio
@respx.mock
async def test_error_handling_500(api_client: FlexLinkAPIClient) -> None:
    """Test handling of 500 server errors."""
    # Setup mock
    respx.get("http://localhost:8000/api/v1/pipelines").mock(
        return_value=httpx.Response(500, json={"detail": "Internal server error"})
    )

    # Execute and verify exception
    async with api_client:
        with pytest.raises(FlexLinkAPIError) as exc_info:
            await api_client.list_pipelines()

        assert exc_info.value.status_code == 500


@pytest.mark.asyncio
@respx.mock
async def test_error_handling_network_error(api_client: FlexLinkAPIClient) -> None:
    """Test handling of network errors."""
    # Setup mock to raise connection error
    respx.get("http://localhost:8000/api/v1/pipelines").mock(
        side_effect=httpx.ConnectError("Connection refused")
    )

    # Execute and verify exception
    async with api_client:
        with pytest.raises(APIConnectionError):
            await api_client.list_pipelines()


@pytest.mark.asyncio
@respx.mock
async def test_error_handling_timeout(api_client: FlexLinkAPIClient) -> None:
    """Test handling of request timeouts."""
    # Setup mock to raise timeout
    respx.get("http://localhost:8000/api/v1/pipelines").mock(
        side_effect=httpx.TimeoutException("Request timeout")
    )

    # Execute and verify exception
    async with api_client:
        with pytest.raises(APIConnectionError):
            await api_client.list_pipelines()


@pytest.mark.asyncio
async def test_base_url_normalization() -> None:
    """Test that base URL is normalized correctly."""
    # Test with trailing slash
    client1 = FlexLinkAPIClient(base_url="http://localhost:8000/")
    assert client1.base_url == "http://localhost:8000"

    # Test without trailing slash
    client2 = FlexLinkAPIClient(base_url="http://localhost:8000")
    assert client2.base_url == "http://localhost:8000"

    # Test with different port
    client3 = FlexLinkAPIClient(base_url="http://api.example.com:9000/")
    assert client3.base_url == "http://api.example.com:9000"
