"""Run history storage for pipeline execution tracking.

This module provides the RunHistoryStorage class for persisting pipeline
execution history to a SQLite database. It tracks all pipeline runs with
detailed metrics and provides query capabilities for analytics.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import aiosqlite

from flexlink.models.pipeline import (
    PipelineExecutionResult,
    PipelineRunHistoryRecord,
)

logger = logging.getLogger(__name__)


class RunHistoryStorage:
    """SQLite-based storage for pipeline execution history.

    This class manages a SQLite database for storing historical pipeline
    execution records. It provides methods for saving runs, querying history,
    and calculating statistics.

    Attributes:
        db_path: Path to the SQLite database file
        _initialized: Flag indicating if database has been initialized
    """

    def __init__(self, db_path: str = "data/run_history.db"):
        """Initialize the RunHistoryStorage.

        Args:
            db_path: Path to SQLite database file (default: data/run_history.db)
        """
        self.db_path = Path(db_path)
        self._initialized = False

    async def initialize(self) -> None:
        """Create database and tables if they don't exist.

        Ensures the database directory exists and creates the pipeline_runs
        table with appropriate indexes for efficient querying.
        """
        try:
            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Initializing run history database at {self.db_path}")

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS pipeline_runs (
                        run_id TEXT PRIMARY KEY,
                        pipeline_name TEXT NOT NULL,
                        status TEXT NOT NULL,
                        started_at TIMESTAMP NOT NULL,
                        completed_at TIMESTAMP NOT NULL,
                        duration_seconds REAL NOT NULL,
                        records_extracted INTEGER DEFAULT 0,
                        records_transformed INTEGER DEFAULT 0,
                        records_loaded INTEGER DEFAULT 0,
                        validation_errors INTEGER DEFAULT 0,
                        error_message TEXT,
                        triggered_by TEXT DEFAULT 'manual',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_pipeline_name ON pipeline_runs(pipeline_name)"
                )
                await db.execute(
                    "CREATE INDEX IF NOT EXISTS idx_started_at ON pipeline_runs(started_at DESC)"
                )
                await db.commit()

            self._initialized = True
            logger.info("Run history database initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize run history database: {e}", exc_info=True)
            raise

    async def save_run(
        self,
        result: PipelineExecutionResult,
        triggered_by: Literal["manual", "schedule"] = "manual",
    ) -> None:
        """Save pipeline execution result to history.

        Args:
            result: The pipeline execution result to save
            triggered_by: How the pipeline was triggered ("manual" or "schedule")
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO pipeline_runs (
                        run_id, pipeline_name, status, started_at, completed_at,
                        duration_seconds, records_extracted, records_transformed,
                        records_loaded, validation_errors, error_message, triggered_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.run_id,
                        result.pipeline_name,
                        result.status,
                        result.started_at,
                        result.completed_at,
                        result.duration_seconds,
                        result.metadata.records_extracted,
                        result.metadata.records_transformed,
                        result.metadata.records_loaded,
                        result.metadata.validation_errors,
                        result.error_message,
                        triggered_by,
                    ),
                )
                await db.commit()

            logger.debug(
                f"Saved pipeline run to history: {result.pipeline_name} "
                f"(run_id={result.run_id}, status={result.status}, triggered_by={triggered_by})"
            )

        except Exception as e:
            logger.error(
                f"Failed to save run {result.run_id} to history database: {e}",
                exc_info=True
            )
            raise

    async def get_run(self, run_id: str) -> PipelineRunHistoryRecord | None:
        """Retrieve specific run by ID.

        Args:
            run_id: Unique identifier for the run

        Returns:
            PipelineRunHistoryRecord if found, None otherwise
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT run_id, pipeline_name, status, started_at, completed_at,
                           duration_seconds, records_extracted, records_transformed,
                           records_loaded, validation_errors, error_message, triggered_by
                    FROM pipeline_runs
                    WHERE run_id = ?
                    """,
                    (run_id,),
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        logger.debug(f"Run {run_id} not found in history")
                        return None

                    logger.debug(f"Retrieved run {run_id} from history")
                    return PipelineRunHistoryRecord(
                        run_id=row["run_id"],
                        pipeline_name=row["pipeline_name"],
                        status=row["status"],
                        started_at=datetime.fromisoformat(row["started_at"]),
                        completed_at=datetime.fromisoformat(row["completed_at"]),
                        duration_seconds=row["duration_seconds"],
                        records_extracted=row["records_extracted"],
                        records_transformed=row["records_transformed"],
                        records_loaded=row["records_loaded"],
                        validation_errors=row["validation_errors"],
                        error_message=row["error_message"],
                        triggered_by=row["triggered_by"],
                    )

        except Exception as e:
            logger.error(f"Failed to retrieve run {run_id} from history: {e}", exc_info=True)
            raise

    async def list_runs(
        self,
        pipeline_name: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PipelineRunHistoryRecord]:
        """List pipeline runs with pagination.

        Args:
            pipeline_name: Optional filter by pipeline name
            limit: Maximum number of records to return (default: 50)
            offset: Number of records to skip (default: 0)

        Returns:
            List of PipelineRunHistoryRecord objects
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if pipeline_name:
                query = """
                    SELECT run_id, pipeline_name, status, started_at, completed_at,
                           duration_seconds, records_extracted, records_transformed,
                           records_loaded, validation_errors, error_message, triggered_by
                    FROM pipeline_runs
                    WHERE pipeline_name = ?
                    ORDER BY started_at DESC
                    LIMIT ? OFFSET ?
                """
                params: tuple[str | int, ...] = (pipeline_name, limit, offset)
            else:
                query = """
                    SELECT run_id, pipeline_name, status, started_at, completed_at,
                           duration_seconds, records_extracted, records_transformed,
                           records_loaded, validation_errors, error_message, triggered_by
                    FROM pipeline_runs
                    ORDER BY started_at DESC
                    LIMIT ? OFFSET ?
                """
                params = (limit, offset)

            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

                return [
                    PipelineRunHistoryRecord(
                        run_id=row["run_id"],
                        pipeline_name=row["pipeline_name"],
                        status=row["status"],
                        started_at=datetime.fromisoformat(row["started_at"]),
                        completed_at=datetime.fromisoformat(row["completed_at"]),
                        duration_seconds=row["duration_seconds"],
                        records_extracted=row["records_extracted"],
                        records_transformed=row["records_transformed"],
                        records_loaded=row["records_loaded"],
                        validation_errors=row["validation_errors"],
                        error_message=row["error_message"],
                        triggered_by=row["triggered_by"],
                    )
                    for row in rows
                ]

    async def get_statistics(self, pipeline_name: str) -> dict[str, Any]:
        """Get success rate, average duration, and other statistics.

        Args:
            pipeline_name: Name of the pipeline to analyze

        Returns:
            Dictionary with statistics (total_runs, success_rate, avg_duration, etc.)
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get overall statistics
            async with db.execute(
                """
                SELECT
                    COUNT(*) as total_runs,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_runs,
                    AVG(duration_seconds) as avg_duration,
                    MIN(duration_seconds) as min_duration,
                    MAX(duration_seconds) as max_duration,
                    SUM(records_extracted) as total_extracted,
                    SUM(records_loaded) as total_loaded
                FROM pipeline_runs
                WHERE pipeline_name = ?
                """,
                (pipeline_name,),
            ) as cursor:
                row = await cursor.fetchone()

                # Aggregate queries always return a row, but check for type safety
                if row is None:
                    return {
                        "pipeline_name": pipeline_name,
                        "total_runs": 0,
                        "successful_runs": 0,
                        "success_rate": 0.0,
                        "avg_duration_seconds": 0.0,
                        "min_duration_seconds": 0.0,
                        "max_duration_seconds": 0.0,
                        "total_records_extracted": 0,
                        "total_records_loaded": 0,
                    }

                total_runs = row["total_runs"] or 0
                successful_runs = row["successful_runs"] or 0
                success_rate = (
                    (successful_runs / total_runs * 100) if total_runs > 0 else 0.0
                )

                return {
                    "pipeline_name": pipeline_name,
                    "total_runs": total_runs,
                    "successful_runs": successful_runs,
                    "success_rate": success_rate,
                    "avg_duration_seconds": row["avg_duration"] or 0.0,
                    "min_duration_seconds": row["min_duration"] or 0.0,
                    "max_duration_seconds": row["max_duration"] or 0.0,
                    "total_records_extracted": row["total_extracted"] or 0,
                    "total_records_loaded": row["total_loaded"] or 0,
                }

    async def delete_old_runs(self, older_than_days: int = 30) -> int:
        """Delete runs older than N days.

        Args:
            older_than_days: Delete runs older than this many days

        Returns:
            Number of runs deleted
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cutoff_date = datetime.now(UTC).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                cutoff_timestamp = cutoff_date.timestamp() - (older_than_days * 86400)
                cutoff_datetime = datetime.fromtimestamp(cutoff_timestamp, tz=UTC)

                logger.info(
                    f"Deleting pipeline runs older than {older_than_days} days "
                    f"(before {cutoff_datetime.isoformat()})"
                )

                cursor = await db.execute(
                    "DELETE FROM pipeline_runs WHERE started_at < ?",
                    (cutoff_datetime.isoformat(),),
                )
                await db.commit()

                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    logger.info(f"Deleted {deleted_count} old pipeline run(s) from history")
                else:
                    logger.debug("No old runs to delete")

                return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete old runs from history: {e}", exc_info=True)
            raise
