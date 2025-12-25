"""
Integration tests for query parameter forwarding through the full request flow.

Tests the complete path: API endpoint -> Router -> Connector -> HTTP request
"""

import httpx
import pytest
import respx

from flexlink.connectors.rest_connector import RestConnector
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.request import IntegrationRequest
from flexlink.models.transformation import RouteConfig


@pytest.fixture
def http_client():
    """Create HTTP client for tests."""
    return httpx.AsyncClient()


@pytest.fixture
async def registry_with_connector(http_client):
    """Create registry with test connector."""
    registry = ConnectorRegistry()

    config = ConnectorConfig(
        name="testapi",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["testapi"] = connector

    return registry


@pytest.fixture
def router_with_routes(registry_with_connector):
    """Create router with configured routes."""
    router = RequestRouter(registry_with_connector)

    routes = [
        RouteConfig(
            path="/items",
            method="GET",
            connector="testapi",
            target_path="/api/items",
            transformations=[],
        ),
        RouteConfig(
            path="/items/{id}",
            method="DELETE",
            connector="testapi",
            target_path="/api/items/{id}",
            transformations=[],
        ),
        RouteConfig(
            path="/search",
            method="POST",
            connector="testapi",
            target_path="/api/search",
            transformations=[],
        ),
    ]

    router.add_routes(routes)
    return router


@pytest.mark.asyncio
@respx.mock
async def test_get_request_forwards_query_params(router_with_routes):
    """Test GET request with query params forwarded correctly."""
    # Mock API endpoint
    route = respx.get("https://api.test.com/api/items").mock(
        return_value=httpx.Response(
            200,
            json={"items": [{"id": 1, "name": "Item 1"}], "total": 1}
        )
    )

    # Create request with query params
    request = IntegrationRequest(
        route="/items",
        method="GET",
        query_params={"category": "electronics", "limit": "10", "offset": "0"}
    )

    # Route request
    response = await router_with_routes.route_request(request)

    # Verify response
    assert response.status_code == 200
    assert "items" in response.body

    # Verify query params were forwarded to HTTP request
    http_request = route.calls.last.request
    assert "category=electronics" in str(http_request.url)
    assert "limit=10" in str(http_request.url)
    assert "offset=0" in str(http_request.url)
    # GET should not have body
    assert http_request.content == b""


@pytest.mark.asyncio
@respx.mock
async def test_delete_request_forwards_query_params(router_with_routes):
    """Test DELETE request with query params forwarded correctly."""
    # Mock API endpoint
    route = respx.delete("https://api.test.com/api/items/123").mock(
        return_value=httpx.Response(204)
    )

    # Create request with query params
    request = IntegrationRequest(
        route="/items/123",
        method="DELETE",
        query_params={"force": "true", "cascade": "false"}
    )

    # Route request
    response = await router_with_routes.route_request(request)

    # Verify response
    assert response.status_code == 204

    # Verify query params were forwarded
    http_request = route.calls.last.request
    assert "force=true" in str(http_request.url)
    assert "cascade=false" in str(http_request.url)
    # DELETE should not have body
    assert http_request.content == b""


@pytest.mark.asyncio
@respx.mock
async def test_post_request_uses_body_not_query_params(router_with_routes):
    """Test POST request uses body, query params still forwarded if provided."""
    # Mock API endpoint
    route = respx.post("https://api.test.com/api/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    # Create POST request with body and query params
    request = IntegrationRequest(
        route="/search",
        method="POST",
        body={"query": "laptop", "filters": {"price_max": 1000}},
        query_params={"page": "1", "per_page": "20"}
    )

    # Route request
    response = await router_with_routes.route_request(request)

    # Verify response
    assert response.status_code == 200

    # Verify both body and query params forwarded
    http_request = route.calls.last.request
    assert "page=1" in str(http_request.url)
    assert "per_page=20" in str(http_request.url)

    # POST should have JSON body
    assert http_request.content != b""
    import json
    body = json.loads(http_request.content)
    assert body["query"] == "laptop"
    assert body["filters"]["price_max"] == 1000


@pytest.mark.asyncio
@respx.mock
async def test_get_without_query_params(router_with_routes):
    """Test GET request without query params works."""
    # Mock API endpoint
    route = respx.get("https://api.test.com/api/items").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    # Create request without query params
    request = IntegrationRequest(
        route="/items",
        method="GET",
        query_params={}
    )

    # Route request
    response = await router_with_routes.route_request(request)

    # Verify response
    assert response.status_code == 200

    # Verify no query params in URL
    http_request = route.calls.last.request
    # URL should not have query string or should end with ?
    url_str = str(http_request.url)
    assert "?" not in url_str or url_str.endswith("?")


@pytest.mark.asyncio
@respx.mock
async def test_query_params_with_transformations(registry_with_connector):
    """Test query params work with request transformations."""
    router = RequestRouter(registry_with_connector)

    # Add route with transformations
    router.add_route(
        RouteConfig(
            path="/items",
            method="GET",
            connector="testapi",
            target_path="/api/items",
            transformations=[],  # Could add transformations here
        )
    )

    # Mock API endpoint
    route = respx.get("https://api.test.com/api/items").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    # Create request with query params
    request = IntegrationRequest(
        route="/items",
        method="GET",
        query_params={"status": "active", "sort": "created_desc"}
    )

    # Route request
    response = await router.route_request(request)

    # Verify query params forwarded correctly
    http_request = route.calls.last.request
    assert "status=active" in str(http_request.url)
    assert "sort=created_desc" in str(http_request.url)


@pytest.mark.asyncio
@respx.mock
async def test_path_params_and_query_params_together(registry_with_connector):
    """Test path parameters and query parameters work together."""
    router = RequestRouter(registry_with_connector)

    # Add route with path parameter
    router.add_route(
        RouteConfig(
            path="/users/{user_id}/items",
            method="GET",
            connector="testapi",
            target_path="/api/users/{user_id}/items",
            transformations=[],
        )
    )

    # Mock API endpoint
    route = respx.get("https://api.test.com/api/users/456/items").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    # Create request with both path params (in route) and query params
    request = IntegrationRequest(
        route="/users/456/items",
        method="GET",
        query_params={"active": "true", "limit": "5"}
    )

    # Route request
    response = await router.route_request(request)

    # Verify both path and query params worked
    assert response.status_code == 200
    http_request = route.calls.last.request

    # Path param substituted
    assert "/users/456/items" in str(http_request.url)

    # Query params appended
    assert "active=true" in str(http_request.url)
    assert "limit=5" in str(http_request.url)


@pytest.mark.asyncio
@respx.mock
async def test_real_world_priceedge_scenario(registry_with_connector):
    """Test real-world scenario: filtering PriceEdge items with query params."""
    router = RequestRouter(registry_with_connector)

    # Add PriceEdge-style route
    router.add_route(
        RouteConfig(
            path="/pricing/items",
            method="GET",
            connector="testapi",
            target_path="/api/tables/item",
            transformations=[],
        )
    )

    # Mock PriceEdge API
    route = respx.get("https://api.test.com/api/tables/item").mock(
        return_value=httpx.Response(
            200,
            json={
                "Data": {
                    "data": [
                        {"cd_ItemNumber": "ITEM001", "cd_Description": "Product 1"}
                    ],
                    "total": 1
                }
            }
        )
    )

    # Create request with query filters (common PriceEdge pattern)
    request = IntegrationRequest(
        route="/pricing/items",
        method="GET",
        query_params={
            "cd_StoreNumber": "STORE01",
            "page": "1",
            "nrOfRecords": "100"
        }
    )

    # Route request
    response = await router.route_request(request)

    # Verify query params forwarded
    assert response.status_code == 200
    http_request = route.calls.last.request
    assert "cd_StoreNumber=STORE01" in str(http_request.url)
    assert "page=1" in str(http_request.url)
    assert "nrOfRecords=100" in str(http_request.url)
