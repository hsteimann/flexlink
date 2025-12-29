"""Tests for pipeline API endpoints."""

from datetime import UTC
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.run_history import RunHistoryStorage
from flexlink.main import app
from flexlink.models.pipeline import (
    ExecutionMetadata,
    PipelineConfig,
    PipelineExecutionResult,
    PipelineStepConfig,
    StepResult,
    StepType,
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
    from flexlink.core.task_manager import TaskManager

    task_manager = Mock(spec=TaskManager)
    return task_manager


@pytest.fixture
def test_client(
    mock_pipeline_registry, mock_orchestrator, mock_run_history, mock_task_manager
):
    """Test client with mocked dependencies."""
    from flexlink.api.pipelines import (
        get_orchestrator,
        get_pipeline_registry,
        get_run_history,
        get_task_manager,
    )

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
    app.dependency_overrides[get_run_history] = lambda: mock_run_history
    app.dependency_overrides[get_task_manager] = lambda: mock_task_manager

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


def test_list_pipelines(test_client):
    """Test listing all pipelines."""
    response = test_client.get("/api/v1/pipelines")

    assert response.status_code == 200
    data = response.json()

    assert "pipelines" in data
    assert "count" in data
    assert data["count"] == 1
    assert "test-pipeline" in data["pipelines"]


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
