"""Pipeline execution context."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from flexlink.models.pipeline import ExecutionMetadata


@dataclass
class StepError:
    """Error that occurred during step execution."""
    step_name: str
    error_type: str
    error_message: str
    timestamp: datetime


@dataclass
class PipelineRunContext:
    """
    Shared execution context for pipeline runs.

    This context is passed between all steps in a pipeline,
    allowing them to share data and metadata.

    IMPORTANT: This context is mutated in-place by steps.
    Never copy or replace the context object.
    """

    run_id: str
    pipeline_name: str
    started_at: datetime
    current_step: int = 0

    # Data being processed (modified by each step)
    data: list[dict[str, Any]] = field(default_factory=list)

    # Execution metadata
    metadata: ExecutionMetadata = field(default_factory=ExecutionMetadata)

    # Errors accumulated during execution
    errors: list[StepError] = field(default_factory=list)

    # Step execution tracking
    _step_successes: list[str] = field(default_factory=list)

    def record_step_success(self, step_name: str) -> None:
        """
        Record successful step execution.

        Args:
            step_name: Name of step that succeeded
        """
        self._step_successes.append(step_name)

    def record_step_error(self, step_name: str, error: Exception) -> None:
        """
        Record step error.

        Args:
            step_name: Name of step that failed
            error: Exception that occurred
        """
        self.errors.append(StepError(
            step_name=step_name,
            error_type=type(error).__name__,
            error_message=str(error),
            timestamp=datetime.now(UTC)
        ))

    def get_records_processed(self) -> int:
        """Get total records currently in context."""
        return len(self.data)

    def get_successful_steps(self) -> list[str]:
        """Get list of successfully executed steps."""
        return self._step_successes.copy()

    def get_errors_by_step(self) -> dict[str, list[StepError]]:
        """
        Group errors by step name.

        Returns:
            Dictionary mapping step name to list of errors
        """
        errors_by_step: dict[str, list[StepError]] = {}
        for error in self.errors:
            if error.step_name not in errors_by_step:
                errors_by_step[error.step_name] = []
            errors_by_step[error.step_name].append(error)
        return errors_by_step

    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.errors) > 0
