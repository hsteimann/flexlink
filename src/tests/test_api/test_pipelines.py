"""Tests for pipeline API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock

from flexlink.main import app
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.models.pipeline import (
    PipelineConfig,
    PipelineStepConfig,
    StepType,
    PipelineExecutionResult,
    ExecutionMetadata,
    StepResult
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
    from datetime import datetime, timezone

    result = PipelineExecutionResult(
        run_id="test-run-123",
        pipeline_name="test-pipeline",
        status="success",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
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
def test_client(mock_pipeline_registry, mock_orchestrator):
    """Test client with mocked dependencies."""
    from flexlink.api.pipelines import get_pipeline_registry, get_orchestrator

    # Override dependencies
    app.dependency_overrides[get_pipeline_registry] = lambda: mock_pipeline_registry
    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

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
