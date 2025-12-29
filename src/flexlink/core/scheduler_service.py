"""Pipeline scheduler service for automated pipeline execution."""

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
    from flexlink.core.pipeline_registry import PipelineRegistry
    from flexlink.core.run_history import RunHistoryStorage

logger = logging.getLogger(__name__)


class SchedulerService:
    """
    Service for scheduling and executing pipelines automatically.

    Supports two trigger types:
    - Cron: Schedule using cron expressions (e.g., "0 */6 * * *" for every 6 hours)
    - Interval: Schedule using fixed intervals (e.g., every 3600 seconds)

    Features:
    - Async-compatible scheduler for FastAPI
    - Graceful startup and shutdown
    - Dynamic schedule reloading
    - Error handling that doesn't crash the scheduler
    - Misfire grace time to prevent job buildup
    """

    def __init__(
        self,
        pipeline_registry: "PipelineRegistry",
        orchestrator: "PipelineOrchestrator",
        run_history: "RunHistoryStorage | None" = None,
    ):
        """
        Initialize scheduler service.

        Args:
            pipeline_registry: Registry containing pipeline configurations
            orchestrator: Orchestrator for executing pipelines
            run_history: Optional run history storage for logging executions
        """
        self.pipeline_registry = pipeline_registry
        self.orchestrator = orchestrator
        self.run_history = run_history
        self.scheduler = AsyncIOScheduler()

        # Configure scheduler
        self.scheduler.configure(
            timezone="UTC",
            job_defaults={
                "coalesce": True,  # Merge multiple missed runs into one
                "max_instances": 1,  # Only one instance of a job runs at a time
                "misfire_grace_time": 60  # Allow up to 60s delay
            }
        )

    async def start(self) -> None:
        """
        Start the scheduler and register all enabled pipeline schedules.

        Scans the pipeline registry for pipelines with schedule configurations
        and registers them with the scheduler.
        """
        logger.info("Starting pipeline scheduler")

        # Register all scheduled pipelines
        scheduled_count = 0
        for pipeline_name in self.pipeline_registry.list_pipelines():
            config = self.pipeline_registry.get_pipeline(pipeline_name)

            if config.schedule and config.schedule.enabled:
                try:
                    self._schedule_pipeline(pipeline_name, config.schedule)
                    scheduled_count += 1
                    logger.info(
                        f"Scheduled pipeline '{pipeline_name}' with "
                        f"{self._format_schedule(config.schedule)}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to schedule pipeline '{pipeline_name}': {e}",
                        exc_info=True
                    )

        # Start the scheduler
        self.scheduler.start()
        logger.info(
            f"Pipeline scheduler started with {scheduled_count} scheduled pipeline(s)"
        )

    async def shutdown(self) -> None:
        """
        Gracefully shutdown the scheduler.

        Waits for running jobs to complete before shutting down.
        """
        logger.info("Shutting down pipeline scheduler")
        self.scheduler.shutdown(wait=True)
        logger.info("Pipeline scheduler shut down successfully")

    def _schedule_pipeline(self, pipeline_name: str, schedule_config) -> None:
        """
        Register a pipeline with the scheduler.

        Args:
            pipeline_name: Name of the pipeline to schedule
            schedule_config: ScheduleConfig with trigger configuration

        Raises:
            ValueError: If schedule configuration is invalid
        """
        # Determine trigger type
        if schedule_config.cron:
            trigger = CronTrigger.from_crontab(schedule_config.cron, timezone="UTC")
            job_id = f"pipeline_{pipeline_name}_cron"
        elif schedule_config.interval_seconds:
            trigger = IntervalTrigger(
                seconds=schedule_config.interval_seconds,
                timezone="UTC"
            )
            job_id = f"pipeline_{pipeline_name}_interval"
        else:
            raise ValueError(
                f"Pipeline '{pipeline_name}' schedule must specify either "
                "cron or interval_seconds"
            )

        # Add job to scheduler
        self.scheduler.add_job(
            func=self._execute_scheduled_pipeline,
            trigger=trigger,
            args=[pipeline_name],
            id=job_id,
            name=f"Pipeline: {pipeline_name}",
            replace_existing=True
        )

    async def _execute_scheduled_pipeline(self, pipeline_name: str) -> None:
        """
        Execute a scheduled pipeline.

        This is the callback function invoked by the scheduler.
        Errors are logged but don't crash the scheduler.

        Args:
            pipeline_name: Name of the pipeline to execute
        """
        logger.info(f"[SCHEDULED] Executing pipeline '{pipeline_name}'")
        start_time = datetime.now(UTC)

        try:
            result = await self.orchestrator.execute_pipeline(
                pipeline_name=pipeline_name,
                inputs=None
            )

            # Save to history
            if self.run_history:
                await self.run_history.save_run(result, triggered_by="schedule")

            duration = (datetime.now(UTC) - start_time).total_seconds()

            if result.status == "success":
                logger.info(
                    f"[SCHEDULED] Pipeline '{pipeline_name}' completed successfully "
                    f"in {duration:.2f}s"
                )
            else:
                logger.warning(
                    f"[SCHEDULED] Pipeline '{pipeline_name}' completed with status "
                    f"'{result.status}' in {duration:.2f}s: {result.error_message}"
                )

        except Exception as e:
            duration = (datetime.now(UTC) - start_time).total_seconds()
            logger.error(
                f"[SCHEDULED] Pipeline '{pipeline_name}' failed after {duration:.2f}s: {e}",
                exc_info=True
            )

    def reload_schedules(self) -> None:
        """
        Reload all pipeline schedules from the registry.

        Removes all existing scheduled jobs and re-registers them.
        Useful after pipeline configurations have been updated.
        """
        logger.info("Reloading pipeline schedules")

        # Remove all existing jobs
        self.scheduler.remove_all_jobs()

        # Re-register scheduled pipelines
        scheduled_count = 0
        for pipeline_name in self.pipeline_registry.list_pipelines():
            config = self.pipeline_registry.get_pipeline(pipeline_name)

            if config.schedule and config.schedule.enabled:
                try:
                    self._schedule_pipeline(pipeline_name, config.schedule)
                    scheduled_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to schedule pipeline '{pipeline_name}': {e}",
                        exc_info=True
                    )

        logger.info(f"Reloaded {scheduled_count} scheduled pipeline(s)")

    def get_scheduled_pipelines(self) -> list[dict]:
        """
        Get information about all currently scheduled pipelines.

        Returns:
            List of dicts with pipeline name, schedule info, and next run time
        """
        jobs = self.scheduler.get_jobs()
        scheduled_pipelines = []

        for job in jobs:
            # Extract pipeline name from job args
            pipeline_name = job.args[0] if job.args else "unknown"

            # Get next run time
            next_run_time = job.next_run_time.isoformat() if job.next_run_time else None

            # Determine schedule type
            trigger_type = type(job.trigger).__name__
            if trigger_type == "CronTrigger":
                schedule_info = str(job.trigger)
            elif trigger_type == "IntervalTrigger":
                schedule_info = f"Every {job.trigger.interval.total_seconds()}s"
            else:
                schedule_info = trigger_type

            scheduled_pipelines.append({
                "pipeline_name": pipeline_name,
                "job_id": job.id,
                "schedule_type": trigger_type,
                "schedule_info": schedule_info,
                "next_run_time": next_run_time,
                "enabled": True
            })

        return scheduled_pipelines

    def update_pipeline_schedule(
        self, pipeline_name: str, schedule_config
    ) -> None:
        """
        Update schedule for specific pipeline.

        Args:
            pipeline_name: Name of pipeline to update
            schedule_config: New ScheduleConfig object

        Raises:
            ValueError: If schedule configuration is invalid
        """
        logger.info(f"Updating schedule for pipeline '{pipeline_name}'")

        # Remove existing schedule if any
        job_id_cron = f"pipeline_{pipeline_name}_cron"
        job_id_interval = f"pipeline_{pipeline_name}_interval"

        if self.scheduler.get_job(job_id_cron):
            self.scheduler.remove_job(job_id_cron)
        if self.scheduler.get_job(job_id_interval):
            self.scheduler.remove_job(job_id_interval)

        # Add new schedule if enabled
        if schedule_config.enabled:
            self._schedule_pipeline(pipeline_name, schedule_config)
            logger.info(f"Schedule updated for pipeline '{pipeline_name}'")
        else:
            logger.info(f"Schedule disabled for pipeline '{pipeline_name}'")

    async def run_pipeline_now(self, pipeline_name: str) -> None:
        """
        Trigger immediate execution of a pipeline (bypass schedule).

        Args:
            pipeline_name: Name of pipeline to execute
        """
        logger.info(f"Manual trigger for scheduled pipeline '{pipeline_name}'")
        await self._execute_scheduled_pipeline(pipeline_name)

    def _format_schedule(self, schedule_config) -> str:
        """
        Format schedule config for logging.

        Args:
            schedule_config: ScheduleConfig object

        Returns:
            Human-readable schedule description
        """
        if schedule_config.cron:
            return f"cron '{schedule_config.cron}'"
        elif schedule_config.interval_seconds:
            return f"interval {schedule_config.interval_seconds}s"
        else:
            return "unknown schedule type"
