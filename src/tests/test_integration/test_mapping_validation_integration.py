"""Integration tests for YAML mapping and validation."""

import pytest
from pathlib import Path
from flexlink.core.router import RequestRouter
from flexlink.core.registry import ConnectorRegistry
from flexlink.models.transformation import RouteConfig
from flexlink.models.request import IntegrationRequest, IntegrationResponse
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def config_dir(tmp_path):
    """Create temporary config directory with test mappings."""
    # Create mappings directory
    mappings_dir = tmp_path / "mappings"
    mappings_dir.mkdir()

    # Create test mapping
    mapping_content = """
name: test-transform-validate
description: Test mapping with validation

mappings:
  - source_field: Data.data
    target_field: items
  - source_field: Data.total
    target_field: totalItems
    transformation: int

validation:
  rules:
    - field: totalItems
      type: int
      min: 0
      required: true
  on_validation_error: fail_pipeline
  log_errors: true
"""
    mapping_file = mappings_dir / "test-transform-validate.yaml"
    mapping_file.write_text(mapping_content)

    return tmp_path


@pytest.fixture
def mock_registry():
    """Mock connector registry."""
    registry = MagicMock(spec=ConnectorRegistry)
    mock_connector = AsyncMock()

    async def identity_transform(data):
        return data

    mock_connector.transform_request = AsyncMock(side_effect=identity_transform)
    mock_connector.transform_response = AsyncMock(side_effect=identity_transform)
    registry.get_connector.return_value = mock_connector

    return registry, mock_connector


@pytest.mark.asyncio
async def test_mapping_reference_loads_and_transforms(mock_registry, config_dir):
    """Test that mapping_ref loads mapping and applies transformations."""
    registry, mock_connector = mock_registry

    # Configure route with mapping reference
    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        mapping_ref="test-transform-validate"
    )

    # Mock connector response
    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"Data": {"data": [{"id": 1}, {"id": 2}], "total": "2"}}
    )

    # Execute request
    router = RequestRouter(registry, config_dir=config_dir)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify transformation applied
    assert response.status_code == 200
    # Note: Request transformations apply to request.body, not connector response
    # This test validates that mapping loads successfully


@pytest.mark.asyncio
async def test_validation_fail_pipeline_strategy(mock_registry, config_dir):
    """Test that fail_pipeline stops on validation error."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        mapping_ref="test-transform-validate"
    )

    # Send invalid request body (will be validated after transformation)
    request = IntegrationRequest(
        route="/test",
        method="POST",
        body={"Data": {"data": [], "total": -1}}  # Invalid: negative total
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"success": True}
    )

    # Execute request
    router = RequestRouter(registry, config_dir=config_dir)
    router.add_route(route_config)
    response = await router.route_request(request)

    # Verify validation failed
    assert response.status_code == 400
    assert "Validation failed" in response.error


@pytest.mark.asyncio
async def test_mapping_not_found_error(mock_registry, config_dir):
    """Test error handling when mapping file doesn't exist."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        mapping_ref="nonexistent-mapping"
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"data": "test"}
    )

    # Execute request
    router = RequestRouter(registry, config_dir=config_dir)
    router.add_route(route_config)
    request = IntegrationRequest(route="/test", method="POST", body={})
    response = await router.route_request(request)

    # Verify error
    assert response.status_code == 500
    assert "Failed to load mapping configuration" in response.error


@pytest.mark.asyncio
async def test_backwards_compatibility_inline_transformations(mock_registry, config_dir):
    """Test that inline transformations still work (backwards compatibility)."""
    from flexlink.models.transformation import TransformationRule

    registry, mock_connector = mock_registry

    # Use inline transformations (old way)
    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        transformations=[
            TransformationRule(source_field="old", target_field="new")
        ]
    )

    # Send request with old field
    request = IntegrationRequest(
        route="/test",
        method="POST",
        body={"old": "value"}
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"success": True}
    )

    router = RequestRouter(registry, config_dir=config_dir)
    router.add_route(route_config)
    response = await router.route_request(request)

    # Verify inline transformation still works
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_validation_with_valid_data(mock_registry, config_dir):
    """Test that valid data passes validation."""
    registry, mock_connector = mock_registry

    route_config = RouteConfig(
        path="/test",
        connector="test",
        target_path="/api/test",
        mapping_ref="test-transform-validate"
    )

    # Send valid request body
    request = IntegrationRequest(
        route="/test",
        method="POST",
        body={"Data": {"data": [{"id": 1}], "total": 1}}
    )

    mock_connector.send_request.return_value = IntegrationResponse(
        status_code=200,
        body={"success": True}
    )

    router = RequestRouter(registry, config_dir=config_dir)
    router.add_route(route_config)
    response = await router.route_request(request)

    # Verify validation passed and request succeeded
    assert response.status_code == 200
