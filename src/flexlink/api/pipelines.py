"""Pipeline orchestration API endpoints."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.run_history import RunHistoryStorage
from flexlink.core.scheduler_service import SchedulerService
from flexlink.core.task_manager import TaskManager
from flexlink.models.logs import LogEntry, LogsResponse
from flexlink.models.pipeline import (
    PipelineExecutionResult,
    PipelineListItemResponse,
    PipelineRunHistoryRecord,
    PipelineRunStatus,
    ScheduleConfig,
    ScheduleSummary,
    ScheduleUpdateRequest,
    TaskStatus,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])


# Response models
class PipelineListResponse(BaseModel):
    """Response model for listing pipelines."""
    pipelines: list[PipelineListItemResponse]
    count: int


class PipelineDetailResponse(BaseModel):
    """Response model for pipeline details."""
    name: str
    description: str
    version: str
    enabled: bool
    steps: list[dict[str, Any]]
    tags: list[str]
    schedule: dict[str, Any] | None = None


class PipelineExecutionRequest(BaseModel):
    """Request model for pipeline execution."""
    inputs: dict[str, Any] | None = None


# Dependency injection
def get_pipeline_registry(request: Request) -> PipelineRegistry:
    """Get pipeline registry from app state."""
    return request.app.state.pipeline_registry  # type: ignore[no-any-return]


def get_orchestrator(request: Request) -> PipelineOrchestrator:
    """Get pipeline orchestrator from app state."""
    return request.app.state.pipeline_orchestrator  # type: ignore[no-any-return]


def get_scheduler_service(request: Request) -> SchedulerService:
    """Get scheduler service from app state."""
    return request.app.state.scheduler_service  # type: ignore[no-any-return]


def get_task_manager(request: Request) -> TaskManager:
    """Get task manager from app state."""
    return request.app.state.task_manager  # type: ignore[no-any-return]


def get_run_history(request: Request) -> RunHistoryStorage:
    """Get run history storage from app state."""
    return request.app.state.run_history  # type: ignore[no-any-return]


@router.get("", response_model=PipelineListResponse)
async def list_pipelines(
    registry: PipelineRegistry = Depends(get_pipeline_registry),
    scheduler: SchedulerService = Depends(get_scheduler_service)
) -> PipelineListResponse:
    """
    List all available pipelines with metadata.

    Returns:
        List of pipelines with metadata and count
    """
    pipeline_names = registry.list_pipelines()
    scheduled_info = {p["pipeline_name"]: p for p in scheduler.get_scheduled_pipelines()}

    items = []
    for name in pipeline_names:
        config = registry.get_pipeline(name)

        # Build schedule summary
        schedule_summary = None
        if config.schedule and config.schedule.enabled:
            sched_type = "cron" if config.schedule.cron else "interval"
            expression = config.schedule.cron or f"every {config.schedule.interval_seconds}s"
            next_run = scheduled_info.get(name, {}).get("next_run_time")

            schedule_summary = ScheduleSummary(
                enabled=True,
                type=sched_type,
                expression=expression,
                next_run=next_run
            )

        items.append(PipelineListItemResponse(
            name=config.name,
            description=config.description,
            enabled=config.enabled,
            schedule=schedule_summary,
            tags=config.tags
        ))

    return PipelineListResponse(pipelines=items, count=len(items))


@router.get("/{pipeline_name}", response_model=PipelineDetailResponse)
async def get_pipeline(
    pipeline_name: str,
    registry: PipelineRegistry = Depends(get_pipeline_registry)
) -> PipelineDetailResponse:
    """
    Get pipeline configuration details.

    Args:
        pipeline_name: Name of pipeline to retrieve

    Returns:
        Pipeline configuration details

    Raises:
        HTTPException: 404 if pipeline not found
    """
    try:
        config = registry.get_pipeline(pipeline_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found"
        )

    # Convert to response model
    return PipelineDetailResponse(
        name=config.name,
        description=config.description,
        version=config.version,
        enabled=config.enabled,
        steps=[
            {
                "name": step.name,
                "type": step.type.value,
                "connector": step.connector,
                "on_error": step.on_error.value
            }
            for step in config.steps
        ],
        tags=config.tags,
        schedule=config.schedule.model_dump() if config.schedule else None
    )


@router.post(
    "/{pipeline_name}/run",
    response_model=PipelineExecutionResult | PipelineRunStatus,
)
async def execute_pipeline(
    pipeline_name: str,
    background: bool = Query(default=False, description="Run in background"),
    request_body: PipelineExecutionRequest = PipelineExecutionRequest(),
    orchestrator: PipelineOrchestrator = Depends(get_orchestrator),
    task_manager: TaskManager = Depends(get_task_manager),
    run_history: RunHistoryStorage = Depends(get_run_history),
) -> PipelineExecutionResult | PipelineRunStatus:
    """
    Execute a pipeline.

    Args:
        pipeline_name: Name of pipeline to execute
        background: Run pipeline in background (returns run_id immediately)
        request_body: Optional inputs for pipeline execution

    Returns:
        PipelineRunStatus if background=True, PipelineExecutionResult if background=False

    Raises:
        HTTPException: 404 if pipeline not found
        HTTPException: 400 if pipeline execution fails
    """
    logger.info(
        f"Executing pipeline: {pipeline_name} (background={background})"
    )

    if background:
        # Submit to background task manager
        run_id = task_manager.submit_task(
            pipeline_name, orchestrator, request_body.inputs
        )
        return PipelineRunStatus(
            run_id=run_id, pipeline_name=pipeline_name, status=TaskStatus.QUEUED
        )
    else:
        # Execute synchronously (existing pattern)
        try:
            result = await orchestrator.execute_pipeline(
                pipeline_name=pipeline_name, inputs=request_body.inputs
            )

            # Save to run history
            await run_history.save_run(result, triggered_by="manual")

            return result

        except KeyError:
            raise HTTPException(
                status_code=404, detail=f"Pipeline '{pipeline_name}' not found"
            )
        except Exception as e:
            logger.error(f"Pipeline execution failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Pipeline execution failed: {str(e)}",
            )


@router.get(
    "/runs/{run_id}",
    response_model=PipelineExecutionResult | PipelineRunStatus,
)
async def get_pipeline_run(
    run_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
    run_history: RunHistoryStorage = Depends(get_run_history),
) -> PipelineExecutionResult | PipelineRunStatus:
    """
    Get pipeline run status.

    Polls the status of a background pipeline execution. Returns the full
    execution result if the pipeline has completed, or status information
    if it's still running.

    Args:
        run_id: Unique identifier for the pipeline run

    Returns:
        PipelineRunStatus for running tasks, PipelineExecutionResult for completed tasks

    Raises:
        HTTPException: 404 if run_id not found
    """
    # Check in-memory tasks first (running/recent)
    task_info = task_manager.get_task_status(run_id)
    if task_info:
        if task_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            # Return full result for completed tasks
            if task_info.result:
                return task_info.result
            else:
                # Task failed, return status with error
                return PipelineRunStatus(
                    run_id=task_info.run_id,
                    pipeline_name=task_info.pipeline_name,
                    status=TaskStatus.FAILED,
                    started_at=task_info.started_at,
                    completed_at=task_info.completed_at,
                    error_message=task_info.error,
                )
        else:
            # Return status for running/queued tasks
            duration = None
            if task_info.started_at:
                duration = (
                    datetime.now(UTC) - task_info.started_at
                ).total_seconds()

            return PipelineRunStatus(
                run_id=task_info.run_id,
                pipeline_name=task_info.pipeline_name,
                status=task_info.status,
                started_at=task_info.started_at,
                duration_seconds=duration,
            )

    # Check database for historical runs
    historical_run = await run_history.get_run(run_id)
    if historical_run:
        # Convert to PipelineRunStatus (completed)
        return PipelineRunStatus(
            run_id=historical_run.run_id,
            pipeline_name=historical_run.pipeline_name,
            status=TaskStatus.COMPLETED,
            started_at=historical_run.started_at,
            completed_at=historical_run.completed_at,
            duration_seconds=historical_run.duration_seconds,
            error_message=historical_run.error_message,
        )

    raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found")


@router.get(
    "/{pipeline_name}/runs",
    response_model=list[PipelineRunHistoryRecord],
)
async def list_pipeline_runs(
    pipeline_name: str,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    registry: PipelineRegistry = Depends(get_pipeline_registry),
    run_history: RunHistoryStorage = Depends(get_run_history),
) -> list[PipelineRunHistoryRecord]:
    """
    List pipeline execution history.

    Retrieves historical pipeline execution records with pagination.
    Results are ordered by start time (most recent first).

    Args:
        pipeline_name: Name of pipeline to retrieve history for
        limit: Maximum number of records to return (1-100, default: 50)
        offset: Number of records to skip (default: 0)

    Returns:
        List of pipeline run history records

    Raises:
        HTTPException: 404 if pipeline not found
    """
    # Validate pipeline exists
    try:
        registry.get_pipeline(pipeline_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found"
        )

    runs = await run_history.list_runs(
        pipeline_name=pipeline_name, limit=limit, offset=offset
    )
    return runs


@router.get(
    "/{pipeline_name}/runs/{run_id}/logs",
    response_model=LogsResponse,
)
async def get_pipeline_run_logs(
    pipeline_name: str,
    run_id: str,
    limit: int = Query(default=1000, ge=1, le=10000),
    offset: int = Query(default=0, ge=0),
    task_manager: TaskManager = Depends(get_task_manager),
) -> LogsResponse:
    """
    Get logs for a pipeline run.

    For active/recent runs, retrieves logs from in-memory task storage.
    Historical runs do not have logs stored (logs are ephemeral).

    Args:
        pipeline_name: Name of pipeline
        run_id: Unique run identifier
        limit: Maximum log entries to return (1-10000, default: 1000)
        offset: Number of entries to skip (default: 0)

    Returns:
        Log entries with pagination

    Raises:
        HTTPException: 404 if run not found or logs unavailable
    """
    # Check task manager for in-memory logs
    task_info = task_manager.get_task_status(run_id)

    if not task_info:
        raise HTTPException(
            status_code=404,
            detail=f"Run {run_id} not found or logs not available (only recent runs have logs)"
        )

    # Apply pagination
    total = len(task_info.logs)
    paginated_logs = task_info.logs[offset:offset + limit]

    return LogsResponse(
        run_id=run_id,
        pipeline_name=pipeline_name,
        logs=[LogEntry(**log) for log in paginated_logs],
        total_entries=total
    )


@router.post("/{pipeline_name}/reload")
async def reload_pipeline(
    pipeline_name: str,
    registry: PipelineRegistry = Depends(get_pipeline_registry)
) -> dict[str, str]:
    """
    Reload pipeline configuration from disk.

    Args:
        pipeline_name: Name of pipeline to reload

    Returns:
        Success message

    Raises:
        HTTPException: 404 if pipeline not found after reload
    """
    logger.info(f"Reloading pipeline: {pipeline_name}")

    registry.reload()

    try:
        registry.get_pipeline(pipeline_name)
        return {"status": "success", "message": f"Pipeline '{pipeline_name}' reloaded"}
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found after reload"
        )


@router.get("/schedules", response_model=list[dict[str, Any]])
async def list_scheduled_pipelines(
    scheduler: SchedulerService = Depends(get_scheduler_service)
) -> list[dict[str, Any]]:
    """
    List all currently scheduled pipelines with next run times.

    Returns:
        List of scheduled pipeline information including next run times
    """
    return scheduler.get_scheduled_pipelines()


@router.post("/schedules/reload")
async def reload_schedules(
    scheduler: SchedulerService = Depends(get_scheduler_service)
) -> dict[str, str]:
    """
    Reload all pipeline schedules from registry.

    Removes existing schedules and re-registers them from updated
    pipeline configurations.

    Returns:
        Success message
    """
    scheduler.reload_schedules()
    return {"status": "success", "message": "Pipeline schedules reloaded"}


@router.patch("/{pipeline_name}/schedule")
async def update_pipeline_schedule(
    pipeline_name: str,
    schedule_update: ScheduleUpdateRequest,
    registry: PipelineRegistry = Depends(get_pipeline_registry),
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> dict[str, str]:
    """
    Update pipeline schedule configuration.

    Updates the schedule in-memory only (does not persist to YAML config).
    Schedule changes are lost on service restart.

    Args:
        pipeline_name: Name of pipeline to update
        schedule_update: New schedule configuration

    Returns:
        Success message

    Raises:
        HTTPException: 404 if pipeline not found
        HTTPException: 400 if schedule configuration invalid
    """
    # Validate pipeline exists
    try:
        registry.get_pipeline(pipeline_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found"
        )

    # Create ScheduleConfig from request
    try:
        new_schedule = ScheduleConfig(
            enabled=schedule_update.enabled,
            cron=schedule_update.cron,
            interval_seconds=schedule_update.interval_seconds
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule configuration: {str(e)}"
        )

    # Update scheduler
    try:
        scheduler.update_pipeline_schedule(pipeline_name, new_schedule)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "success",
        "message": f"Schedule updated for pipeline '{pipeline_name}'"
    }


@router.post("/{pipeline_name}/schedule/run-now")
async def trigger_scheduled_pipeline_now(
    pipeline_name: str,
    registry: PipelineRegistry = Depends(get_pipeline_registry),
    scheduler: SchedulerService = Depends(get_scheduler_service),
) -> dict[str, str]:
    """
    Trigger immediate execution of a scheduled pipeline.

    Executes the pipeline immediately, bypassing the schedule.
    Pipeline does not need to be scheduled to use this endpoint.

    Args:
        pipeline_name: Name of pipeline to execute

    Returns:
        Success message

    Raises:
        HTTPException: 404 if pipeline not found
        HTTPException: 500 if execution fails
    """
    # Validate pipeline exists
    try:
        registry.get_pipeline(pipeline_name)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Pipeline '{pipeline_name}' not found"
        )

    # Execute immediately
    try:
        await scheduler.run_pipeline_now(pipeline_name)
        return {
            "status": "success",
            "message": f"Pipeline '{pipeline_name}' execution triggered"
        }
    except Exception as e:
        logger.error(f"Failed to execute pipeline '{pipeline_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )
