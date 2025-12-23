"""Integration tests for full request flow."""

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
import respx

from flexlink.connectors.rest_connector import RestConnector
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.request import IntegrationRequest
from flexlink.models.transformation import RouteConfig, TransformationRule


@pytest.fixture
def http_client():
    """Create HTTP client for tests."""
    return httpx.AsyncClient()


@pytest.fixture
async def registry_with_rest_connector(http_client):
    """Create registry with REST connector."""
    registry = ConnectorRegistry()

    # Add REST connector
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["test_api"] = connector

    return registry


@pytest.fixture
def router_with_routes(registry_with_rest_connector):
    """Create router with configured routes."""
    router = RequestRouter(registry_with_rest_connector)

    # Add routes with transformations
    routes = [
        RouteConfig(
            path="/users",
            method="POST",
            connector="test_api",
            target_path="/api/users",
            transformations=[
                TransformationRule(
                    source_field="firstName",
                    target_field="first_name",
                    transformation="upper",
                ),
                TransformationRule(
                    source_field="lastName",
                    target_field="last_name",
                    transformation="upper",
                ),
                TransformationRule(
                    source_field="age", target_field="age", transformation="int"
                ),
            ],
        ),
        RouteConfig(
            path="/users/{id}",
            method="GET",
            connector="test_api",
            target_path="/api/users/{id}",
            transformations=[],
        ),
        RouteConfig(
            path="/posts/*",
            method="GET",
            connector="test_api",
            target_path="/api/posts",
            transformations=[],
        ),
    ]

    router.add_routes(routes)
    return router


@pytest.mark.asyncio
@respx.mock
async def test_full_request_flow_with_transformations(router_with_routes):
    """Test complete request flow with transformations."""
    # Mock API response
    respx.post("https://api.test.com/api/users").mock(
        return_value=httpx.Response(
            200, json={"id": 1, "first_name": "ALICE", "last_name": "SMITH", "age": 30}
        )
    )

    # Create request
    request = IntegrationRequest(
        route="/users",
        method="POST",
        body={"firstName": "alice", "lastName": "smith", "age": "30"},
    )

    # Route request
    response = await router_with_routes.route_request(request)

    # Verify response
    assert response.status_code == 200
    assert response.body["first_name"] == "ALICE"
    assert response.body["last_name"] == "SMITH"
    assert response.body["age"] == 30


@pytest.mark.asyncio
@respx.mock
async def test_full_request_flow_without_transformations(router_with_routes):
    """Test request flow without transformations."""
    # Mock API response
    respx.get("https://api.test.com/api/users/123").mock(
        return_value=httpx.Response(
            200, json={"id": 123, "name": "John Doe", "email": "john@test.com"}
        )
    )

    # Create request
    request = IntegrationRequest(route="/users/123", method="GET")

    # Route request
    response = await router_with_routes.route_request(request)

    # Verify response
    assert response.status_code == 200
    assert response.body["id"] == 123
    assert response.body["name"] == "John Doe"


@pytest.mark.asyncio
@respx.mock
async def test_full_request_flow_wildcard_route(router_with_routes):
    """Test request flow with wildcard route matching."""
    # Mock API response
    respx.get("https://api.test.com/api/posts").mock(
        return_value=httpx.Response(
            200, json=[{"id": 1, "title": "Post 1"}, {"id": 2, "title": "Post 2"}]
        )
    )

    # Create request with wildcard path
    request = IntegrationRequest(route="/posts/recent", method="GET")

    # Route request
    response = await router_with_routes.route_request(request)

    # Verify response
    assert response.status_code == 200
    assert len(response.body) == 2


@pytest.mark.asyncio
@respx.mock
async def test_request_flow_with_headers(registry_with_rest_connector):
    """Test request flow preserves custom headers."""
    router = RequestRouter(registry_with_rest_connector)

    # Add route
    router.add_route(
        RouteConfig(
            path="/secure",
            method="GET",
            connector="test_api",
            target_path="/api/secure",
            transformations=[],
        )
    )

    # Mock API response
    route = respx.get("https://api.test.com/api/secure").mock(
        return_value=httpx.Response(200, json={"status": "authorized"})
    )

    # Create request with headers
    request = IntegrationRequest(
        route="/secure", method="GET", headers={"Authorization": "Bearer token123"}
    )

    # Route request
    response = await router.route_request(request)

    # Verify response
    assert response.status_code == 200

    # Verify headers were sent
    assert route.calls.last.request.headers["Authorization"] == "Bearer token123"


@pytest.mark.asyncio
@respx.mock
async def test_request_flow_handles_api_errors(router_with_routes):
    """Test request flow handles API errors gracefully."""
    # Mock API error response
    respx.post("https://api.test.com/api/users").mock(
        return_value=httpx.Response(400, json={"error": "Invalid data"})
    )

    # Create request
    request = IntegrationRequest(
        route="/users", method="POST", body={"firstName": "alice"}
    )

    # Route request
    response = await router_with_routes.route_request(request)

    # Verify error response
    assert response.status_code == 400
    assert "error" in response.error or "error" in str(response.body)


@pytest.mark.asyncio
async def test_request_flow_no_matching_route(registry_with_rest_connector):
    """Test request flow when no route matches."""
    router = RequestRouter(registry_with_rest_connector)

    # Create request for non-existent route
    request = IntegrationRequest(route="/unknown", method="GET")

    # Route request
    response = await router.route_request(request)

    # Verify 404 response
    assert response.status_code == 404
    assert "No route configured" in response.error


@pytest.mark.asyncio
async def test_request_flow_transformation_error(registry_with_rest_connector):
    """Test request flow when transformation fails."""
    router = RequestRouter(registry_with_rest_connector)

    # Add route with transformation that will fail
    router.add_route(
        RouteConfig(
            path="/convert",
            method="POST",
            connector="test_api",
            target_path="/api/convert",
            transformations=[
                TransformationRule(
                    source_field="age", target_field="age", transformation="int"
                )
            ],
        )
    )

    # Create request with invalid data for transformation
    request = IntegrationRequest(
        route="/convert", method="POST", body={"age": "not_a_number"}
    )

    # Route request
    response = await router.route_request(request)

    # Verify transformation error
    assert response.status_code == 400
    assert "transformation failed" in response.error.lower()


@pytest.mark.asyncio
@respx.mock
async def test_request_flow_multiple_transformations(registry_with_rest_connector):
    """Test request flow with multiple chained transformations."""
    router = RequestRouter(registry_with_rest_connector)

    # Add route with multiple transformations
    router.add_route(
        RouteConfig(
            path="/complex",
            method="POST",
            connector="test_api",
            target_path="/api/complex",
            transformations=[
                TransformationRule(
                    source_field="name",
                    target_field="user.name",
                    transformation="strip",
                ),
                TransformationRule(
                    source_field="email",
                    target_field="user.email",
                    transformation="lower",
                ),
                TransformationRule(
                    source_field="active",
                    target_field="user.is_active",
                    transformation="bool",
                ),
                TransformationRule(
                    source_field="count",
                    target_field="user.count",
                    transformation="int",
                ),
            ],
        )
    )

    # Mock API response
    respx.post("https://api.test.com/api/complex").mock(
        return_value=httpx.Response(200, json={"status": "created"})
    )

    # Create request
    request = IntegrationRequest(
        route="/complex",
        method="POST",
        body={"name": "  Alice  ", "email": "ALICE@TEST.COM", "active": "true", "count": "42"},
    )

    # Route request
    response = await router.route_request(request)

    # Verify response
    assert response.status_code == 200
