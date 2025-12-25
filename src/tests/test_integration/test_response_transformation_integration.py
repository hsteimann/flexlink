"""
Integration tests for response transformation with real connector setup.

Tests full end-to-end flow:
- Request routing
- Connector HTTP call
- Response transformation
- Error handling
"""

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
async def priceedge_registry(http_client):
    """Create registry with PriceEdge connector configuration."""
    registry = ConnectorRegistry()

    # Configure PriceEdge connector (matching real config)
    config = ConnectorConfig(
        name="priceedge",
        type="rest",
        base_url="https://api.priceedge.com",
        auth=AuthConfig(
            type="bearer",
            credentials={"token": "test_token_123"}
        ),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["priceedge"] = connector

    return registry


@pytest.fixture
def router_with_priceedge_routes(priceedge_registry):
    """Create router with PriceEdge routes including response transformations."""
    router = RequestRouter(priceedge_registry)

    # Add route matching priceedge_routes.yaml configuration
    router.add_route(
        RouteConfig(
            path="/pricing/suggested-prices",
            method="POST",
            connector="priceedge",
            target_path="/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price",
            transformations=[],
            response_transformations=[
                TransformationRule(
                    source_field="Data.data",
                    target_field="items"
                ),
                TransformationRule(
                    source_field="Data.total",
                    target_field="totalItems"
                )
            ]
        )
    )

    return router


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_response_transformation(router_with_priceedge_routes):
    """Test PriceEdge response transformation end-to-end."""
    # Mock PriceEdge API response (real format from PriceEdge)
    mock_priceedge_response = {
        "Data": {
            "data": [
                {
                    "cd_ItemNumber": "ITEM001",
                    "cd_StoreNumber": "STORE01",
                    "Value": 19.99,
                    "dt_Created": "2024-01-01T10:00:00Z"
                },
                {
                    "cd_ItemNumber": "ITEM002",
                    "cd_StoreNumber": "STORE01",
                    "Value": 29.99,
                    "dt_Created": "2024-01-01T10:00:00Z"
                }
            ],
            "total": 2,
            "page": 1,
            "pageSize": 100
        }
    }

    respx.post(
        "https://api.priceedge.com/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price"
    ).mock(
        return_value=httpx.Response(200, json=mock_priceedge_response)
    )

    # Create request
    request = IntegrationRequest(
        route="/pricing/suggested-prices",
        method="POST",
        body={
            "filters": {"cd_StoreNumber": "STORE01"},
            "page": 1,
            "pageSize": 100
        }
    )

    # Route request
    response = await router_with_priceedge_routes.route_request(request)

    # Verify response transformation
    assert response.status_code == 200
    assert "items" in response.body
    assert "totalItems" in response.body

    # Verify transformed fields
    assert len(response.body["items"]) == 2
    assert response.body["totalItems"] == 2

    # Verify items contain original data
    assert response.body["items"][0]["cd_ItemNumber"] == "ITEM001"
    assert response.body["items"][0]["Value"] == 19.99
    assert response.body["items"][1]["cd_ItemNumber"] == "ITEM002"
    assert response.body["items"][1]["Value"] == 29.99

    # Verify original nested structure is preserved (additive transformation)
    assert "Data" in response.body
    assert response.body["Data"]["data"][0]["cd_ItemNumber"] == "ITEM001"


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_response_transformation_empty_results(router_with_priceedge_routes):
    """Test PriceEdge response transformation with empty results."""
    # Mock empty PriceEdge response
    mock_priceedge_response = {
        "Data": {
            "data": [],
            "total": 0,
            "page": 1,
            "pageSize": 100
        }
    }

    respx.post(
        "https://api.priceedge.com/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price"
    ).mock(
        return_value=httpx.Response(200, json=mock_priceedge_response)
    )

    # Create request
    request = IntegrationRequest(
        route="/pricing/suggested-prices",
        method="POST",
        body={"filters": {"cd_StoreNumber": "NONEXISTENT"}}
    )

    # Route request
    response = await router_with_priceedge_routes.route_request(request)

    # Verify response transformation with empty data
    assert response.status_code == 200
    assert "items" in response.body
    assert "totalItems" in response.body
    assert len(response.body["items"]) == 0
    assert response.body["totalItems"] == 0


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_response_transformation_large_dataset(router_with_priceedge_routes):
    """Test PriceEdge response transformation with large dataset."""
    # Mock large dataset response
    items = [
        {
            "cd_ItemNumber": f"ITEM{i:04d}",
            "cd_StoreNumber": "STORE01",
            "Value": 10.0 + (i * 0.5),
            "dt_Created": "2024-01-01T10:00:00Z"
        }
        for i in range(1, 101)  # 100 items
    ]

    mock_priceedge_response = {
        "Data": {
            "data": items,
            "total": 100,
            "page": 1,
            "pageSize": 100
        }
    }

    respx.post(
        "https://api.priceedge.com/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price"
    ).mock(
        return_value=httpx.Response(200, json=mock_priceedge_response)
    )

    # Create request
    request = IntegrationRequest(
        route="/pricing/suggested-prices",
        method="POST",
        body={"filters": {}, "pageSize": 100}
    )

    # Route request
    response = await router_with_priceedge_routes.route_request(request)

    # Verify response transformation
    assert response.status_code == 200
    assert len(response.body["items"]) == 100
    assert response.body["totalItems"] == 100

    # Verify first and last items
    assert response.body["items"][0]["cd_ItemNumber"] == "ITEM0001"
    assert response.body["items"][99]["cd_ItemNumber"] == "ITEM0100"


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_api_error_handling(router_with_priceedge_routes):
    """Test response transformation handles API errors gracefully."""
    # Mock API error response
    respx.post(
        "https://api.priceedge.com/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price"
    ).mock(
        return_value=httpx.Response(
            500,
            json={"error": "Internal Server Error", "message": "Database connection failed"}
        )
    )

    # Create request
    request = IntegrationRequest(
        route="/pricing/suggested-prices",
        method="POST",
        body={"filters": {}}
    )

    # Route request
    response = await router_with_priceedge_routes.route_request(request)

    # Verify error response (no transformation attempted on error)
    assert response.status_code == 500
    # Error response should not be transformed
    assert "items" not in response.body or "error" in response.body


@pytest.mark.asyncio
@respx.mock
async def test_response_transformation_with_headers(priceedge_registry):
    """Test response transformation preserves request headers."""
    router = RequestRouter(priceedge_registry)

    router.add_route(
        RouteConfig(
            path="/pricing/current-prices",
            method="POST",
            connector="priceedge",
            target_path="/api/tables/Item_CurrentPrices",
            transformations=[],
            response_transformations=[
                TransformationRule(
                    source_field="Data.data",
                    target_field="prices"
                )
            ]
        )
    )

    # Mock response
    mock_route = respx.post(
        "https://api.priceedge.com/api/tables/Item_CurrentPrices"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"Data": {"data": [{"price": 10.0}], "total": 1}}
        )
    )

    # Create request with custom headers
    request = IntegrationRequest(
        route="/pricing/current-prices",
        method="POST",
        body={"filters": {}},
        headers={"X-Request-ID": "test-123", "X-Client-Version": "1.0"}
    )

    # Route request
    response = await router.route_request(request)

    # Verify response
    assert response.status_code == 200
    assert "prices" in response.body

    # Verify headers were sent to PriceEdge
    assert mock_route.calls.last.request.headers["X-Request-ID"] == "test-123"
    assert mock_route.calls.last.request.headers["X-Client-Version"] == "1.0"


@pytest.mark.asyncio
@respx.mock
async def test_multiple_response_transformations(priceedge_registry):
    """Test multiple response transformations applied in sequence."""
    router = RequestRouter(priceedge_registry)

    router.add_route(
        RouteConfig(
            path="/pricing/metadata",
            method="POST",
            connector="priceedge",
            target_path="/api/tables/item",
            transformations=[],
            response_transformations=[
                TransformationRule(
                    source_field="Data.data",
                    target_field="items"
                ),
                TransformationRule(
                    source_field="Data.total",
                    target_field="totalItems"
                ),
                TransformationRule(
                    source_field="Data.page",
                    target_field="currentPage"
                ),
                TransformationRule(
                    source_field="Data.pageSize",
                    target_field="itemsPerPage"
                )
            ]
        )
    )

    # Mock response
    respx.post("https://api.priceedge.com/api/tables/item").mock(
        return_value=httpx.Response(
            200,
            json={
                "Data": {
                    "data": [{"id": 1}, {"id": 2}],
                    "total": 50,
                    "page": 2,
                    "pageSize": 20
                }
            }
        )
    )

    # Create request
    request = IntegrationRequest(
        route="/pricing/metadata",
        method="POST",
        body={"page": 2}
    )

    # Route request
    response = await router.route_request(request)

    # Verify all transformations applied
    assert response.status_code == 200
    assert response.body["items"] == [{"id": 1}, {"id": 2}]
    assert response.body["totalItems"] == 50
    assert response.body["currentPage"] == 2
    assert response.body["itemsPerPage"] == 20


@pytest.mark.asyncio
@respx.mock
async def test_response_transformation_error_graceful_degradation(priceedge_registry):
    """Test that transformation errors don't break the response."""
    router = RequestRouter(priceedge_registry)

    # Add route with transformation that will fail (missing field)
    router.add_route(
        RouteConfig(
            path="/pricing/test",
            method="POST",
            connector="priceedge",
            target_path="/api/test",
            transformations=[],
            response_transformations=[
                TransformationRule(
                    source_field="NonExistent.Field",
                    target_field="result"
                )
            ]
        )
    )

    # Mock response without expected field
    original_response = {"Data": {"value": 123}}
    respx.post("https://api.priceedge.com/api/test").mock(
        return_value=httpx.Response(200, json=original_response)
    )

    # Create request
    request = IntegrationRequest(
        route="/pricing/test",
        method="POST",
        body={}
    )

    # Route request
    response = await router.route_request(request)

    # Verify original response returned (graceful degradation)
    assert response.status_code == 200
    assert response.body == original_response
    # Transformation should have failed silently and returned original response
