"""Tests for request router."""

from typing import Any
from unittest.mock import AsyncMock

import pytest

from flexlink.core.connector import BaseConnector
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.request import IntegrationRequest, IntegrationResponse
from flexlink.models.transformation import RouteConfig, TransformationRule


class MockConnector(BaseConnector):
    """Mock connector for testing."""

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.send_request_mock = AsyncMock(
            return_value=IntegrationResponse(
                status_code=200, body={"result": "success"}
            )
        )

    async def send_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> IntegrationResponse:
        return await self.send_request_mock(method, path, data, **kwargs)

    async def transform_request(self, data: dict[str, Any]) -> dict[str, Any]:
        return data

    async def transform_response(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


@pytest.fixture
def mock_registry():
    """Create mock connector registry."""
    registry = ConnectorRegistry()

    # Add mock connector
    config = ConnectorConfig(
        name="test_connector",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = MockConnector(config)
    registry._connectors["test_connector"] = connector

    return registry


@pytest.fixture
def router(mock_registry):
    """Create router with mock registry."""
    return RequestRouter(mock_registry)


@pytest.mark.asyncio
async def test_add_route(router):
    """Test adding a single route."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )

    router.add_route(route_config)

    assert len(router.routes) == 1
    assert router.routes[0] == route_config


@pytest.mark.asyncio
async def test_add_multiple_routes(router):
    """Test adding multiple routes."""
    routes = [
        RouteConfig(
            path="/api/users", method="POST", connector="test_connector", target_path="/users"
        ),
        RouteConfig(
            path="/api/posts", method="GET", connector="test_connector", target_path="/posts"
        ),
    ]

    router.add_routes(routes)

    assert len(router.routes) == 2


@pytest.mark.asyncio
async def test_exact_path_matching(router):
    """Test exact path matching."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    request = IntegrationRequest(route="/api/users", method="POST")

    matched = router._match_route(request)

    assert matched == route_config


@pytest.mark.asyncio
async def test_wildcard_path_matching(router):
    """Test wildcard path matching."""
    route_config = RouteConfig(
        path="/api/users/*",
        method="GET",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    request = IntegrationRequest(route="/api/users/123", method="GET")

    matched = router._match_route(request)

    assert matched == route_config


@pytest.mark.asyncio
async def test_path_parameter_matching(router):
    """Test path parameter matching."""
    route_config = RouteConfig(
        path="/api/users/{id}",
        method="GET",
        connector="test_connector",
        target_path="/users/{id}",
    )
    router.add_route(route_config)

    request = IntegrationRequest(route="/api/users/123", method="GET")

    matched = router._match_route(request)

    assert matched == route_config


@pytest.mark.asyncio
async def test_method_must_match(router):
    """Test that HTTP method must match for route matching."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    # Different method should not match
    request = IntegrationRequest(route="/api/users", method="GET")

    matched = router._match_route(request)

    assert matched is None


@pytest.mark.asyncio
async def test_no_matching_route(router):
    """Test handling when no route matches."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    request = IntegrationRequest(route="/api/posts", method="POST")

    matched = router._match_route(request)

    assert matched is None


@pytest.mark.asyncio
async def test_route_request_success(router, mock_registry):
    """Test successful request routing."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    request = IntegrationRequest(
        route="/api/users", method="POST", body={"name": "Alice"}
    )

    response = await router.route_request(request)

    assert response.status_code == 200
    assert response.body == {"result": "success"}

    # Verify connector was called
    connector = mock_registry.get_connector("test_connector")
    connector.send_request_mock.assert_called_once()


@pytest.mark.asyncio
async def test_route_request_with_transformations(router, mock_registry):
    """Test request routing with transformations applied."""
    transformations = [
        TransformationRule(
            source_field="firstName", target_field="first_name", transformation="upper"
        ),
        TransformationRule(source_field="age", target_field="age", transformation="int"),
    ]
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
        transformations=transformations,
    )
    router.add_route(route_config)

    request = IntegrationRequest(
        route="/api/users", method="POST", body={"firstName": "alice", "age": "30"}
    )

    response = await router.route_request(request)

    assert response.status_code == 200

    # Verify connector was called with transformed data
    connector = mock_registry.get_connector("test_connector")
    call_args = connector.send_request_mock.call_args
    # Data is passed as third positional argument (args[2])
    transformed_data = call_args.args[2]
    assert transformed_data["first_name"] == "ALICE"
    assert transformed_data["age"] == 30


@pytest.mark.asyncio
async def test_route_request_no_route_found(router):
    """Test routing request when no matching route exists."""
    request = IntegrationRequest(route="/api/unknown", method="POST")

    response = await router.route_request(request)

    assert response.status_code == 404
    assert "No route configured" in response.error


@pytest.mark.asyncio
async def test_route_request_connector_not_found(router):
    """Test routing request when connector doesn't exist."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="nonexistent_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    request = IntegrationRequest(route="/api/users", method="POST")

    response = await router.route_request(request)

    assert response.status_code == 500
    assert "Connector not found" in response.error


@pytest.mark.asyncio
async def test_route_request_transformation_failed(router):
    """Test routing request when transformation fails."""
    transformations = [
        TransformationRule(source_field="age", target_field="age", transformation="int")
    ]
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
        transformations=transformations,
    )
    router.add_route(route_config)

    # Invalid data for int transformation
    request = IntegrationRequest(
        route="/api/users", method="POST", body={"age": "not_a_number"}
    )

    response = await router.route_request(request)

    assert response.status_code == 400
    assert "transformation failed" in response.error.lower()


@pytest.mark.asyncio
async def test_route_request_connector_error(router, mock_registry):
    """Test routing request when connector raises exception."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    # Make connector raise exception
    connector = mock_registry.get_connector("test_connector")
    connector.send_request_mock.side_effect = Exception("Connection failed")

    request = IntegrationRequest(route="/api/users", method="POST")

    response = await router.route_request(request)

    assert response.status_code == 500
    assert "Connector request failed" in response.error


@pytest.mark.asyncio
async def test_route_request_empty_body(router, mock_registry):
    """Test routing request with no body."""
    route_config = RouteConfig(
        path="/api/users",
        method="GET",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    request = IntegrationRequest(route="/api/users", method="GET", body=None)

    response = await router.route_request(request)

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_routes(router):
    """Test listing all registered routes."""
    routes = [
        RouteConfig(
            path="/api/users", method="POST", connector="test_connector", target_path="/users"
        ),
        RouteConfig(
            path="/api/posts", method="GET", connector="test_connector", target_path="/posts"
        ),
    ]
    router.add_routes(routes)

    route_list = router.list_routes()

    assert len(route_list) == 2
    assert route_list[0]["method"] == "POST"
    assert route_list[0]["path"] == "/api/users"
    assert route_list[1]["method"] == "GET"
    assert route_list[1]["path"] == "/api/posts"


@pytest.mark.asyncio
async def test_clear_routes(router):
    """Test clearing all routes."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    assert len(router.routes) == 1

    router.clear_routes()

    assert len(router.routes) == 0


@pytest.mark.asyncio
async def test_multiple_routes_first_match_wins(router):
    """Test that first matching route is used when multiple routes match."""
    routes = [
        RouteConfig(
            path="/api/users/*",
            method="GET",
            connector="test_connector",
            target_path="/users/all",
        ),
        RouteConfig(
            path="/api/users/{id}",
            method="GET",
            connector="test_connector",
            target_path="/users/specific",
        ),
    ]
    router.add_routes(routes)

    request = IntegrationRequest(route="/api/users/123", method="GET")

    matched = router._match_route(request)

    # First route should match (both patterns would match)
    assert matched.target_path == "/users/all"


@pytest.mark.asyncio
async def test_case_insensitive_method_matching(router):
    """Test that HTTP method matching is case-insensitive."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    # Lowercase method should still match
    request = IntegrationRequest(route="/api/users", method="post")

    matched = router._match_route(request)

    assert matched == route_config


@pytest.mark.asyncio
async def test_headers_passed_to_connector(router, mock_registry):
    """Test that request headers are passed to connector."""
    route_config = RouteConfig(
        path="/api/users",
        method="POST",
        connector="test_connector",
        target_path="/users",
    )
    router.add_route(route_config)

    request = IntegrationRequest(
        route="/api/users",
        method="POST",
        headers={"Authorization": "Bearer token123"},
    )

    response = await router.route_request(request)

    assert response.status_code == 200

    # Verify headers were passed
    connector = mock_registry.get_connector("test_connector")
    call_args = connector.send_request_mock.call_args
    # Headers are passed as keyword argument
    assert call_args.kwargs["headers"]["Authorization"] == "Bearer token123"
