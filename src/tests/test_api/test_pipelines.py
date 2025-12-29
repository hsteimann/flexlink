"""Tests for pipeline API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.run_history import RunHistoryStorage
from flexlink.core.scheduler_service import SchedulerService
from flexlink.core.task_manager import TaskInfo, TaskManager
from flexlink.main import app
from flexlink.models.pipeline import (
    ExecutionMetadata,
    PipelineConfig,
    PipelineExecutionResult,
    PipelineStepConfig,
    ScheduleConfig,
    StepResult,
    StepType,
    TaskStatus,
)


@pytest.fixture
def mock_pipeline_registry():
    """Mock pipeline registry."""
    registry = Mock(spec=PipelineRegistry)

    # Mock pipeline config
    test_config = PipelineConfig(
        name="test-pipeline",
        description="Test pipeline",
        version="1.0",
        tags=["test"],
        enabled=True,
        steps=[
            PipelineStepConfig(
                name="extract",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data"
            ),
            PipelineStepConfig(
                name="load",
                type=StepType.LOAD,
                connector="test-output"
            )
        ]
    )

    registry.list_pipelines.return_value = ["test-pipeline"]
    registry.get_pipeline.return_value = test_config

    return registry


@pytest.fixture
def mock_orchestrator():
    """Mock pipeline orchestrator."""
    orchestrator = Mock(spec=PipelineOrchestrator)

    # Mock execution result
    from datetime import datetime

    result = PipelineExecutionResult(
        run_id="test-run-123",
        pipeline_name="test-pipeline",
        status="success",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=1.5,
        steps=[
            StepResult(
                step_name="extract",
                status="success",
                duration_seconds=0.5,
                records_processed=100
            ),
            StepResult(
                step_name="load",
                status="success",
                duration_seconds=1.0,
                records_processed=100
            )
        ],
        metadata=ExecutionMetadata(
            records_extracted=100,
            records_transformed=0,
            records_loaded=100
        )
    )

    orchestrator.execute_pipeline = AsyncMock(return_value=result)

    return orchestrator


@pytest.fixture
def mock_run_history():
    """Mock run history storage."""
    run_history = Mock(spec=RunHistoryStorage)
    run_history.list_runs = AsyncMock(return_value=[])
    run_history.save_run = AsyncMock()
    return run_history


@pytest.fixture
def mock_task_manager():
    """Mock task manager."""
    task_manager = Mock(spec=TaskManager)
    return task_manager


@pytest.fixture
def mock_scheduler_service():
    """Mock scheduler service."""
    scheduler = Mock(spec=SchedulerService)
    scheduler.get_scheduled_pipelines.return_value = []
    scheduler.update_pipeline_schedule = Mock()
    scheduler.run_pipeline_now = AsyncMock()
    return scheduler


@pytest.fixture
def test_client(
    mock_pipeline_registry,
    mock_orchestrator,
    mock_run_history,
    mock_task_manager,
    mock_scheduler_service,
):
    """Test client with mocked dependencies."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


def test_list_pipelines(test_client):
    """Test listing all pipelines with metadata."""
    response = test_client.get("/api/v1/pipelines")

    assert response.status_code == 200
    data = response.json()

    assert "pipelines" in data
    assert "count" in data
    assert data["count"] == 1
    assert len(data["pipelines"]) == 1

    # Verify pipeline list item structure
    pipeline = data["pipelines"][0]
    assert pipeline["name"] == "test-pipeline"
    assert pipeline["description"] == "Test pipeline"
    assert pipeline["enabled"] is True
    assert pipeline["tags"] == ["test"]
    assert "schedule" in pipeline


def test_get_pipeline_details(test_client):
    """Test getting pipeline configuration."""
    response = test_client.get("/api/v1/pipelines/test-pipeline")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "test-pipeline"
    assert data["description"] == "Test pipeline"
    assert data["version"] == "1.0"
    assert data["enabled"] is True
    assert len(data["steps"]) == 2
    assert data["tags"] == ["test"]


def test_get_pipeline_not_found(test_client, mock_pipeline_registry):
    """Test 404 when pipeline doesn't exist."""
    mock_pipeline_registry.get_pipeline.side_effect = KeyError("not found")

    response = test_client.get("/api/v1/pipelines/nonexistent")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_execute_pipeline(test_client):
    """Test executing a pipeline."""
    response = test_client.post(
        "/api/v1/pipelines/test-pipeline/run",
        json={"inputs": {"param": "value"}}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["run_id"] == "test-run-123"
    assert data["pipeline_name"] == "test-pipeline"
    assert data["status"] == "success"
    assert len(data["steps"]) == 2


def test_execute_pipeline_without_inputs(test_client):
    """Test executing pipeline without input data."""
    response = test_client.post("/api/v1/pipelines/test-pipeline/run")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_execute_pipeline_not_found(test_client, mock_orchestrator):
    """Test 404 when executing non-existent pipeline."""
    mock_orchestrator.execute_pipeline.side_effect = KeyError("not found")

    response = test_client.post("/api/v1/pipelines/nonexistent/run")

    assert response.status_code == 404


def test_execute_pipeline_failure(test_client, mock_orchestrator):
    """Test 500 when pipeline execution fails."""
    mock_orchestrator.execute_pipeline.side_effect = Exception("Execution failed")

    response = test_client.post("/api/v1/pipelines/test-pipeline/run")

    assert response.status_code == 500
    assert "failed" in response.json()["detail"].lower()


def test_reload_pipeline(test_client):
    """Test reloading pipeline configuration."""
    response = test_client.post("/api/v1/pipelines/test-pipeline/reload")

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert "reloaded" in data["message"].lower()


def test_list_pipeline_runs_pipeline_not_found(test_client, mock_pipeline_registry):
    """Test listing runs for non-existent pipeline returns 404."""
    # Make get_pipeline raise KeyError for non-existent pipeline
    mock_pipeline_registry.get_pipeline.side_effect = KeyError("not found")

    response = test_client.get("/api/v1/pipelines/non-existent-pipeline/runs")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# UI MVP Tests - Enhanced Endpoints with Metadata and Schedules
# ============================================================================

def test_list_pipelines_with_metadata_and_schedules(
    mock_pipeline_registry, mock_scheduler_service, mock_orchestrator,
    mock_run_history, mock_task_manager
):
    """Test listing pipelines with full metadata and schedule information for UI."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    # Setup pipeline with schedule
    test_config = PipelineConfig(
        name="scheduled-pipeline",
        description="Pipeline with schedule",
        version="1.0",
        tags=["test", "scheduled"],
        enabled=True,
        schedule=ScheduleConfig(
            enabled=True,
            cron="0 */6 * * *",
            interval_seconds=None
        ),
        steps=[
            PipelineStepConfig(
                name="extract",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data"
            )
        ]
    )

    mock_pipeline_registry.list_pipelines.return_value = ["scheduled-pipeline"]
    mock_pipeline_registry.get_pipeline.return_value = test_config

    # Mock scheduler with next run time
    mock_scheduler_service.get_scheduled_pipelines.return_value = [
        {
            "pipeline_name": "scheduled-pipeline",
            "next_run_time": "2025-01-01T00:00:00Z",
            "schedule_type": "CronTrigger"
        }
    ]

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)
    response = client.get("/api/v1/pipelines")

    assert response.status_code == 200
    data = response.json()

    # Verify structure matches UI needs
    assert "pipelines" in data
    assert "count" in data
    assert data["count"] == 1
    assert isinstance(data["pipelines"], list)

    # Verify pipeline metadata
    pipeline = data["pipelines"][0]
    assert pipeline["name"] == "scheduled-pipeline"
    assert pipeline["description"] == "Pipeline with schedule"
    assert pipeline["enabled"] is True
    assert pipeline["tags"] == ["test", "scheduled"]

    # Verify schedule information for UI
    assert "schedule" in pipeline
    assert pipeline["schedule"] is not None
    assert pipeline["schedule"]["enabled"] is True
    assert pipeline["schedule"]["type"] == "cron"
    assert pipeline["schedule"]["expression"] == "0 */6 * * *"
    assert pipeline["schedule"]["next_run"] == "2025-01-01T00:00:00Z"

    app.dependency_overrides.clear()


def test_get_pipeline_with_schedule_details(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test getting pipeline details with schedule configuration for UI."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    # Setup pipeline with schedule
    test_config = PipelineConfig(
        name="test-pipeline",
        description="Test pipeline",
        version="1.0",
        tags=["test"],
        enabled=True,
        schedule=ScheduleConfig(
            enabled=True,
            cron=None,
            interval_seconds=3600
        ),
        steps=[
            PipelineStepConfig(
                name="extract",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data"
            )
        ]
    )

    mock_pipeline_registry.get_pipeline.return_value = test_config

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)
    response = client.get("/api/v1/pipelines/test-pipeline")

    assert response.status_code == 200
    data = response.json()

    # Verify schedule is included
    assert "schedule" in data
    assert data["schedule"] is not None
    assert data["schedule"]["enabled"] is True
    assert data["schedule"]["interval_seconds"] == 3600

    app.dependency_overrides.clear()


def test_get_pipeline_run_logs_success(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test retrieving logs for a pipeline run for UI log viewer."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    # Setup task with logs
    task_info = TaskInfo(
        run_id="test-run-123",
        pipeline_name="test-pipeline",
        status=TaskStatus.COMPLETED,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        logs=[
            {
                "timestamp": "2025-01-01T10:00:00Z",
                "level": "INFO",
                "logger": "flexlink.core",
                "message": "Pipeline started"
            },
            {
                "timestamp": "2025-01-01T10:00:05Z",
                "level": "INFO",
                "logger": "flexlink.core",
                "message": "Extracting data"
            },
            {
                "timestamp": "2025-01-01T10:00:10Z",
                "level": "INFO",
                "logger": "flexlink.core",
                "message": "Pipeline completed successfully"
            }
        ]
    )

    mock_task_manager.get_task_status.return_value = task_info

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)
    response = client.get("/api/v1/pipelines/test-pipeline/runs/test-run-123/logs")

    assert response.status_code == 200
    data = response.json()

    # Verify log response structure for UI
    assert data["run_id"] == "test-run-123"
    assert data["pipeline_name"] == "test-pipeline"
    assert "logs" in data
    assert "total_entries" in data
    assert data["total_entries"] == 3
    assert len(data["logs"]) == 3

    # Verify log entry structure
    log_entry = data["logs"][0]
    assert "timestamp" in log_entry
    assert "level" in log_entry
    assert "logger" in log_entry
    assert "message" in log_entry
    assert log_entry["level"] == "INFO"
    assert log_entry["message"] == "Pipeline started"

    app.dependency_overrides.clear()


def test_get_pipeline_run_logs_pagination(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test log pagination for UI infinite scroll."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    # Setup task with many logs
    logs = [
        {
            "timestamp": f"2025-01-01T10:00:{i:02d}Z",
            "level": "INFO",
            "logger": "flexlink.core",
            "message": f"Log entry {i}"
        }
        for i in range(100)
    ]

    task_info = TaskInfo(
        run_id="test-run-123",
        pipeline_name="test-pipeline",
        status=TaskStatus.RUNNING,
        started_at=datetime.now(UTC),
        logs=logs
    )

    mock_task_manager.get_task_status.return_value = task_info

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)

    # Test pagination
    response = client.get(
        "/api/v1/pipelines/test-pipeline/runs/test-run-123/logs?limit=10&offset=0"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total_entries"] == 100
    assert len(data["logs"]) == 10
    assert data["logs"][0]["message"] == "Log entry 0"

    # Test second page
    response = client.get(
        "/api/v1/pipelines/test-pipeline/runs/test-run-123/logs?limit=10&offset=10"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 10
    assert data["logs"][0]["message"] == "Log entry 10"

    app.dependency_overrides.clear()


def test_get_pipeline_run_logs_not_found(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test 404 when logs are not available."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    mock_task_manager.get_task_status.return_value = None

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)
    response = client.get("/api/v1/pipelines/test-pipeline/runs/nonexistent/logs")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_update_pipeline_schedule(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test updating pipeline schedule for UI schedule editor."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    test_config = PipelineConfig(
        name="test-pipeline",
        description="Test pipeline",
        version="1.0",
        tags=["test"],
        enabled=True,
        steps=[
            PipelineStepConfig(
                name="extract",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data"
            )
        ]
    )

    mock_pipeline_registry.get_pipeline.return_value = test_config

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)

    # Test enabling schedule with cron
    response = client.patch(
        "/api/v1/pipelines/test-pipeline/schedule",
        json={
            "enabled": True,
            "cron": "0 */6 * * *",
            "interval_seconds": None
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "updated" in data["message"].lower()
    mock_scheduler_service.update_pipeline_schedule.assert_called_once()

    app.dependency_overrides.clear()


def test_update_pipeline_schedule_disable(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test disabling pipeline schedule for UI."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    test_config = PipelineConfig(
        name="test-pipeline",
        description="Test pipeline",
        version="1.0",
        tags=["test"],
        enabled=True,
        steps=[
            PipelineStepConfig(
                name="extract",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data"
            )
        ]
    )

    mock_pipeline_registry.get_pipeline.return_value = test_config

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)

    # Test disabling schedule
    response = client.patch(
        "/api/v1/pipelines/test-pipeline/schedule",
        json={"enabled": False}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

    app.dependency_overrides.clear()


def test_update_pipeline_schedule_not_found(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test 404 when updating schedule for non-existent pipeline."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    mock_pipeline_registry.get_pipeline.side_effect = KeyError("not found")

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)

    response = client.patch(
        "/api/v1/pipelines/nonexistent/schedule",
        json={"enabled": False}
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

    app.dependency_overrides.clear()


def test_trigger_pipeline_now(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test immediate pipeline execution for UI run-now button."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )

    test_config = PipelineConfig(
        name="test-pipeline",
        description="Test pipeline",
        version="1.0",
        tags=["test"],
        enabled=True,
        steps=[
            PipelineStepConfig(
                name="extract",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data"
            )
        ]
    )

    mock_pipeline_registry.get_pipeline.return_value = test_config

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)

    response = client.post("/api/v1/pipelines/test-pipeline/schedule/run-now")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "triggered" in data["message"].lower()
    mock_scheduler_service.run_pipeline_now.assert_called_once_with("test-pipeline")

    app.dependency_overrides.clear()


def test_background_execution_and_status_polling(
    mock_pipeline_registry, mock_orchestrator, mock_run_history,
    mock_task_manager, mock_scheduler_service
):
    """Test background execution and status polling flow for UI."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_scheduler_service,
        get_task_manager,
    )
    from flexlink.models.pipeline import PipelineRunStatus

    test_config = PipelineConfig(
        name="test-pipeline",
        description="Test pipeline",
        version="1.0",
        tags=["test"],
        enabled=True,
        steps=[
            PipelineStepConfig(
                name="extract",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data"
            )
        ]
    )

    mock_pipeline_registry.get_pipeline.return_value = test_config

    # Mock background execution
    run_status = PipelineRunStatus(
        run_id="bg-run-456",
        pipeline_name="test-pipeline",
        status=TaskStatus.QUEUED
    )

    # First call returns queued status
    task_info_queued = TaskInfo(
        run_id="bg-run-456",
        pipeline_name="test-pipeline",
        status=TaskStatus.QUEUED
    )

    # Second call returns running status
    task_info_running = TaskInfo(
        run_id="bg-run-456",
        pipeline_name="test-pipeline",
        status=TaskStatus.RUNNING,
        started_at=datetime.now(UTC)
    )

    mock_task_manager.submit_task.return_value = "bg-run-456"
    mock_task_manager.get_task_status.side_effect = [task_info_queued, task_info_running]

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager
    app.dependency_overrides[get_scheduler_service] = lambda: mock_scheduler_service

    client = TestClient(app)

    # Start background execution
    response = client.post(
        "/api/v1/pipelines/test-pipeline/run?background=true"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == "bg-run-456"
    assert data["status"] == "queued"

    # Poll status - first time (queued)
    response = client.get("/api/v1/pipelines/runs/bg-run-456")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"

    # Poll status - second time (running)
    response = client.get("/api/v1/pipelines/runs/bg-run-456")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "started_at" in data

    app.dependency_overrides.clear()
