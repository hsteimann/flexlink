"""Tests for TaskManager background execution."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from flexlink.core.task_manager import TaskManager, TaskInfo
from flexlink.models.pipeline import (
    PipelineExecutionResult,
    ExecutionMetadata,
    StepResult,
    TaskStatus,
)


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = AsyncMock()
    # Create a successful result
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
            )
        ],
        metadata=ExecutionMetadata(
            records_extracted=100,
            records_loaded=100
        )
    )
    orchestrator.execute_pipeline.return_value = result
    return orchestrator


@pytest.fixture
def mock_run_history():
    """Create a mock run history storage."""
    run_history = AsyncMock()
    return run_history


@pytest.fixture
def task_manager(mock_run_history):
    """Create a TaskManager instance with mock run_history."""
    return TaskManager(run_history=mock_run_history)


@pytest.mark.asyncio
async def test_submit_task_returns_run_id(task_manager, mock_orchestrator):
    """Test that submitting a task returns a unique run_id."""
    run_id = task_manager.submit_task(
        pipeline_name="test-pipeline",
        orchestrator=mock_orchestrator,
        inputs={"param": "value"}
    )

    assert run_id is not None
    assert isinstance(run_id, str)
    assert len(run_id) > 0

    # Verify task is stored
    task_info = task_manager.get_task_status(run_id)
    assert task_info is not None
    assert task_info.pipeline_name == "test-pipeline"
    assert task_info.status == TaskStatus.QUEUED


@pytest.mark.asyncio
async def test_get_task_status_running(task_manager, mock_orchestrator):
    """Test getting status of a running task."""
    # Make orchestrator take some time
    async def slow_execute(*args, **kwargs):
        await asyncio.sleep(0.1)
        return mock_orchestrator.execute_pipeline.return_value

    mock_orchestrator.execute_pipeline.side_effect = slow_execute

    run_id = task_manager.submit_task(
        pipeline_name="test-pipeline",
        orchestrator=mock_orchestrator
    )

    # Give task a moment to start
    await asyncio.sleep(0.05)

    task_info = task_manager.get_task_status(run_id)
    assert task_info is not None
    # Status should be either queued or running
    assert task_info.status in [TaskStatus.QUEUED, TaskStatus.RUNNING]


@pytest.mark.asyncio
async def test_get_task_status_completed(task_manager, mock_orchestrator):
    """Test getting status of a completed task."""
    run_id = task_manager.submit_task(
        pipeline_name="test-pipeline",
        orchestrator=mock_orchestrator
    )

    # Wait for task to complete
    await asyncio.sleep(0.1)

    task_info = task_manager.get_task_status(run_id)
    assert task_info is not None
    assert task_info.status == TaskStatus.COMPLETED
    assert task_info.result is not None
    assert task_info.result.status == "success"
    assert task_info.started_at is not None
    assert task_info.completed_at is not None


@pytest.mark.asyncio
async def test_background_execution_success(task_manager, mock_orchestrator, mock_run_history):
    """Test successful background pipeline execution."""
    run_id = task_manager.submit_task(
        pipeline_name="test-pipeline",
        orchestrator=mock_orchestrator,
        inputs={"test": "data"}
    )

    # Wait for execution
    await asyncio.sleep(0.1)

    # Verify orchestrator was called
    mock_orchestrator.execute_pipeline.assert_called_once_with(
        pipeline_name="test-pipeline",
        inputs={"test": "data"}
    )

    # Verify result was saved to history
    mock_run_history.save_run.assert_called_once()
    saved_result = mock_run_history.save_run.call_args[0][0]
    assert saved_result.pipeline_name == "test-pipeline"
    assert saved_result.status == "success"


@pytest.mark.asyncio
async def test_background_execution_failure(task_manager, mock_orchestrator):
    """Test background execution with pipeline failure."""
    # Make orchestrator raise an exception
    mock_orchestrator.execute_pipeline.side_effect = Exception("Pipeline failed")

    run_id = task_manager.submit_task(
        pipeline_name="test-pipeline",
        orchestrator=mock_orchestrator
    )

    # Wait for execution
    await asyncio.sleep(0.1)

    task_info = task_manager.get_task_status(run_id)
    assert task_info is not None
    assert task_info.status == TaskStatus.FAILED
    assert task_info.error == "Pipeline failed"
    assert task_info.completed_at is not None


@pytest.mark.asyncio
async def test_background_execution_without_run_history(mock_orchestrator):
    """Test that background execution works without run_history."""
    task_manager = TaskManager(run_history=None)

    run_id = task_manager.submit_task(
        pipeline_name="test-pipeline",
        orchestrator=mock_orchestrator
    )

    # Wait for execution
    await asyncio.sleep(0.1)

    task_info = task_manager.get_task_status(run_id)
    assert task_info is not None
    assert task_info.status == TaskStatus.COMPLETED
    # No exception should be raised even without run_history


def test_cleanup_completed_tasks(task_manager):
    """Test cleanup of old completed tasks."""
    # Create a task info directly (without async submission)
    task_info = TaskInfo(
        run_id="old-task-123",
        pipeline_name="test-pipeline",
        status=TaskStatus.COMPLETED,
    )
    task_info.completed_at = datetime.now(timezone.utc).replace(year=2020)

    # Add to task manager
    task_manager._tasks["old-task-123"] = task_info

    # Cleanup tasks older than 1 hour
    removed = task_manager.cleanup_completed_tasks(older_than_hours=1)

    assert removed == 1
    assert task_manager.get_task_status("old-task-123") is None


def test_cleanup_completed_tasks_no_old_tasks(task_manager):
    """Test cleanup when there are no old tasks."""
    removed = task_manager.cleanup_completed_tasks(older_than_hours=24)
    assert removed == 0


@pytest.mark.asyncio
async def test_multiple_concurrent_tasks(task_manager, mock_orchestrator):
    """Test submitting multiple tasks concurrently."""
    run_ids = []

    for i in range(5):
        run_id = task_manager.submit_task(
            pipeline_name=f"pipeline-{i}",
            orchestrator=mock_orchestrator
        )
        run_ids.append(run_id)

    # Wait for all to complete
    await asyncio.sleep(0.2)

    # Verify all tasks completed
    for run_id in run_ids:
        task_info = task_manager.get_task_status(run_id)
        assert task_info is not None
        assert task_info.status == TaskStatus.COMPLETED

    # Verify all run IDs are unique
    assert len(set(run_ids)) == 5


@pytest.mark.asyncio
async def test_get_task_status_not_found(task_manager):
    """Test getting status for non-existent task."""
    task_info = task_manager.get_task_status("non-existent-id")
    assert task_info is None


@pytest.mark.asyncio
async def test_task_info_dataclass():
    """Test TaskInfo dataclass structure."""
    task_info = TaskInfo(
        run_id="test-123",
        pipeline_name="test-pipeline",
        status="queued"
    )

    assert task_info.run_id == "test-123"
    assert task_info.pipeline_name == "test-pipeline"
    assert task_info.status == "queued"
    assert task_info.started_at is None
    assert task_info.completed_at is None
    assert task_info.task is None
    assert task_info.result is None
    assert task_info.error is None
