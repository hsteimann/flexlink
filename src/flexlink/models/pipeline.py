"""Pipeline configuration models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepType(str, Enum):
    """Type of pipeline step."""
    EXTRACT = "extract"
    TRANSFORM = "transform"
    LOAD = "load"


class ErrorStrategy(str, Enum):
    """Error handling strategy for steps."""
    FAIL_PIPELINE = "fail_pipeline"  # Stop entire pipeline
    SKIP_STEP = "skip_step"          # Skip this step, continue
    CONTINUE = "continue"            # Log error, continue


class RetryPolicy(BaseModel):
    """Retry configuration for steps."""
    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_strategy: str = Field(default="exponential")  # fixed, exponential, linear
    backoff_factor: float = Field(default=2.0, ge=1.0)
    initial_delay_seconds: float = Field(default=1.0, ge=0.1)


class PipelineStepConfig(BaseModel):
    """Configuration for a single pipeline step."""

    name: str = Field(..., description="Step name (must be unique in pipeline)")
    type: StepType = Field(..., description="Step type: extract, transform, load")

    # Connector configuration (for extract/load steps)
    connector: str | None = Field(default=None, description="Connector name")
    method: str | None = Field(default=None, description="HTTP method for extract")
    path: str | None = Field(default=None, description="Path for extract")
    operation: str | None = Field(default=None, description="Operation for load (INSERT, etc.)")

    # Transformation configuration (for transform steps)
    mapping_ref: str | None = Field(default=None, description="Mapping configuration name")

    # Additional parameters
    params: dict[str, Any] = Field(default_factory=dict, description="Step-specific parameters")
    pagination: dict[str, Any] = Field(default_factory=dict, description="Pagination config for extract")
    batch_config: dict[str, Any] = Field(default_factory=dict, description="Batch config for load")

    # Error handling
    on_error: ErrorStrategy = Field(
        default=ErrorStrategy.FAIL_PIPELINE,
        description="What to do if step fails"
    )
    retry_policy: RetryPolicy | None = Field(default=None, description="Retry configuration")

    # Conditional execution (future enhancement)
    condition: str | None = Field(default=None, description="JSONata condition for execution")


class ScheduleConfig(BaseModel):
    """Scheduling configuration for pipelines."""
    enabled: bool = Field(default=False, description="Enable scheduled execution")
    cron: str | None = Field(default=None, description="Cron expression for schedule")
    interval_seconds: int | None = Field(default=None, ge=60, description="Interval in seconds")


class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""

    name: str = Field(..., description="Pipeline name (must be unique)")
    description: str = Field(default="", description="Pipeline description")
    version: str = Field(default="1.0", description="Pipeline version")

    steps: list[PipelineStepConfig] = Field(..., min_length=1, description="Pipeline steps")
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig, description="Scheduling config")

    # Metadata
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    enabled: bool = Field(default=True, description="Enable/disable pipeline")


class StepResult(BaseModel):
    """Result of a single step execution."""
    step_name: str
    status: str  # "success" | "error" | "skipped"
    duration_seconds: float
    records_processed: int = 0
    error_message: str | None = None


class ExecutionMetadata(BaseModel):
    """Metadata about pipeline execution."""
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    validation_errors: int = 0
    custom_metadata: dict[str, Any] = Field(default_factory=dict, description="Custom step metadata")


class TaskStatus(str, Enum):
    """Status of background task."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineRunStatus(BaseModel):
    """Status response for background pipeline execution."""
    run_id: str
    pipeline_name: str
    status: TaskStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None


class PipelineRunHistoryRecord(BaseModel):
    """Historical record of pipeline execution."""
    run_id: str
    pipeline_name: str
    status: str  # "success" | "partial" | "failed"
    started_at: datetime
    completed_at: datetime
    duration_seconds: float
    records_extracted: int = 0
    records_transformed: int = 0
    records_loaded: int = 0
    validation_errors: int = 0
    error_message: str | None = None
    triggered_by: str = "manual"  # "manual" | "schedule"


class PipelineExecutionResult(BaseModel):
    """Result of pipeline execution."""
    run_id: str
    pipeline_name: str
    status: str  # "success" | "partial" | "failed"

    started_at: datetime
    completed_at: datetime
    duration_seconds: float

    steps: list[StepResult]
    metadata: ExecutionMetadata

    error_message: str | None = None


class ScheduleSummary(BaseModel):
    """Compact schedule information for list views."""
    enabled: bool
    type: str | None = None  # "cron" | "interval" | None
    expression: str | None = None  # cron expression or "every Xs"
    next_run: datetime | None = None  # calculated from scheduler


class PipelineListItemResponse(BaseModel):
    """Single pipeline item in list view with metadata."""
    name: str
    description: str
    enabled: bool
    schedule: ScheduleSummary | None = None
    tags: list[str] = Field(default_factory=list)


class ScheduleUpdateRequest(BaseModel):
    """Request model for updating pipeline schedule."""
    enabled: bool = Field(..., description="Enable or disable schedule")
    cron: str | None = Field(default=None, description="Cron expression")
    interval_seconds: int | None = Field(default=None, ge=60, description="Interval in seconds")
