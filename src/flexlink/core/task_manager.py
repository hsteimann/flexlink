"""Task Manager for background pipeline execution.

This module provides the TaskManager class for managing background pipeline
executions using asyncio tasks. It tracks task status in-memory and provides
status polling capabilities for running and completed tasks.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any
from dataclasses import dataclass

from flexlink.models.pipeline import PipelineExecutionResult


@dataclass
class TaskInfo:
    """Information about a background pipeline task."""

    run_id: str
    pipeline_name: str
    status: str  # "queued", "running", "completed", "failed"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    task: asyncio.Task | None = None
    result: PipelineExecutionResult | None = None
    error: str | None = None


class TaskManager:
    """Manages background pipeline execution tasks.

    The TaskManager maintains an in-memory registry of active and recently
    completed pipeline execution tasks. It provides methods for submitting
    pipelines for background execution, polling task status, and cleaning up
    completed tasks.

    Attributes:
        _tasks: Dictionary mapping run_id to TaskInfo objects
    """

    def __init__(self):
        """Initialize the TaskManager with an empty task registry."""
        self._tasks: Dict[str, TaskInfo] = {}

    def submit_task(
        self,
        pipeline_name: str,
        orchestrator: Any,
        inputs: Dict[str, Any] | None = None,
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

        # Create task info with queued status
        task_info = TaskInfo(
            run_id=run_id,
            pipeline_name=pipeline_name,
            status="queued",
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
        orchestrator: Any,
        inputs: Dict[str, Any] | None,
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
            return

        try:
            # Update status to running
            task_info.status = "running"
            task_info.started_at = datetime.now(timezone.utc)

            # Execute the pipeline
            result = await orchestrator.execute_pipeline(
                pipeline_name=pipeline_name, inputs=inputs
            )

            # Update task with result
            task_info.status = "completed"
            task_info.completed_at = datetime.now(timezone.utc)
            task_info.result = result

        except Exception as e:
            # Capture error
            task_info.status = "failed"
            task_info.completed_at = datetime.now(timezone.utc)
            task_info.error = str(e)

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
        now = datetime.now(timezone.utc)
        to_remove = []

        for run_id, task_info in self._tasks.items():
            if task_info.status in ["completed", "failed"] and task_info.completed_at:
                hours_since_completion = (
                    now - task_info.completed_at
                ).total_seconds() / 3600
                if hours_since_completion > older_than_hours:
                    to_remove.append(run_id)

        for run_id in to_remove:
            del self._tasks[run_id]

        return len(to_remove)
