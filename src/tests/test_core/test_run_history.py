"""Tests for RunHistoryStorage database operations."""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from flexlink.core.run_history import RunHistoryStorage
from flexlink.models.pipeline import (
    PipelineExecutionResult,
    ExecutionMetadata,
    StepResult,
    PipelineRunHistoryRecord
)


@pytest.fixture
async def run_history(tmp_path):
    """Create a RunHistoryStorage instance with temporary database."""
    db_path = tmp_path / "test_history.db"
    storage = RunHistoryStorage(db_path=str(db_path))
    await storage.initialize()
    return storage


@pytest.fixture
def sample_result():
    """Create a sample pipeline execution result."""
    now = datetime.now(timezone.utc)
    return PipelineExecutionResult(
        run_id="test-run-123",
        pipeline_name="test-pipeline",
        status="success",
        started_at=now - timedelta(seconds=10),
        completed_at=now,
        duration_seconds=10.0,
        steps=[
            StepResult(
                step_name="extract",
                status="success",
                duration_seconds=3.0,
                records_processed=100
            ),
            StepResult(
                step_name="load",
                status="success",
                duration_seconds=7.0,
                records_processed=100
            )
        ],
        metadata=ExecutionMetadata(
            records_extracted=100,
            records_transformed=100,
            records_loaded=100,
            validation_errors=0
        ),
        error_message=None
    )


@pytest.mark.asyncio
async def test_initialize_creates_database(tmp_path):
    """Test that initialize creates the database file and tables."""
    db_path = tmp_path / "test.db"
    storage = RunHistoryStorage(db_path=str(db_path))

    assert not db_path.exists()

    await storage.initialize()

    assert db_path.exists()
    assert storage._initialized is True


@pytest.mark.asyncio
async def test_save_and_retrieve_run(run_history, sample_result):
    """Test saving and retrieving a pipeline run."""
    # Save the run
    await run_history.save_run(sample_result, triggered_by="manual")

    # Retrieve it
    retrieved = await run_history.get_run(sample_result.run_id)

    assert retrieved is not None
    assert retrieved.run_id == sample_result.run_id
    assert retrieved.pipeline_name == sample_result.pipeline_name
    assert retrieved.status == sample_result.status
    assert retrieved.duration_seconds == sample_result.duration_seconds
    assert retrieved.records_extracted == 100
    assert retrieved.records_loaded == 100
    assert retrieved.triggered_by == "manual"


@pytest.mark.asyncio
async def test_get_run_not_found(run_history):
    """Test retrieving a non-existent run."""
    result = await run_history.get_run("non-existent-id")
    assert result is None


@pytest.mark.asyncio
async def test_save_scheduled_run(run_history, sample_result):
    """Test saving a scheduled pipeline run."""
    await run_history.save_run(sample_result, triggered_by="schedule")

    retrieved = await run_history.get_run(sample_result.run_id)
    assert retrieved is not None
    assert retrieved.triggered_by == "schedule"


@pytest.mark.asyncio
async def test_list_runs_pagination(run_history):
    """Test listing runs with pagination."""
    # Create multiple runs
    now = datetime.now(timezone.utc)

    for i in range(10):
        result = PipelineExecutionResult(
            run_id=f"run-{i}",
            pipeline_name="test-pipeline",
            status="success",
            started_at=now - timedelta(minutes=10-i),
            completed_at=now - timedelta(minutes=10-i-1),
            duration_seconds=60.0,
            steps=[],
            metadata=ExecutionMetadata()
        )
        await run_history.save_run(result)

    # Test pagination
    runs_page1 = await run_history.list_runs(limit=5, offset=0)
    assert len(runs_page1) == 5

    runs_page2 = await run_history.list_runs(limit=5, offset=5)
    assert len(runs_page2) == 5

    # Verify they're different runs
    page1_ids = {run.run_id for run in runs_page1}
    page2_ids = {run.run_id for run in runs_page2}
    assert len(page1_ids.intersection(page2_ids)) == 0


@pytest.mark.asyncio
async def test_list_runs_filter_by_pipeline(run_history):
    """Test filtering runs by pipeline name."""
    now = datetime.now(timezone.utc)

    # Create runs for different pipelines
    for pipeline in ["pipeline-a", "pipeline-b"]:
        for i in range(3):
            result = PipelineExecutionResult(
                run_id=f"{pipeline}-{i}",
                pipeline_name=pipeline,
                status="success",
                started_at=now - timedelta(minutes=i),
                completed_at=now,
                duration_seconds=60.0,
                steps=[],
                metadata=ExecutionMetadata()
            )
            await run_history.save_run(result)

    # Filter by pipeline name
    pipeline_a_runs = await run_history.list_runs(pipeline_name="pipeline-a")
    assert len(pipeline_a_runs) == 3
    assert all(run.pipeline_name == "pipeline-a" for run in pipeline_a_runs)

    pipeline_b_runs = await run_history.list_runs(pipeline_name="pipeline-b")
    assert len(pipeline_b_runs) == 3
    assert all(run.pipeline_name == "pipeline-b" for run in pipeline_b_runs)


@pytest.mark.asyncio
async def test_list_runs_ordered_by_started_at(run_history):
    """Test that runs are ordered by started_at descending."""
    now = datetime.now(timezone.utc)

    # Create runs with different start times
    for i in range(5):
        result = PipelineExecutionResult(
            run_id=f"run-{i}",
            pipeline_name="test-pipeline",
            status="success",
            started_at=now - timedelta(hours=i),
            completed_at=now,
            duration_seconds=60.0,
            steps=[],
            metadata=ExecutionMetadata()
        )
        await run_history.save_run(result)

    runs = await run_history.list_runs(limit=10)

    # Most recent should be first
    assert runs[0].run_id == "run-0"
    assert runs[1].run_id == "run-1"
    assert runs[4].run_id == "run-4"


@pytest.mark.asyncio
async def test_get_statistics(run_history):
    """Test calculating pipeline statistics."""
    now = datetime.now(timezone.utc)

    # Create successful runs
    for i in range(3):
        result = PipelineExecutionResult(
            run_id=f"success-{i}",
            pipeline_name="test-pipeline",
            status="success",
            started_at=now,
            completed_at=now + timedelta(seconds=10),
            duration_seconds=10.0,
            steps=[],
            metadata=ExecutionMetadata(
                records_extracted=100,
                records_loaded=100
            )
        )
        await run_history.save_run(result)

    # Create failed run
    failed_result = PipelineExecutionResult(
        run_id="failed-1",
        pipeline_name="test-pipeline",
        status="failed",
        started_at=now,
        completed_at=now + timedelta(seconds=5),
        duration_seconds=5.0,
        steps=[],
        metadata=ExecutionMetadata(),
        error_message="Pipeline failed"
    )
    await run_history.save_run(failed_result)

    # Get statistics
    stats = await run_history.get_statistics("test-pipeline")

    assert stats["pipeline_name"] == "test-pipeline"
    assert stats["total_runs"] == 4
    assert stats["successful_runs"] == 3
    assert stats["success_rate"] == 75.0
    assert stats["avg_duration_seconds"] == 8.75  # (10+10+10+5)/4
    assert stats["total_records_extracted"] == 300
    assert stats["total_records_loaded"] == 300


@pytest.mark.asyncio
async def test_get_statistics_no_runs(run_history):
    """Test statistics for pipeline with no runs."""
    stats = await run_history.get_statistics("non-existent-pipeline")

    assert stats["total_runs"] == 0
    assert stats["successful_runs"] == 0
    assert stats["success_rate"] == 0.0
    assert stats["avg_duration_seconds"] == 0.0


@pytest.mark.asyncio
async def test_delete_old_runs(run_history):
    """Test deleting old runs."""
    now = datetime.now(timezone.utc)

    # Create old runs
    for i in range(3):
        old_result = PipelineExecutionResult(
            run_id=f"old-{i}",
            pipeline_name="test-pipeline",
            status="success",
            started_at=now - timedelta(days=40),
            completed_at=now - timedelta(days=40),
            duration_seconds=10.0,
            steps=[],
            metadata=ExecutionMetadata()
        )
        await run_history.save_run(old_result)

    # Create recent run
    recent_result = PipelineExecutionResult(
        run_id="recent-1",
        pipeline_name="test-pipeline",
        status="success",
        started_at=now - timedelta(days=5),
        completed_at=now - timedelta(days=5),
        duration_seconds=10.0,
        steps=[],
        metadata=ExecutionMetadata()
    )
    await run_history.save_run(recent_result)

    # Delete runs older than 30 days
    deleted_count = await run_history.delete_old_runs(older_than_days=30)

    assert deleted_count == 3

    # Verify recent run still exists
    recent = await run_history.get_run("recent-1")
    assert recent is not None

    # Verify old runs are gone
    old = await run_history.get_run("old-0")
    assert old is None


@pytest.mark.asyncio
async def test_delete_old_runs_no_old_runs(run_history):
    """Test deleting when there are no old runs."""
    now = datetime.now(timezone.utc)

    result = PipelineExecutionResult(
        run_id="recent-1",
        pipeline_name="test-pipeline",
        status="success",
        started_at=now - timedelta(days=5),
        completed_at=now,
        duration_seconds=10.0,
        steps=[],
        metadata=ExecutionMetadata()
    )
    await run_history.save_run(result)

    deleted_count = await run_history.delete_old_runs(older_than_days=30)
    assert deleted_count == 0


@pytest.mark.asyncio
async def test_save_run_with_error_message(run_history):
    """Test saving a failed run with error message."""
    now = datetime.now(timezone.utc)
    result = PipelineExecutionResult(
        run_id="failed-run",
        pipeline_name="test-pipeline",
        status="failed",
        started_at=now,
        completed_at=now + timedelta(seconds=2),
        duration_seconds=2.0,
        steps=[],
        metadata=ExecutionMetadata(),
        error_message="Database connection failed"
    )

    await run_history.save_run(result)

    retrieved = await run_history.get_run("failed-run")
    assert retrieved is not None
    assert retrieved.status == "failed"
    assert retrieved.error_message == "Database connection failed"


@pytest.mark.asyncio
async def test_concurrent_writes(run_history):
    """Test concurrent write operations."""
    import asyncio

    now = datetime.now(timezone.utc)

    async def save_run(i):
        result = PipelineExecutionResult(
            run_id=f"concurrent-{i}",
            pipeline_name="test-pipeline",
            status="success",
            started_at=now,
            completed_at=now,
            duration_seconds=1.0,
            steps=[],
            metadata=ExecutionMetadata()
        )
        await run_history.save_run(result)

    # Execute multiple saves concurrently
    await asyncio.gather(*[save_run(i) for i in range(10)])

    # Verify all were saved
    runs = await run_history.list_runs(limit=20)
    assert len(runs) == 10
