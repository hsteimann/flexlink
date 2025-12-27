"""Tests for pipeline orchestrator."""

import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from flexlink.core.pipeline_orchestrator import PipelineOrchestrator
from flexlink.core.pipeline_registry import PipelineRegistry
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.transformation import TransformationEngine
from flexlink.models.pipeline import (
    PipelineConfig,
    PipelineStepConfig,
    StepType,
    ErrorStrategy,
    RetryPolicy
)
from flexlink.models.connector import ConnectorConfig, AuthConfig
from flexlink.connectors.rest_connector import RestConnector


# Fixtures

@pytest.fixture
async def http_client():
    """Create async HTTP client."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def connector_registry(http_client):
    """Create connector registry with test connectors."""
    registry = ConnectorRegistry()

    # Register a test REST connector
    rest_config = ConnectorConfig(
        name="test-source",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(type="none", credentials={}),
        timeout=30,
        enabled=True
    )
    rest_connector = RestConnector(rest_config, http_client)
    registry._connectors["test-source"] = rest_connector

    # Register output connector
    output_config = ConnectorConfig(
        name="test-output",
        type="rest",
        base_url="https://output.example.com",
        auth=AuthConfig(type="none", credentials={}),
        timeout=30,
        enabled=True
    )
    output_connector = RestConnector(output_config, http_client)
    registry._connectors["test-output"] = output_connector

    return registry


@pytest.fixture
def pipeline_registry(tmp_path):
    """Create pipeline registry with test pipelines."""
    config_dir = tmp_path / "pipelines"
    config_dir.mkdir()

    # Create simple ETL pipeline
    pipeline_yaml = config_dir / "simple-etl.yaml"
    pipeline_yaml.write_text("""
name: simple-etl
steps:
  - name: extract
    type: extract
    connector: test-source
    method: GET
    path: /data
    on_error: fail_pipeline

  - name: load
    type: load
    connector: test-output
    on_error: fail_pipeline
""")

    registry = PipelineRegistry(config_dir=config_dir)
    registry.load_pipelines()
    return registry


@pytest.fixture
def transformation_engine():
    """Create transformation engine."""
    return TransformationEngine(rules=[])


@pytest.fixture
def orchestrator(pipeline_registry, connector_registry, transformation_engine):
    """Create pipeline orchestrator."""
    return PipelineOrchestrator(
        pipeline_registry=pipeline_registry,
        connector_registry=connector_registry,
        transformation_engine=transformation_engine
    )


# Tests

@pytest.mark.asyncio
@respx.mock
async def test_execute_simple_pipeline(orchestrator):
    """Test executing a simple extract-load pipeline."""
    # Mock extract endpoint
    respx.get("https://api.example.com/data").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "value": "A"},
            {"id": 2, "value": "B"}
        ])
    )

    # Mock load endpoint
    respx.post("https://output.example.com").mock(
        return_value=httpx.Response(201, json={"success": True})
    )

    # Execute pipeline
    result = await orchestrator.execute_pipeline("simple-etl")

    # Verify result
    assert result.status == "success"
    assert result.pipeline_name == "simple-etl"
    assert len(result.steps) == 2
    assert result.steps[0].step_name == "extract"
    assert result.steps[0].status == "success"
    assert result.steps[1].step_name == "load"
    assert result.steps[1].status == "success"
    assert result.error_message is None


@pytest.mark.asyncio
async def test_execute_pipeline_with_error_fail_strategy(pipeline_registry, connector_registry, transformation_engine):
    """Test pipeline stops on error with fail_pipeline strategy."""
    # Create pipeline with multiple steps
    config = PipelineConfig(
        name="test-fail",
        steps=[
            PipelineStepConfig(
                name="step1",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/fail",
                on_error=ErrorStrategy.FAIL_PIPELINE
            ),
            PipelineStepConfig(
                name="step2",
                type=StepType.LOAD,
                connector="test-output",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ]
    )
    pipeline_registry._pipelines["test-fail"] = config

    orchestrator = PipelineOrchestrator(
        pipeline_registry=pipeline_registry,
        connector_registry=connector_registry,
        transformation_engine=transformation_engine
    )

    # Mock failing extract
    with respx.mock:
        respx.get("https://api.example.com/fail").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )

        # Execute pipeline
        result = await orchestrator.execute_pipeline("test-fail")

    # Verify pipeline failed and step2 was skipped
    assert result.status == "failed"
    assert len(result.steps) == 2
    assert result.steps[0].status == "error"
    assert result.steps[1].status == "skipped"


@pytest.mark.asyncio
async def test_execute_pipeline_with_error_skip_strategy(pipeline_registry, connector_registry, transformation_engine):
    """Test pipeline skips failed step and continues."""
    # Create pipeline with skip strategy
    config = PipelineConfig(
        name="test-skip",
        steps=[
            PipelineStepConfig(
                name="step1",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data",
                on_error=ErrorStrategy.SKIP_STEP
            ),
            PipelineStepConfig(
                name="step2",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/data2",
                on_error=ErrorStrategy.SKIP_STEP
            )
        ]
    )
    pipeline_registry._pipelines["test-skip"] = config

    orchestrator = PipelineOrchestrator(
        pipeline_registry=pipeline_registry,
        connector_registry=connector_registry,
        transformation_engine=transformation_engine
    )

    # Mock responses
    with respx.mock:
        # Step 1 fails
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(500, json={"error": "Error"})
        )
        # Step 2 succeeds
        respx.get("https://api.example.com/data2").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )

        # Execute
        result = await orchestrator.execute_pipeline("test-skip")

    # Verify step1 failed but step2 succeeded
    assert result.status == "partial"
    assert result.steps[0].status == "error"
    assert result.steps[1].status == "success"


@pytest.mark.asyncio
async def test_retry_logic(pipeline_registry, connector_registry, transformation_engine):
    """Test step retry with exponential backoff."""
    # Create pipeline with retry policy
    config = PipelineConfig(
        name="test-retry",
        steps=[
            PipelineStepConfig(
                name="extract",
                type=StepType.EXTRACT,
                connector="test-source",
                method="GET",
                path="/flaky",
                retry_policy=RetryPolicy(
                    max_attempts=3,
                    backoff_strategy="exponential",
                    initial_delay_seconds=0.1,
                    backoff_factor=2.0
                ),
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ]
    )
    pipeline_registry._pipelines["test-retry"] = config

    orchestrator = PipelineOrchestrator(
        pipeline_registry=pipeline_registry,
        connector_registry=connector_registry,
        transformation_engine=transformation_engine
    )

    # Mock flaky endpoint (fails twice, succeeds third time)
    with respx.mock:
        route = respx.get("https://api.example.com/flaky")
        route.side_effect = [
            httpx.Response(500, json={"error": "Error"}),
            httpx.Response(500, json={"error": "Error"}),
            httpx.Response(200, json=[{"id": 1}])
        ]

        # Execute
        result = await orchestrator.execute_pipeline("test-retry")

    # Verify succeeded after retries
    assert result.status == "success"
    assert result.steps[0].status == "success"
    assert route.call_count == 3


@pytest.mark.asyncio
async def test_backoff_delay_calculation(orchestrator):
    """Test backoff delay calculation."""
    policy = RetryPolicy(
        max_attempts=3,
        backoff_strategy="exponential",
        initial_delay_seconds=1.0,
        backoff_factor=2.0
    )

    # Calculate delays (with jitter, so check range)
    delay1 = orchestrator._calculate_backoff_delay(1, policy)
    delay2 = orchestrator._calculate_backoff_delay(2, policy)
    delay3 = orchestrator._calculate_backoff_delay(3, policy)

    # Check approximate ranges (±20% jitter)
    assert 0.8 <= delay1 <= 1.2  # 1.0 ± 20%
    assert 1.6 <= delay2 <= 2.4  # 2.0 ± 20%
    assert 3.2 <= delay3 <= 4.8  # 4.0 ± 20%


@pytest.mark.asyncio
async def test_backoff_linear_strategy(orchestrator):
    """Test linear backoff strategy."""
    policy = RetryPolicy(
        max_attempts=3,
        backoff_strategy="linear",
        initial_delay_seconds=1.0
    )

    delay1 = orchestrator._calculate_backoff_delay(1, policy)
    delay2 = orchestrator._calculate_backoff_delay(2, policy)

    # Linear: delay = initial_delay * attempt
    # Check ranges (with jitter)
    assert 0.8 <= delay1 <= 1.2  # 1.0 ± 20%
    assert 1.6 <= delay2 <= 2.4  # 2.0 ± 20%


@pytest.mark.asyncio
async def test_backoff_fixed_strategy(orchestrator):
    """Test fixed backoff strategy."""
    policy = RetryPolicy(
        max_attempts=3,
        backoff_strategy="fixed",
        initial_delay_seconds=1.0
    )

    delay1 = orchestrator._calculate_backoff_delay(1, policy)
    delay2 = orchestrator._calculate_backoff_delay(2, policy)

    # Fixed: always initial_delay
    # Check ranges (with jitter)
    assert 0.8 <= delay1 <= 1.2  # 1.0 ± 20%
    assert 0.8 <= delay2 <= 1.2  # 1.0 ± 20%


@pytest.mark.asyncio
async def test_result_building(orchestrator):
    """Test execution result building."""
    # Mock successful execution
    with respx.mock:
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(200, json=[{"id": 1}])
        )
        respx.post("https://output.example.com").mock(
            return_value=httpx.Response(201, json={"success": True})
        )

        result = await orchestrator.execute_pipeline("simple-etl")

    # Verify result structure
    assert result.run_id is not None
    assert result.pipeline_name == "simple-etl"
    assert result.started_at is not None
    assert result.completed_at is not None
    assert result.duration_seconds > 0
    assert isinstance(result.steps, list)
    assert result.metadata is not None


@pytest.mark.asyncio
async def test_pipeline_not_found(orchestrator):
    """Test error when pipeline doesn't exist."""
    with pytest.raises(KeyError, match="Pipeline 'nonexistent' not found"):
        await orchestrator.execute_pipeline("nonexistent")


@pytest.mark.asyncio
async def test_context_mutation(orchestrator):
    """Test that context is properly mutated across steps."""
    # This test verifies that the same context object is passed through
    # all steps and data is properly accumulated

    with respx.mock:
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}])
        )
        respx.post("https://output.example.com").mock(
            return_value=httpx.Response(201, json={"success": True})
        )

        result = await orchestrator.execute_pipeline("simple-etl")

    # Verify metadata was updated
    assert result.metadata.records_extracted == 2
    assert result.metadata.records_loaded == 2


# Tests for input conversion and seeding


@pytest.mark.asyncio
async def test_pipeline_with_single_record_input(pipeline_registry, connector_registry, transformation_engine):
    """Test pipeline execution with single record input (dict without wrapper)."""
    # Create transform-load pipeline (no EXTRACT step)
    config = PipelineConfig(
        name="webhook-processor",
        steps=[
            PipelineStepConfig(
                name="load",
                type=StepType.LOAD,
                connector="test-output",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ]
    )
    pipeline_registry._pipelines["webhook-processor"] = config

    orchestrator = PipelineOrchestrator(
        pipeline_registry=pipeline_registry,
        connector_registry=connector_registry,
        transformation_engine=transformation_engine
    )

    # Mock load endpoint
    with respx.mock:
        respx.post("https://output.example.com").mock(
            return_value=httpx.Response(201, json={"success": True})
        )

        # Execute with single record input
        result = await orchestrator.execute_pipeline(
            pipeline_name="webhook-processor",
            inputs={"id": 1, "name": "Test", "status": "active"}
        )

    # Verify
    assert result.status == "success"
    assert result.metadata.records_extracted == 1  # Seeded from inputs
    assert result.metadata.records_loaded == 1


@pytest.mark.asyncio
async def test_pipeline_with_multiple_records_input(pipeline_registry, connector_registry, transformation_engine):
    """Test pipeline with nested records list."""
    # Create pipeline with LOAD only
    config = PipelineConfig(
        name="batch-processor",
        steps=[
            PipelineStepConfig(
                name="load",
                type=StepType.LOAD,
                connector="test-output",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ]
    )
    pipeline_registry._pipelines["batch-processor"] = config

    orchestrator = PipelineOrchestrator(
        pipeline_registry=pipeline_registry,
        connector_registry=connector_registry,
        transformation_engine=transformation_engine
    )

    # Mock load endpoint
    with respx.mock:
        respx.post("https://output.example.com").mock(
            return_value=httpx.Response(201, json={"success": True})
        )

        # Execute with multiple records
        result = await orchestrator.execute_pipeline(
            pipeline_name="batch-processor",
            inputs={
                "records": [
                    {"id": 1, "name": "Item 1"},
                    {"id": 2, "name": "Item 2"},
                    {"id": 3, "name": "Item 3"}
                ]
            }
        )

    # Verify
    assert result.status == "success"
    assert result.metadata.records_extracted == 3
    assert result.metadata.records_loaded == 3


@pytest.mark.asyncio
async def test_pipeline_without_inputs(orchestrator):
    """Test pipeline without inputs (existing behavior)."""
    # Mock responses
    with respx.mock:
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}])
        )
        respx.post("https://output.example.com").mock(
            return_value=httpx.Response(201, json={"success": True})
        )

        # Execute without inputs (None is default)
        result = await orchestrator.execute_pipeline("simple-etl")

    # EXTRACT step populates context.data
    assert result.status == "success"
    assert result.metadata.records_extracted == 2  # From EXTRACT step, not inputs


@pytest.mark.asyncio
@pytest.mark.parametrize("inputs,expected_count", [
    ({"data": [{"id": 1}]}, 1),  # 'data' key
    ({"items": [{"id": 1}, {"id": 2}]}, 2),  # 'items' key
    ({"records": []}, 0),  # Empty list
    ({"key": "value"}, 1),  # No list key - single record
])
async def test_input_format_variations(pipeline_registry, connector_registry, transformation_engine, inputs, expected_count):
    """Test various input format patterns."""
    # Create simple load pipeline
    config = PipelineConfig(
        name="flexible-processor",
        steps=[
            PipelineStepConfig(
                name="load",
                type=StepType.LOAD,
                connector="test-output",
                on_error=ErrorStrategy.FAIL_PIPELINE
            )
        ]
    )
    pipeline_registry._pipelines["flexible-processor"] = config

    orchestrator = PipelineOrchestrator(
        pipeline_registry=pipeline_registry,
        connector_registry=connector_registry,
        transformation_engine=transformation_engine
    )

    # Mock load endpoint
    with respx.mock:
        respx.post("https://output.example.com").mock(
            return_value=httpx.Response(201, json={"success": True})
        )

        result = await orchestrator.execute_pipeline(
            pipeline_name="flexible-processor",
            inputs=inputs
        )

    assert result.metadata.records_extracted == expected_count


@pytest.mark.asyncio
async def test_backward_compatibility_with_extract(orchestrator):
    """Ensure inputs don't interfere with EXTRACT steps."""
    # Pipeline: EXTRACT -> LOAD
    with respx.mock:
        respx.get("https://api.example.com/data").mock(
            return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}, {"id": 3}])
        )
        respx.post("https://output.example.com").mock(
            return_value=httpx.Response(201, json={"success": True})
        )

        # Execute with inputs (should be overridden by EXTRACT)
        result = await orchestrator.execute_pipeline(
            pipeline_name="simple-etl",
            inputs={"should": "be_overridden"}  # Initial seed
        )

    # Verify EXTRACT step data is used (3 records from API, not 1 from inputs)
    # Note: Initial inputs seed context with 1 record, but EXTRACT step
    # replaces context.data with its extracted data (3 records)
    assert result.status == "success"
    assert result.metadata.records_extracted == 3  # From EXTRACT step


@pytest.mark.asyncio
async def test_convert_inputs_to_records_none(orchestrator):
    """Test _convert_inputs_to_records with None input."""
    result = orchestrator._convert_inputs_to_records(None)
    assert result == []


@pytest.mark.asyncio
async def test_convert_inputs_to_records_single_dict(orchestrator):
    """Test _convert_inputs_to_records with single dict."""
    result = orchestrator._convert_inputs_to_records({"id": 1, "name": "Test"})
    assert result == [{"id": 1, "name": "Test"}]


@pytest.mark.asyncio
async def test_convert_inputs_to_records_nested_list(orchestrator):
    """Test _convert_inputs_to_records with nested list under 'records' key."""
    inputs = {
        "records": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ]
    }
    result = orchestrator._convert_inputs_to_records(inputs)
    assert result == inputs["records"]
    assert len(result) == 2


@pytest.mark.asyncio
async def test_convert_inputs_to_records_data_key(orchestrator):
    """Test _convert_inputs_to_records with 'data' key."""
    inputs = {"data": [{"id": 1}]}
    result = orchestrator._convert_inputs_to_records(inputs)
    assert result == [{"id": 1}]


@pytest.mark.asyncio
async def test_convert_inputs_to_records_items_key(orchestrator):
    """Test _convert_inputs_to_records with 'items' key."""
    inputs = {"items": [{"id": 1}, {"id": 2}]}
    result = orchestrator._convert_inputs_to_records(inputs)
    assert result == inputs["items"]
    assert len(result) == 2
