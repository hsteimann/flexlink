"""Task Manager for background pipeline execution.

This module provides the TaskManager class for managing background pipeline
executions using asyncio tasks. It tracks task status in-memory and provides
status polling capabilities for running and completed tasks.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from flexlink.models.pipeline import PipelineExecutionResult, TaskStatus

if TYPE_CHECKING:
    from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
    from flexlink.core.run_history import RunHistoryStorage

logger = logging.getLogger(__name__)


class MemoryLogHandler(logging.Handler):
    """Captures log records to in-memory list."""
    def __init__(self, log_list: list[dict[str, Any]]):
        super().__init__()
        self.log_list = log_list

    def emit(self, record: logging.LogRecord) -> None:
        self.log_list.append({
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        })


@dataclass
class TaskInfo:
    """Information about a background pipeline task."""

    run_id: str
    pipeline_name: str
    status: TaskStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    task: asyncio.Task[None] | None = None
    result: PipelineExecutionResult | None = None
    error: str | None = None
    logs: list[dict[str, Any]] = field(default_factory=list)


class TaskManager:
    """Manages background pipeline execution tasks.

    The TaskManager maintains an in-memory registry of active and recently
    completed pipeline execution tasks. It provides methods for submitting
    pipelines for background execution, polling task status, and cleaning up
    completed tasks.

    Attributes:
        _tasks: Dictionary mapping run_id to TaskInfo objects
        run_history: Optional RunHistoryStorage for persisting completed runs
    """

    def __init__(self, run_history: "RunHistoryStorage | None" = None):
        """Initialize the TaskManager with an empty task registry.

        Args:
            run_history: Optional RunHistoryStorage for persisting execution history
        """
        self._tasks: dict[str, TaskInfo] = {}
        self.run_history = run_history
        logger.info("TaskManager initialized")

    def submit_task(
        self,
        pipeline_name: str,
        orchestrator: "PipelineOrchestrator",
        inputs: dict[str, Any] | None = None,
    ) -> str:
        """Submit a pipeline for background execution.

        Creates a new background task for pipeline execution and returns
        a unique run_id that can be used to poll the task status.

        Args:
            pipeline_name: Name of the pipeline to execute
            orchestrator: PipelineOrchestrator instance for execution
            inputs: Optional inputs to pass to the pipeline

        Returns:
            Unique run_id string for the submitted task
        """
        run_id = str(uuid.uuid4())

        logger.info(
            f"Submitting background task for pipeline '{pipeline_name}' with run_id {run_id}"
        )

        # Create task info with queued status
        task_info = TaskInfo(
            run_id=run_id,
            pipeline_name=pipeline_name,
            status=TaskStatus.QUEUED,
        )

        # Store task info
        self._tasks[run_id] = task_info

        # Create background task - this runs without awaiting
        task = asyncio.create_task(
            self._execute_pipeline_background(run_id, pipeline_name, orchestrator, inputs)
        )
        task_info.task = task

        return run_id

    async def _execute_pipeline_background(
        self,
        run_id: str,
        pipeline_name: str,
        orchestrator: "PipelineOrchestrator",
        inputs: dict[str, Any] | None,
    ) -> None:
        """Execute pipeline in background with error handling.

        This is the wrapper function that actually executes the pipeline
        asynchronously and updates the task status and result.

        Args:
            run_id: Unique identifier for this execution
            pipeline_name: Name of the pipeline to execute
            orchestrator: PipelineOrchestrator instance
            inputs: Optional inputs for the pipeline
        """
        task_info = self._tasks.get(run_id)
        if not task_info:
            logger.warning(f"Task info not found for run_id {run_id}")
            return

        # Setup log capture
        log_handler = MemoryLogHandler(task_info.logs)
        pipeline_logger = logging.getLogger("flexlink")
        pipeline_logger.addHandler(log_handler)

        try:
            # Update status to running
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = datetime.now(UTC)
            logger.info(
                f"Starting background execution of pipeline '{pipeline_name}' "
                f"(run_id={run_id})"
            )

            # Execute the pipeline
            result = await orchestrator.execute_pipeline(
                pipeline_name=pipeline_name, inputs=inputs
            )

            # Update task with result
            task_info.status = TaskStatus.COMPLETED
            task_info.completed_at = datetime.now(UTC)
            task_info.result = result

            if task_info.started_at:
                duration = (task_info.completed_at - task_info.started_at).total_seconds()
                logger.info(
                    f"Background pipeline '{pipeline_name}' completed successfully "
                    f"(run_id={run_id}, duration={duration:.2f}s, status={result.status})"
                )
            else:
                logger.info(
                    f"Background pipeline '{pipeline_name}' completed successfully "
                    f"(run_id={run_id}, status={result.status})"
                )

            # Save to run history if available
            if self.run_history:
                try:
                    await self.run_history.save_run(result, triggered_by="manual")
                    logger.debug(f"Saved run {run_id} to history database")
                except Exception as history_error:
                    logger.error(
                        f"Failed to save run {run_id} to history: {history_error}",
                        exc_info=True
                    )

        except Exception as e:
            # Capture error
            task_info.status = TaskStatus.FAILED
            task_info.completed_at = datetime.now(UTC)
            task_info.error = str(e)

            if task_info.started_at:
                duration = (task_info.completed_at - task_info.started_at).total_seconds()
                logger.error(
                    f"Background pipeline '{pipeline_name}' failed after {duration:.2f}s "
                    f"(run_id={run_id}): {e}",
                    exc_info=True
                )
            else:
                logger.error(
                    f"Background pipeline '{pipeline_name}' failed "
                    f"(run_id={run_id}): {e}",
                    exc_info=True
                )

        finally:
            # Remove log handler
            pipeline_logger.removeHandler(log_handler)

    def get_task_status(self, run_id: str) -> TaskInfo | None:
        """Get status of a running or completed task.

        Args:
            run_id: Unique identifier for the task

        Returns:
            TaskInfo object if task exists, None otherwise
        """
        return self._tasks.get(run_id)

    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """Remove old completed tasks from memory.

        Removes tasks that have been completed for longer than the specified
        number of hours. This prevents unbounded memory growth.

        Args:
            older_than_hours: Remove tasks completed more than this many hours ago

        Returns:
            Number of tasks removed
        """
        now = datetime.now(UTC)
        to_remove = []

        for run_id, task_info in self._tasks.items():
            if (
                task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]
                and task_info.completed_at
            ):
                hours_since_completion = (
                    now - task_info.completed_at
                ).total_seconds() / 3600
                if hours_since_completion > older_than_hours:
                    to_remove.append(run_id)

        for run_id in to_remove:
            del self._tasks[run_id]

        if to_remove:
            logger.info(
                f"Cleaned up {len(to_remove)} completed task(s) older than {older_than_hours} hours"
            )
        else:
            logger.debug("No old tasks to clean up")

        return len(to_remove)
