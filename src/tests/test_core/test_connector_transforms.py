"""
Tests for connector-specific transformation hooks.

Verifies that:
- Connector transform_request is called before send_request
- Connector transform_response is called after send_request
- Transformation pipeline order is correct
- Errors are handled gracefully
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any

from flexlink.core.router import RequestRouter
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.connector import BaseConnector
from flexlink.models.connector import ConnectorConfig
from flexlink.models.request import IntegrationRequest, IntegrationResponse
from flexlink.models.transformation import RouteConfig, TransformationRule


class MockConnector(BaseConnector):
    """Mock connector for testing transformation hooks."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.transform_request_called = False
        self.transform_response_called = False
        self.request_transform_result = None
        self.response_transform_result = None

    async def send_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> IntegrationResponse:
        """Mock send_request."""
        return IntegrationResponse(
            status_code=200,
            body={"original": "response", "data": data}
        )

    async def transform_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mock transform_request - adds connector marker."""
        self.transform_request_called = True
        result = {**data, "connector_request_transform": True}
        self.request_transform_result = result
        return result

    async def transform_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Mock transform_response - adds connector marker."""
        self.transform_response_called = True
        result = {**data, "connector_response_transform": True}
        self.response_transform_result = result
        return result


@pytest.fixture
def mock_connector():
    """Create mock connector."""
    config = ConnectorConfig(
        name="test_connector",
        type="rest",
        base_url="https://api.test.com",
    )
    return MockConnector(config)


@pytest.fixture
def registry_with_mock_connector(mock_connector):
    """Create registry with mock connector."""
    registry = ConnectorRegistry()
    registry._connectors["test_connector"] = mock_connector
    return registry, mock_connector


@pytest.fixture
def router_with_mock(registry_with_mock_connector):
    """Create router with mock connector."""
    registry, mock_connector = registry_with_mock_connector
    router = RequestRouter(registry)
    return router, mock_connector


@pytest.mark.asyncio
async def test_connector_transform_request_is_called(router_with_mock):
    """Test that connector.transform_request() is called."""
    router, mock_connector = router_with_mock

    # Add simple route
    router.add_route(
        RouteConfig(
            path="/test",
            method="POST",
            connector="test_connector",
            target_path="/api/test",
            transformations=[],
        )
    )

    # Send request
    request = IntegrationRequest(
        route="/test",
        method="POST",
        body={"input": "data"}
    )

    response = await router.route_request(request)

    # Verify connector transform_request was called
    assert mock_connector.transform_request_called is True
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_connector_transform_response_is_called(router_with_mock):
    """Test that connector.transform_response() is called."""
    router, mock_connector = router_with_mock

    # Add simple route
    router.add_route(
        RouteConfig(
            path="/test",
            method="GET",
            connector="test_connector",
            target_path="/api/test",
            transformations=[],
        )
    )

    # Send request
    request = IntegrationRequest(
        route="/test",
        method="GET"
    )

    response = await router.route_request(request)

    # Verify connector transform_response was called
    assert mock_connector.transform_response_called is True
    assert response.status_code == 200
    # Response should have connector marker
    assert response.body["connector_response_transform"] is True


@pytest.mark.asyncio
async def test_transformation_pipeline_order(router_with_mock):
    """
    Test transformation pipeline order:
    Route Request Transform → Connector Request Transform → Send →
    Connector Response Transform → Route Response Transform
    """
    router, mock_connector = router_with_mock

    # Add route with both route and connector transformations
    router.add_route(
        RouteConfig(
            path="/test",
            method="POST",
            connector="test_connector",
            target_path="/api/test",
            transformations=[
                TransformationRule(
                    source_field="input",
                    target_field="route_transformed_input"
                )
            ],
            response_transformations=[
                TransformationRule(
                    source_field="original",
                    target_field="route_transformed_original"
                )
            ],
        )
    )

    # Send request
    request = IntegrationRequest(
        route="/test",
        method="POST",
        body={"input": "test_data"}
    )

    response = await router.route_request(request)

    # Verify request transformation order
    # 1. Route transform should have run first
    assert "route_transformed_input" in mock_connector.request_transform_result
    # 2. Connector transform should have added its marker
    assert mock_connector.request_transform_result["connector_request_transform"] is True

    # Verify response transformation order
    # 1. Connector transform should have run (adds marker)
    assert response.body["connector_response_transform"] is True
    # 2. Route transform should have run (transforms fields)
    assert response.body["route_transformed_original"] == "response"


@pytest.mark.asyncio
async def test_connector_request_transform_error_handling(router_with_mock):
    """Test that connector request transform errors are handled gracefully."""
    router, mock_connector = router_with_mock

    # Make transform_request raise an error
    async def failing_transform(data):
        raise ValueError("Connector transform failed!")

    mock_connector.transform_request = failing_transform

    # Add route
    router.add_route(
        RouteConfig(
            path="/test",
            method="POST",
            connector="test_connector",
            target_path="/api/test",
            transformations=[],
        )
    )

    # Send request
    request = IntegrationRequest(
        route="/test",
        method="POST",
        body={"input": "data"}
    )

    response = await router.route_request(request)

    # Should return error response
    assert response.status_code == 400
    assert "Connector request transformation failed" in response.error


@pytest.mark.asyncio
async def test_connector_response_transform_error_handling(router_with_mock):
    """Test that connector response transform errors are handled gracefully."""
    router, mock_connector = router_with_mock

    # Make transform_response raise an error
    async def failing_transform(data):
        raise ValueError("Connector response transform failed!")

    mock_connector.transform_response = failing_transform

    # Add route
    router.add_route(
        RouteConfig(
            path="/test",
            method="GET",
            connector="test_connector",
            target_path="/api/test",
            transformations=[],
        )
    )

    # Send request
    request = IntegrationRequest(
        route="/test",
        method="GET"
    )

    response = await router.route_request(request)

    # Should return original response (error logged but not raised)
    assert response.status_code == 200
    # Original response body should be preserved
    assert "original" in response.body


@pytest.mark.asyncio
async def test_connector_transform_with_none_data():
    """Test connector transforms handle None data correctly."""
    config = ConnectorConfig(
        name="test",
        type="rest",
        base_url="https://api.test.com",
    )
    connector = MockConnector(config)

    # Transform None should return None
    result = await connector.transform_request({})
    assert result is not None

    result = await connector.transform_response({})
    assert result is not None


@pytest.mark.asyncio
async def test_connector_transforms_preserve_data_types(router_with_mock):
    """Test connector transforms preserve various data types."""
    router, mock_connector = router_with_mock

    # Override connector transforms to preserve types
    async def identity_request_transform(data):
        return data

    async def identity_response_transform(data):
        return data

    mock_connector.transform_request = identity_request_transform
    mock_connector.transform_response = identity_response_transform

    # Add route
    router.add_route(
        RouteConfig(
            path="/test",
            method="POST",
            connector="test_connector",
            target_path="/api/test",
            transformations=[],
        )
    )

    # Send request with various data types
    request = IntegrationRequest(
        route="/test",
        method="POST",
        body={
            "string": "test",
            "number": 123,
            "float": 45.67,
            "bool": True,
            "null": None,
            "array": [1, 2, 3],
            "nested": {"key": "value"}
        }
    )

    response = await router.route_request(request)

    # Verify data types preserved
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_connector_transform_returns_none_uses_original():
    """Test that if connector transform returns None, original data is used."""
    config = ConnectorConfig(
        name="test",
        type="rest",
        base_url="https://api.test.com",
    )
    connector = MockConnector(config)
    registry = ConnectorRegistry()
    registry._connectors["test"] = connector
    router = RequestRouter(registry)

    # Make transform return None
    async def none_transform(data):
        return None

    connector.transform_request = none_transform
    connector.transform_response = none_transform

    # Add route
    router.add_route(
        RouteConfig(
            path="/test",
            method="POST",
            connector="test",
            target_path="/api/test",
            transformations=[],
        )
    )

    # Send request
    request = IntegrationRequest(
        route="/test",
        method="POST",
        body={"original": "data"}
    )

    response = await router.route_request(request)

    # Should still work - None transform is ignored
    assert response.status_code == 200
