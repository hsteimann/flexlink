"""Tests for PriceEdge specialized connector."""

import httpx
import pytest
import respx

from flexlink.connectors.priceedge_connector import PriceEdgeConnector
from flexlink.models.connector import AuthConfig, ConnectorConfig


@pytest.fixture
async def http_client():
    """Create async HTTP client for tests."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def priceedge_config():
    """Create PriceEdge connector configuration."""
    return ConnectorConfig(
        name="priceedge",
        type="rest",
        base_url="https://test.priceedge.eu/papi",
        auth=AuthConfig(
            type="api_key",
            credentials={
                "header": "Authorization",
                "key": "ApiKey test_key:test_token"
            }
        ),
        timeout=30,
        retry_attempts=3,
    )


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_response_unwrapping(http_client, priceedge_config):
    """Test that PriceEdge responses are automatically unwrapped."""
    connector = PriceEdgeConnector(priceedge_config, http_client)

    # Mock PriceEdge's wrapped response format
    respx.post("https://test.priceedge.eu/papi/api/tables/test").mock(
        return_value=httpx.Response(200, json={
            "Data": {
                "data": [
                    {"id": 1, "price": 99.99},
                    {"id": 2, "price": 149.99}
                ],
                "totalRecords": 2,
                "page": 1
            }
        })
    )

    response = await connector.send_request(
        method="POST",
        path="api/tables/test",
        data={"page": 1, "nrOfRecords": 100}
    )

    # Should be unwrapped to just the data array
    assert response.body == [
        {"id": 1, "price": 99.99},
        {"id": 2, "price": 149.99}
    ]


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_pagination(http_client, priceedge_config):
    """Test PriceEdge automatic pagination."""
    connector = PriceEdgeConnector(priceedge_config, http_client)

    # Mock two pages of results
    respx.post("https://test.priceedge.eu/papi/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price").mock(
        side_effect=[
            # Page 1: Full page
            httpx.Response(200, json={
                "Data": {
                    "data": [{"cd_ItemNumber": f"ITEM{i:03d}", "price": 10.0 + i} for i in range(100)]
                }
            }),
            # Page 2: Partial page (last)
            httpx.Response(200, json={
                "Data": {
                    "data": [{"cd_ItemNumber": f"ITEM{i:03d}", "price": 110.0 + i} for i in range(50)]
                }
            }),
        ]
    )

    result = await connector.query_suggested_prices(
        item_ids=["ITEM001", "ITEM002"],
        page_size=100,
        max_pages=5
    )

    # Should have fetched both pages
    assert len(result) == 150
    assert result[0]["cd_ItemNumber"] == "ITEM000"
    assert result[149]["cd_ItemNumber"] == "ITEM049"


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_empty_results(http_client, priceedge_config):
    """Test PriceEdge handles empty results gracefully."""
    connector = PriceEdgeConnector(priceedge_config, http_client)

    # Mock empty response
    respx.post("https://test.priceedge.eu/papi/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price").mock(
        return_value=httpx.Response(200, json={
            "Data": {
                "data": []
            }
        })
    )

    result = await connector.query_suggested_prices(
        item_ids=["NONEXISTENT"],
        page_size=100
    )

    assert result == []


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_body_based_pagination_params(http_client, priceedge_config):
    """Test that pagination params are sent in request body."""
    connector = PriceEdgeConnector(priceedge_config, http_client)

    # Capture request to verify body content
    def check_request_body(request):
        import json
        body = json.loads(request.content)
        assert body["page"] == 1
        assert body["nrOfRecords"] == 50
        assert body["filters"] == [{"columnName": "cd_ItemNumber", "op": "containsAny", "value": "ITEM001"}]
        return httpx.Response(200, json={"Data": {"data": [{"price": 99.99}]}})

    respx.post("https://test.priceedge.eu/papi/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price").mock(
        side_effect=check_request_body
    )

    await connector.query_suggested_prices(
        item_ids=["ITEM001"],
        page_size=50,
        max_pages=1
    )


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_max_pages_limit(http_client, priceedge_config):
    """Test that max_pages limit is respected."""
    connector = PriceEdgeConnector(priceedge_config, http_client)

    # Mock API that always returns full pages (would paginate forever)
    def always_full_page(request):
        return httpx.Response(200, json={
            "Data": {
                "data": [{"price": 99.99}] * 100  # Always full page
            }
        })

    mock_route = respx.post("https://test.priceedge.eu/papi/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price").mock(
        side_effect=always_full_page
    )

    result = await connector.query_suggested_prices(
        item_ids=["ITEM001"],
        page_size=100,
        max_pages=3  # Limit to 3 pages
    )

    # Should have stopped at 3 pages (300 records)
    assert len(result) == 300
    assert mock_route.call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_single_page(http_client, priceedge_config):
    """Test PriceEdge with results fitting in single page."""
    connector = PriceEdgeConnector(priceedge_config, http_client)

    # Mock single page response (< page_size)
    respx.post("https://test.priceedge.eu/papi/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price").mock(
        return_value=httpx.Response(200, json={
            "Data": {
                "data": [{"cd_ItemNumber": "ITEM001", "price": 99.99}]
            }
        })
    )

    result = await connector.query_suggested_prices(
        item_ids=["ITEM001"],
        page_size=100
    )

    # Single result, should stop after first page
    assert len(result) == 1
    assert result[0]["cd_ItemNumber"] == "ITEM001"
