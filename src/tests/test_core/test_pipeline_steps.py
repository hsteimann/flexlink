"""Tests for pipeline steps."""

import pytest
import respx
import httpx
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from flexlink.core.pipeline_steps import (
    ExtractStep,
    TransformStep,
    LoadStep,
    ExtractError,
    TransformError,
    LoadError,
    ValidationError
)
from flexlink.core.pipeline_context import PipelineRunContext
from flexlink.models.connector import ConnectorConfig, AuthConfig
from flexlink.models.pipeline import ExecutionMetadata
from flexlink.connectors.rest_connector import RestConnector


# Fixtures

@pytest.fixture
async def http_client():
    """Create async HTTP client."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def pipeline_context():
    """Create test pipeline context."""
    return PipelineRunContext(
        run_id="test-run-123",
        pipeline_name="test-pipeline",
        started_at=datetime.now(timezone.utc),
        data=[],
        metadata=ExecutionMetadata()
    )


@pytest.fixture
def rest_connector(http_client):
    """Create REST connector for testing."""
    config = ConnectorConfig(
        name="test-api",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(type="none", credentials={}),
        timeout=30,
        enabled=True
    )
    return RestConnector(config, http_client)


# ExtractStep Tests

@pytest.mark.asyncio
@respx.mock
async def test_extract_single_request(rest_connector, pipeline_context):
    """Test extracting data from single request."""
    # Mock API response
    respx.get("https://api.example.com/products").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "name": "Product 1"},
            {"id": 2, "name": "Product 2"}
        ])
    )

    # Create and execute step
    step = ExtractStep(
        connector=rest_connector,
        method="GET",
        path="/products"
    )
    await step.execute(pipeline_context)

    # Verify
    assert len(pipeline_context.data) == 2
    assert pipeline_context.data[0]["id"] == 1
    assert pipeline_context.metadata.records_extracted == 2


@pytest.mark.asyncio
@respx.mock
async def test_extract_with_nested_data(rest_connector, pipeline_context):
    """Test extracting nested data from response."""
    # Mock API with nested response
    respx.get("https://api.example.com/orders").mock(
        return_value=httpx.Response(200, json={
            "data": {
                "orders": [
                    {"id": 1, "status": "completed"},
                    {"id": 2, "status": "pending"}
                ]
            },
            "meta": {"total": 2}
        })
    )

    # Create step with data_path
    step = ExtractStep(
        connector=rest_connector,
        method="GET",
        path="/orders",
        pagination={"data_path": "data.orders"}
    )
    await step.execute(pipeline_context)

    # Verify
    assert len(pipeline_context.data) == 2
    assert pipeline_context.data[0]["id"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_extract_with_offset_pagination(rest_connector, pipeline_context):
    """Test offset-based pagination."""
    # Mock paginated responses
    respx.get("https://api.example.com/items?offset=0&limit=2").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1}, {"id": 2}
        ])
    )
    respx.get("https://api.example.com/items?offset=2&limit=2").mock(
        return_value=httpx.Response(200, json=[
            {"id": 3}
        ])
    )

    # Create step with pagination
    step = ExtractStep(
        connector=rest_connector,
        method="GET",
        path="/items",
        pagination={
            "enabled": True,
            "strategy": "offset",
            "page_size": 2,
            "max_pages": 10
        }
    )
    await step.execute(pipeline_context)

    # Verify all pages fetched
    assert len(pipeline_context.data) == 3
    assert pipeline_context.data[0]["id"] == 1
    assert pipeline_context.data[2]["id"] == 3


@pytest.mark.asyncio
@respx.mock
async def test_extract_with_cursor_pagination(rest_connector, pipeline_context):
    """Test cursor-based pagination."""
    # Mock cursor responses
    respx.get("https://api.example.com/data?limit=2").mock(
        return_value=httpx.Response(200, json={
            "data": [{"id": 1}, {"id": 2}],
            "pagination": {"next_cursor": "cursor_abc"}
        })
    )
    respx.get("https://api.example.com/data?cursor=cursor_abc&limit=2").mock(
        return_value=httpx.Response(200, json={
            "data": [{"id": 3}],
            "pagination": {"next_cursor": None}
        })
    )

    # Create step with cursor pagination
    step = ExtractStep(
        connector=rest_connector,
        method="GET",
        path="/data",
        pagination={
            "enabled": True,
            "strategy": "cursor",
            "page_size": 2,
            "max_pages": 10,
            "next_cursor_path": "pagination.next_cursor",
            "data_path": "data"
        }
    )
    await step.execute(pipeline_context)

    # Verify
    assert len(pipeline_context.data) == 3


@pytest.mark.asyncio
@respx.mock
async def test_extract_with_page_pagination(rest_connector, pipeline_context):
    """Test page number pagination."""
    # Mock page responses
    respx.get("https://api.example.com/items?page=1&page_size=2").mock(
        return_value=httpx.Response(200, json=[{"id": 1}, {"id": 2}])
    )
    respx.get("https://api.example.com/items?page=2&page_size=2").mock(
        return_value=httpx.Response(200, json=[{"id": 3}])
    )

    # Create step
    step = ExtractStep(
        connector=rest_connector,
        method="GET",
        path="/items",
        pagination={
            "enabled": True,
            "strategy": "page",
            "page_size": 2,
            "max_pages": 10,
            "start_page": 1
        }
    )
    await step.execute(pipeline_context)

    # Verify
    assert len(pipeline_context.data) == 3


@pytest.mark.asyncio
@respx.mock
async def test_extract_error_handling(rest_connector, pipeline_context):
    """Test extract step error handling."""
    # Mock failed response
    respx.get("https://api.example.com/fail").mock(
        return_value=httpx.Response(500, json={"error": "Internal Server Error"})
    )

    # Create step
    step = ExtractStep(
        connector=rest_connector,
        method="GET",
        path="/fail"
    )

    # Verify error raised
    with pytest.raises(ExtractError, match="HTTP 500"):
        await step.execute(pipeline_context)


# TransformStep Tests

@pytest.mark.asyncio
async def test_transform_basic(pipeline_context):
    """Test basic transformation."""
    # Setup context with data
    pipeline_context.data = [
        {"source_id": 1, "source_name": "Item 1"},
        {"source_id": 2, "source_name": "Item 2"}
    ]

    # Mock transformation engine
    mock_engine = MagicMock()
    mock_engine.apply.side_effect = lambda record, mappings: {
        "id": record["source_id"],
        "name": record["source_name"]
    }

    # Mock mapping config
    mock_mapping = MagicMock()
    mock_mapping.mappings = [{"from": "source_id", "to": "id"}]
    mock_mapping.validation = None

    # Create and execute step
    step = TransformStep(
        transformation_engine=mock_engine,
        mapping=mock_mapping
    )
    await step.execute(pipeline_context)

    # Verify
    assert len(pipeline_context.data) == 2
    assert pipeline_context.data[0]["id"] == 1
    assert pipeline_context.metadata.records_transformed == 2


@pytest.mark.asyncio
async def test_transform_with_validation_skip(pipeline_context):
    """Test transformation with validation that skips invalid records."""
    # Setup context
    pipeline_context.data = [
        {"value": 10},
        {"value": -5},  # Invalid
        {"value": 20}
    ]

    # Mock engine
    mock_engine = MagicMock()
    mock_engine.apply.side_effect = lambda record, mappings: record

    # Mock validation
    mock_validation_result = MagicMock()
    mock_engine.validator.validate.side_effect = [
        MagicMock(valid=True, errors=[]),
        MagicMock(valid=False, errors=["Value must be positive"]),
        MagicMock(valid=True, errors=[])
    ]

    mock_validation = MagicMock()
    mock_validation.rules = [{"field": "value", "min": 0}]
    mock_validation.on_validation_error = "skip_row"

    mock_mapping = MagicMock()
    mock_mapping.mappings = []
    mock_mapping.validation = mock_validation

    # Create and execute
    step = TransformStep(
        transformation_engine=mock_engine,
        mapping=mock_mapping
    )
    await step.execute(pipeline_context)

    # Verify invalid record skipped
    assert len(pipeline_context.data) == 2
    assert pipeline_context.data[0]["value"] == 10
    assert pipeline_context.data[1]["value"] == 20
    assert pipeline_context.metadata.validation_errors == 1


@pytest.mark.asyncio
async def test_transform_with_validation_fail(pipeline_context):
    """Test transformation that fails pipeline on validation error."""
    # Setup context
    pipeline_context.data = [{"value": -5}]

    # Mock engine
    mock_engine = MagicMock()
    mock_engine.apply.side_effect = lambda record, mappings: record
    mock_engine.validator.validate.return_value = MagicMock(
        valid=False,
        errors=["Value must be positive"]
    )

    mock_validation = MagicMock()
    mock_validation.rules = [{"field": "value", "min": 0}]
    mock_validation.on_validation_error = "fail_pipeline"

    mock_mapping = MagicMock()
    mock_mapping.mappings = []
    mock_mapping.validation = mock_validation

    # Create step
    step = TransformStep(
        transformation_engine=mock_engine,
        mapping=mock_mapping
    )

    # Verify error raised
    with pytest.raises(ValidationError, match="Validation failed"):
        await step.execute(pipeline_context)


@pytest.mark.asyncio
async def test_transform_empty_data(pipeline_context):
    """Test transform step with no data."""
    pipeline_context.data = []

    mock_engine = MagicMock()
    mock_mapping = MagicMock()

    step = TransformStep(
        transformation_engine=mock_engine,
        mapping=mock_mapping
    )
    await step.execute(pipeline_context)

    # Should complete without error
    assert len(pipeline_context.data) == 0


# LoadStep Tests

@pytest.mark.asyncio
@respx.mock
async def test_load_per_record(rest_connector, pipeline_context):
    """Test loading records one at a time."""
    # Setup context
    pipeline_context.data = [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"}
    ]

    # Mock endpoint
    respx.post("https://api.example.com/items").mock(
        return_value=httpx.Response(201, json={"success": True})
    )

    # Create and execute step
    step = LoadStep(
        connector=rest_connector,
        params={"path": "/items", "method": "POST"}
    )
    await step.execute(pipeline_context)

    # Verify
    assert pipeline_context.metadata.records_loaded == 2


@pytest.mark.asyncio
@respx.mock
async def test_load_batch(rest_connector, pipeline_context):
    """Test batch loading."""
    # Setup context
    pipeline_context.data = [
        {"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}
    ]

    # Mock batch endpoint
    respx.post("https://api.example.com/batch").mock(
        return_value=httpx.Response(200, json={"success": True})
    )

    # Create step with batch config
    step = LoadStep(
        connector=rest_connector,
        params={"path": "/batch", "method": "POST"},
        batch_config={
            "enabled": True,
            "batch_size": 3,
            "wrapper_key": "items"
        }
    )
    await step.execute(pipeline_context)

    # Verify - 5 records in batches of 3 = 2 batches
    assert pipeline_context.metadata.records_loaded == 5


@pytest.mark.asyncio
@respx.mock
async def test_load_partial_batch_failure(rest_connector, pipeline_context):
    """Test batch loading with partial failures."""
    # Setup context
    pipeline_context.data = [{"id": 1}, {"id": 2}, {"id": 3}]

    # Mock response with partial failures
    respx.post("https://api.example.com/batch").mock(
        return_value=httpx.Response(200, json={
            "results": [
                {"status": "success"},
                {"status": "error"},
                {"status": "success"}
            ]
        })
    )

    # Create step
    step = LoadStep(
        connector=rest_connector,
        params={"path": "/batch", "method": "POST"},
        batch_config={
            "enabled": True,
            "batch_size": 3,
            "status_field": "status",
            "success_values": ["success", "ok"]
        }
    )
    await step.execute(pipeline_context)

    # Verify - 2 successes, 1 failure
    assert pipeline_context.metadata.records_loaded == 2


@pytest.mark.asyncio
@respx.mock
async def test_load_all_records_fail(rest_connector, pipeline_context):
    """Test load step when all records fail."""
    # Setup context
    pipeline_context.data = [{"id": 1}]

    # Mock failed response
    respx.post("https://api.example.com/fail").mock(
        return_value=httpx.Response(500, text="Error")
    )

    # Create step
    step = LoadStep(
        connector=rest_connector,
        params={"path": "/fail", "method": "POST"}
    )

    # Verify error raised when all fail
    with pytest.raises(LoadError, match="All records failed to load"):
        await step.execute(pipeline_context)


@pytest.mark.asyncio
async def test_load_empty_data(rest_connector, pipeline_context):
    """Test load step with no data."""
    pipeline_context.data = []

    step = LoadStep(
        connector=rest_connector,
        params={"path": "/items", "method": "POST"}
    )
    await step.execute(pipeline_context)

    # Should complete without error
    assert pipeline_context.metadata.records_loaded == 0
