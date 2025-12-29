"""Log models for pipeline execution tracking."""

from pydantic import BaseModel


class LogEntry(BaseModel):
    """Single log entry."""
    timestamp: str
    level: str
    logger: str
    message: str


class LogsResponse(BaseModel):
    """Response for log retrieval."""
    run_id: str
    pipeline_name: str
    logs: list[LogEntry]
    total_entries: int
