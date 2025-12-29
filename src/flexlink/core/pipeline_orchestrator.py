"""Pipeline orchestration engine."""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from flexlink.core import mapping_loader
from flexlink.core.pipeline_context import PipelineRunContext
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.pipeline_steps import ExtractStep, LoadStep, PipelineStep, TransformStep
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.transformation import TransformationEngine
from flexlink.core.validator import Validator
from flexlink.models.pipeline import (
    ErrorStrategy,
    ExecutionMetadata,
    PipelineConfig,
    PipelineExecutionResult,
    PipelineStepConfig,
    RetryPolicy,
    StepResult,
    StepType,
)

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Orchestrates multi-step pipeline execution."""

    def __init__(
        self,
        pipeline_registry: PipelineRegistry,
        connector_registry: ConnectorRegistry,
        transformation_engine: TransformationEngine
    ):
        self.pipeline_registry = pipeline_registry
        self.connector_registry = connector_registry
        self.transformation_engine = transformation_engine

    def _convert_inputs_to_records(
        self,
        inputs: dict[str, Any] | None
    ) -> list[dict[str, Any]]:
        """
        Convert inputs to list of records for context.data.

        Supports multiple input formats:
        - None: Empty list (existing behavior)
        - Dict with 'records' key: Extract list from {"records": [...]}
        - Dict with 'data' key: Extract list from {"data": [...]}
        - Dict with 'items' key: Extract list from {"items": [...]}
        - Plain dict: Wrap as single record [input]

        Args:
            inputs: Input data from API call

        Returns:
            List of records ready for context.data
        """
        if inputs is None:
            return []

        if isinstance(inputs, dict):
            # Check for common list-wrapper keys
            for key in ["records", "data", "items"]:
                if key in inputs and isinstance(inputs[key], list):
                    logger.info(
                        f"Seeding context from inputs.{key}: "
                        f"{len(inputs[key])} record(s)"
                    )
                    return cast(list[dict[str, Any]], inputs[key])

            # No list wrapper found - treat entire dict as single record
            logger.info("Seeding context from inputs: 1 record (single dict)")
            return [inputs]

        logger.warning(
            f"Unexpected inputs type: {type(inputs).__name__}, "
            f"using empty context"
        )
        return []

    async def execute_pipeline(
        self,
        pipeline_name: str,
        inputs: dict[str, Any] | None = None
    ) -> PipelineExecutionResult:
        """
        Execute a pipeline end-to-end.

        Args:
            pipeline_name: Name of pipeline to execute
            inputs: Optional input data for pipeline

        Returns:
            PipelineExecutionResult with status, metadata, and results
        """
        # 1. Load pipeline config
        config = self.pipeline_registry.get_pipeline(pipeline_name)

        # 2. Convert inputs to records
        initial_records = self._convert_inputs_to_records(inputs)

        # 3. Create execution context with seeded data
        context = PipelineRunContext(
            run_id=str(uuid.uuid4()),
            pipeline_name=pipeline_name,
            started_at=datetime.now(UTC),
            data=initial_records,
            metadata=ExecutionMetadata(
                records_extracted=len(initial_records)
            ),
            errors=[]
        )

        # 4. Log context initialization
        if initial_records:
            logger.info(
                f"Pipeline '{pipeline_name}' started with "
                f"{len(initial_records)} input record(s) "
                f"(run_id={context.run_id})"
            )
        else:
            logger.info(
                f"Pipeline '{pipeline_name}' started with empty context "
                f"(run_id={context.run_id})"
            )

        # 5. Execute each step with retry support
        for i, step_config in enumerate(config.steps):
            context.current_step = i
            step = self._create_step(step_config)

            try:
                logger.info(f"Executing step {i+1}/{len(config.steps)}: {step_config.name}")

                # Execute with retry if configured
                await self._execute_step_with_retry(step, step_config, context)

                context.record_step_success(step_config.name)

            except Exception as e:
                context.record_step_error(step_config.name, e)

                # Handle error according to policy
                if step_config.on_error == ErrorStrategy.FAIL_PIPELINE:
                    logger.error(f"Step {step_config.name} failed, stopping pipeline")
                    break
                elif step_config.on_error == ErrorStrategy.SKIP_STEP:
                    logger.warning(f"Step {step_config.name} failed, skipping")
                    continue
                elif step_config.on_error == ErrorStrategy.CONTINUE:
                    logger.warning(f"Step {step_config.name} failed, continuing")
                    continue

        # 6. Build result
        return self._build_result(context, config)

    async def _execute_step_with_retry(
        self,
        step: PipelineStep,
        step_config: PipelineStepConfig,
        context: PipelineRunContext
    ) -> None:
        """
        Execute a step with retry logic.

        Implements exponential backoff with jitter for failed steps.
        Respects the retry_policy configuration if provided.
        """
        retry_policy = step_config.retry_policy or RetryPolicy()
        max_attempts = retry_policy.max_attempts

        for attempt in range(1, max_attempts + 1):
            try:
                # Attempt to execute the step
                await step.execute(context)

                # Success - log and return
                if attempt > 1:
                    logger.info(
                        f"Step {step_config.name} succeeded on attempt {attempt}/{max_attempts}"
                    )
                return

            except Exception as e:
                # Log the failure
                logger.warning(
                    f"Step {step_config.name} failed on attempt {attempt}/{max_attempts}: {e}"
                )

                # If this was the last attempt, raise the error
                if attempt >= max_attempts:
                    logger.error(
                        f"Step {step_config.name} exhausted all {max_attempts} retry attempts"
                    )
                    raise

                # Calculate backoff delay
                delay = self._calculate_backoff_delay(
                    attempt=attempt,
                    policy=retry_policy
                )

                logger.debug(f"Retrying step {step_config.name} after {delay:.2f}s delay")

                # Sleep before retry
                await asyncio.sleep(delay)

    def _calculate_backoff_delay(
        self,
        attempt: int,
        policy: RetryPolicy
    ) -> float:
        """
        Calculate backoff delay for retry attempt.

        Supports:
        - exponential: delay = initial_delay * (backoff_factor ^ attempt)
        - linear: delay = initial_delay * attempt
        - fixed: delay = initial_delay

        Adds jitter (±20% randomness) to prevent thundering herd.
        """
        import random

        if policy.backoff_strategy == "exponential":
            delay = policy.initial_delay_seconds * (policy.backoff_factor ** (attempt - 1))
        elif policy.backoff_strategy == "linear":
            delay = policy.initial_delay_seconds * attempt
        elif policy.backoff_strategy == "fixed":
            delay = policy.initial_delay_seconds
        else:
            # Default to exponential
            delay = policy.initial_delay_seconds * (policy.backoff_factor ** (attempt - 1))

        # Add jitter (±20%)
        jitter_factor = 1.0 + (random.random() - 0.5) * 0.4  # 0.8 to 1.2
        delay_with_jitter = delay * jitter_factor

        return delay_with_jitter

    def _create_step(
        self, step_config: PipelineStepConfig
    ) -> ExtractStep | TransformStep | LoadStep:
        """
        Create step instance from configuration.

        Note: Imports step classes locally to avoid circular imports.
        """
        # Import step classes here to avoid circular imports
        from flexlink.core.pipeline_steps import ExtractStep, LoadStep, TransformStep

        if step_config.type == StepType.EXTRACT:
            # Validate required fields for EXTRACT step
            if not step_config.connector:
                raise ValueError(
                    f"Step '{step_config.name}': EXTRACT step requires 'connector' field"
                )
            if not step_config.method:
                raise ValueError(f"Step '{step_config.name}': EXTRACT step requires 'method' field")
            if not step_config.path:
                raise ValueError(f"Step '{step_config.name}': EXTRACT step requires 'path' field")

            return ExtractStep(
                connector=self.connector_registry.get_connector(step_config.connector),
                method=step_config.method,
                path=step_config.path,
                params=step_config.params,
                pagination=step_config.pagination
            )
        elif step_config.type == StepType.TRANSFORM:
            # Validate required fields for TRANSFORM step
            if not step_config.mapping_ref:
                raise ValueError(
                    f"Step '{step_config.name}': TRANSFORM step requires 'mapping_ref' field"
                )

            mapping = mapping_loader.load_mapping_config(step_config.mapping_ref)

            # Create dedicated engine with mapping rules
            # Note: MappingRule is compatible with TransformationRule (has all required fields)
            transform_engine = TransformationEngine(rules=mapping.mappings)  # type: ignore[arg-type]

            # Create validator if validation configured
            validator = None
            if mapping.validation:
                validator = Validator(config=mapping.validation)

            return TransformStep(
                transformation_engine=transform_engine,
                validator=validator,
                mapping=mapping
            )
        elif step_config.type == StepType.LOAD:
            # Validate required fields for LOAD step
            if not step_config.connector:
                raise ValueError(f"Step '{step_config.name}': LOAD step requires 'connector' field")

            return LoadStep(
                connector=self.connector_registry.get_connector(step_config.connector),
                operation=step_config.operation,
                params=step_config.params,
                batch_config=step_config.batch_config
            )
        else:
            raise ValueError(f"Unknown step type: {step_config.type}")

    def _build_result(
        self,
        context: PipelineRunContext,
        config: PipelineConfig
    ) -> PipelineExecutionResult:
        """
        Build execution result from context.

        Args:
            context: Pipeline execution context
            config: Pipeline configuration

        Returns:
            PipelineExecutionResult with status and metadata
        """
        completed_at = datetime.now(UTC)
        duration_seconds = (completed_at - context.started_at).total_seconds()

        # Build step results
        step_results = []
        successful_steps = context.get_successful_steps()
        errors_by_step = context.get_errors_by_step()

        for step_config in config.steps:
            step_name = step_config.name

            if step_name in successful_steps:
                step_results.append(StepResult(
                    step_name=step_name,
                    status="success",
                    duration_seconds=0.0,  # Individual step timing not tracked
                    records_processed=context.get_records_processed()
                ))
            elif step_name in errors_by_step:
                errors = errors_by_step[step_name]
                step_results.append(StepResult(
                    step_name=step_name,
                    status="error",
                    duration_seconds=0.0,
                    records_processed=0,
                    error_message=errors[0].error_message if errors else None
                ))
            else:
                # Step was skipped or not reached
                step_results.append(StepResult(
                    step_name=step_name,
                    status="skipped",
                    duration_seconds=0.0,
                    records_processed=0
                ))

        # Determine overall status
        if not context.has_errors():
            status = "success"
            error_message = None
        elif len(successful_steps) > 0:
            status = "partial"
            error_message = f"{len(context.errors)} step(s) failed"
        else:
            status = "failed"
            error_message = f"Pipeline failed: {len(context.errors)} error(s)"

        return PipelineExecutionResult(
            run_id=context.run_id,
            pipeline_name=context.pipeline_name,
            status=status,
            started_at=context.started_at,
            completed_at=completed_at,
            duration_seconds=duration_seconds,
            steps=step_results,
            metadata=context.metadata,
            error_message=error_message
        )
