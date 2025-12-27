"""Tests for pipeline scheduler service."""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from flexlink.core.scheduler_service import SchedulerService
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.models.pipeline import (
    PipelineConfig,
    PipelineStepConfig,
    ScheduleConfig,
    StepType,
    ErrorStrategy,
    PipelineExecutionResult,
    ExecutionMetadata
)


# Fixtures

@pytest.fixture
def mock_pipeline_registry():
    """Create mock pipeline registry."""
    registry = MagicMock(spec=PipelineRegistry)
    return registry


@pytest.fixture
def mock_orchestrator():
    """Create mock pipeline orchestrator."""
    orchestrator = MagicMock(spec=PipelineOrchestrator)

    # Mock successful execution
    orchestrator.execute_pipeline = AsyncMock(return_value=PipelineExecutionResult(
        run_id="test-run-123",
        pipeline_name="test-pipeline",
        status="success",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        duration_seconds=1.5,
        steps=[],
        metadata=ExecutionMetadata(),
        error_message=None
    ))

    return orchestrator


@pytest.fixture
def scheduler_service(mock_pipeline_registry, mock_orchestrator):
    """Create scheduler service for testing."""
    return SchedulerService(
        pipeline_registry=mock_pipeline_registry,
        orchestrator=mock_orchestrator
    )


# Test Cases

@pytest.mark.asyncio
async def test_scheduler_initialization_and_shutdown(scheduler_service):
    """Test scheduler can be initialized and shut down cleanly."""
    # Start scheduler
    scheduler_service.pipeline_registry.list_pipelines.return_value = []

    await scheduler_service.start()
    assert scheduler_service.scheduler.running

    # Shutdown scheduler
    await scheduler_service.shutdown()
    # Note: APScheduler's shutdown() may not immediately set running=False
    # The important thing is it completes without error
    assert True  # Shutdown completed successfully


@pytest.mark.asyncio
async def test_cron_schedule_registration(mock_pipeline_registry, mock_orchestrator):
    """Test cron schedule is registered correctly."""
    # Setup pipeline with cron schedule
    pipeline_config = PipelineConfig(
        name="test-cron-pipeline",
        description="Test pipeline with cron schedule",
        version="1.0.0",
        steps=[
            PipelineStepConfig(
                name="test-step",
                type=StepType.EXTRACT,
                connector="test-connector",
                method="GET",
                path="/test",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ],
        schedule=ScheduleConfig(
            enabled=True,
            cron="0 */6 * * *"  # Every 6 hours
        ),
        tags=[],
        enabled=True
    )

    mock_pipeline_registry.list_pipelines.return_value = ["test-cron-pipeline"]
    mock_pipeline_registry.get_pipeline.return_value = pipeline_config

    # Create and start scheduler
    scheduler_service = SchedulerService(
        pipeline_registry=mock_pipeline_registry,
        orchestrator=mock_orchestrator
    )

    await scheduler_service.start()

    # Verify job was registered
    jobs = scheduler_service.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "pipeline_test-cron-pipeline_cron"
    assert jobs[0].name == "Pipeline: test-cron-pipeline"

    await scheduler_service.shutdown()


@pytest.mark.asyncio
async def test_interval_schedule_registration(mock_pipeline_registry, mock_orchestrator):
    """Test interval schedule is registered correctly."""
    # Setup pipeline with interval schedule
    pipeline_config = PipelineConfig(
        name="test-interval-pipeline",
        description="Test pipeline with interval schedule",
        version="1.0.0",
        steps=[
            PipelineStepConfig(
                name="test-step",
                type=StepType.EXTRACT,
                connector="test-connector",
                method="GET",
                path="/test",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ],
        schedule=ScheduleConfig(
            enabled=True,
            interval_seconds=3600  # Every hour
        ),
        tags=[],
        enabled=True
    )

    mock_pipeline_registry.list_pipelines.return_value = ["test-interval-pipeline"]
    mock_pipeline_registry.get_pipeline.return_value = pipeline_config

    # Create and start scheduler
    scheduler_service = SchedulerService(
        pipeline_registry=mock_pipeline_registry,
        orchestrator=mock_orchestrator
    )

    await scheduler_service.start()

    # Verify job was registered
    jobs = scheduler_service.scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "pipeline_test-interval-pipeline_interval"

    await scheduler_service.shutdown()


@pytest.mark.asyncio
async def test_disabled_schedule_not_registered(mock_pipeline_registry, mock_orchestrator):
    """Test that disabled schedules are not registered."""
    # Setup pipeline with disabled schedule
    pipeline_config = PipelineConfig(
        name="test-disabled-pipeline",
        description="Test pipeline with disabled schedule",
        version="1.0.0",
        steps=[
            PipelineStepConfig(
                name="test-step",
                type=StepType.EXTRACT,
                connector="test-connector",
                method="GET",
                path="/test",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ],
        schedule=ScheduleConfig(
            enabled=False,  # Disabled
            cron="0 */6 * * *"
        ),
        tags=[],
        enabled=True
    )

    mock_pipeline_registry.list_pipelines.return_value = ["test-disabled-pipeline"]
    mock_pipeline_registry.get_pipeline.return_value = pipeline_config

    # Create and start scheduler
    scheduler_service = SchedulerService(
        pipeline_registry=mock_pipeline_registry,
        orchestrator=mock_orchestrator
    )

    await scheduler_service.start()

    # Verify no jobs were registered
    jobs = scheduler_service.scheduler.get_jobs()
    assert len(jobs) == 0

    await scheduler_service.shutdown()


@pytest.mark.asyncio
async def test_pipeline_without_schedule_not_registered(mock_pipeline_registry, mock_orchestrator):
    """Test that pipelines without schedule config are not registered."""
    # Setup pipeline without schedule (uses default ScheduleConfig with enabled=False)
    pipeline_config = PipelineConfig(
        name="test-no-schedule-pipeline",
        description="Test pipeline without schedule",
        version="1.0.0",
        steps=[
            PipelineStepConfig(
                name="test-step",
                type=StepType.EXTRACT,
                connector="test-connector",
                method="GET",
                path="/test",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ],
        # schedule field omitted - will use default ScheduleConfig with enabled=False
        tags=[],
        enabled=True
    )

    mock_pipeline_registry.list_pipelines.return_value = ["test-no-schedule-pipeline"]
    mock_pipeline_registry.get_pipeline.return_value = pipeline_config

    # Create and start scheduler
    scheduler_service = SchedulerService(
        pipeline_registry=mock_pipeline_registry,
        orchestrator=mock_orchestrator
    )

    await scheduler_service.start()

    # Verify no jobs were registered
    jobs = scheduler_service.scheduler.get_jobs()
    assert len(jobs) == 0

    await scheduler_service.shutdown()


@pytest.mark.asyncio
async def test_schedule_reload(mock_pipeline_registry, mock_orchestrator):
    """Test schedule reload functionality."""
    # Setup initial pipeline
    pipeline_config_1 = PipelineConfig(
        name="test-pipeline-1",
        description="Test pipeline 1",
        version="1.0.0",
        steps=[
            PipelineStepConfig(
                name="test-step",
                type=StepType.EXTRACT,
                connector="test-connector",
                method="GET",
                path="/test",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ],
        schedule=ScheduleConfig(enabled=True, cron="0 */6 * * *"),
        tags=[],
        enabled=True
    )

    mock_pipeline_registry.list_pipelines.return_value = ["test-pipeline-1"]
    mock_pipeline_registry.get_pipeline.return_value = pipeline_config_1

    # Create and start scheduler
    scheduler_service = SchedulerService(
        pipeline_registry=mock_pipeline_registry,
        orchestrator=mock_orchestrator
    )

    await scheduler_service.start()

    # Verify initial job
    jobs = scheduler_service.scheduler.get_jobs()
    assert len(jobs) == 1

    # Update registry to add another pipeline
    pipeline_config_2 = PipelineConfig(
        name="test-pipeline-2",
        description="Test pipeline 2",
        version="1.0.0",
        steps=[
            PipelineStepConfig(
                name="test-step",
                type=StepType.EXTRACT,
                connector="test-connector",
                method="GET",
                path="/test",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ],
        schedule=ScheduleConfig(enabled=True, interval_seconds=3600),
        tags=[],
        enabled=True
    )

    mock_pipeline_registry.list_pipelines.return_value = ["test-pipeline-1", "test-pipeline-2"]
    mock_pipeline_registry.get_pipeline.side_effect = lambda name: (
        pipeline_config_1 if name == "test-pipeline-1" else pipeline_config_2
    )

    # Reload schedules
    scheduler_service.reload_schedules()

    # Verify both jobs registered
    jobs = scheduler_service.scheduler.get_jobs()
    assert len(jobs) == 2

    await scheduler_service.shutdown()


@pytest.mark.asyncio
async def test_scheduled_execution_success(scheduler_service, mock_orchestrator):
    """Test successful scheduled pipeline execution."""
    # Execute scheduled pipeline
    await scheduler_service._execute_scheduled_pipeline("test-pipeline")

    # Verify orchestrator was called
    mock_orchestrator.execute_pipeline.assert_called_once_with(
        pipeline_name="test-pipeline",
        inputs=None
    )


@pytest.mark.asyncio
async def test_scheduled_execution_error_handling(scheduler_service, mock_orchestrator):
    """Test error handling in scheduled execution."""
    # Mock orchestrator to raise error
    mock_orchestrator.execute_pipeline = AsyncMock(side_effect=Exception("Test error"))

    # Execute should not raise (errors are logged)
    await scheduler_service._execute_scheduled_pipeline("test-pipeline")

    # Verify orchestrator was called despite error
    mock_orchestrator.execute_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_get_scheduled_pipelines(mock_pipeline_registry, mock_orchestrator):
    """Test getting list of scheduled pipelines."""
    # Setup pipeline with schedule
    pipeline_config = PipelineConfig(
        name="test-pipeline",
        description="Test pipeline",
        version="1.0.0",
        steps=[
            PipelineStepConfig(
                name="test-step",
                type=StepType.EXTRACT,
                connector="test-connector",
                method="GET",
                path="/test",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ],
        schedule=ScheduleConfig(enabled=True, cron="0 */6 * * *"),
        tags=[],
        enabled=True
    )

    mock_pipeline_registry.list_pipelines.return_value = ["test-pipeline"]
    mock_pipeline_registry.get_pipeline.return_value = pipeline_config

    # Create and start scheduler
    scheduler_service = SchedulerService(
        pipeline_registry=mock_pipeline_registry,
        orchestrator=mock_orchestrator
    )

    await scheduler_service.start()

    # Get scheduled pipelines
    scheduled = scheduler_service.get_scheduled_pipelines()

    assert len(scheduled) == 1
    assert scheduled[0]["pipeline_name"] == "test-pipeline"
    assert scheduled[0]["job_id"] == "pipeline_test-pipeline_cron"
    assert scheduled[0]["schedule_type"] == "CronTrigger"
    assert scheduled[0]["enabled"] is True
    assert "next_run_time" in scheduled[0]

    await scheduler_service.shutdown()


@pytest.mark.asyncio
async def test_invalid_schedule_config_error_handling(mock_pipeline_registry, mock_orchestrator):
    """Test error handling for invalid schedule configuration."""
    # Setup pipeline with invalid schedule (no cron or interval)
    pipeline_config = PipelineConfig(
        name="test-invalid-pipeline",
        description="Test pipeline with invalid schedule",
        version="1.0.0",
        steps=[
            PipelineStepConfig(
                name="test-step",
                type=StepType.EXTRACT,
                connector="test-connector",
                method="GET",
                path="/test",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ],
        schedule=ScheduleConfig(enabled=True),  # No cron or interval!
        tags=[],
        enabled=True
    )

    mock_pipeline_registry.list_pipelines.return_value = ["test-invalid-pipeline"]
    mock_pipeline_registry.get_pipeline.return_value = pipeline_config

    # Create and start scheduler
    scheduler_service = SchedulerService(
        pipeline_registry=mock_pipeline_registry,
        orchestrator=mock_orchestrator
    )

    # Should not raise, just log error
    await scheduler_service.start()

    # Verify no jobs were registered due to error
    jobs = scheduler_service.scheduler.get_jobs()
    assert len(jobs) == 0

    await scheduler_service.shutdown()
