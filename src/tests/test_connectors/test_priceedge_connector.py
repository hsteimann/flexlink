"""Integration tests for PriceEdge connector."""

import pytest
import respx
import httpx
from flexlink.core.registry import ConnectorRegistry
from flexlink.models.connector import ConnectorConfig, AuthConfig


@pytest.mark.asyncio
async def test_priceedge_connector_loads():
    """Test that PriceEdge connector can be loaded from configuration."""
    # This test verifies the YAML configuration is valid
    registry = ConnectorRegistry()

    # Load connectors from config directory
    await registry.load_connectors("config/connectors")

    # Check PriceEdge connector was loaded
    assert "priceedge" in registry.list_connectors()


@pytest.mark.asyncio
async def test_priceedge_auth_headers():
    """Test that PriceEdge connector adds correct ApiKey header."""
    config = ConnectorConfig(
        name="priceedge",
        type="rest",
        base_url="https://yourcompany-staging.priceedge.eu/papi",
        auth=AuthConfig(
            type="api_key",
            credentials={
                "header": "Authorization",
                "key": "ApiKey test_key:abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"
            }
        ),
        timeout=30,
        retry_attempts=3,
    )

    # Create HTTP client for testing
    async with httpx.AsyncClient() as client:
        from flexlink.connectors.rest_connector import RestConnector
        connector = RestConnector(config, client)

        # Get auth headers
        headers = connector._get_auth_headers()

        # Verify ApiKey format
        assert "Authorization" in headers
        assert headers["Authorization"] == "ApiKey test_key:abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"
        assert headers["Authorization"].startswith("ApiKey ")
        assert "test_key:" in headers["Authorization"]


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_get_suggested_prices(respx_mock: respx.MockRouter):
    """Test getting suggested prices from PriceEdge API."""
    # Mock PriceEdge API response (adjust endpoint path based on actual API)
    respx_mock.post("https://yourcompany-staging.priceedge.eu/papi/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price").mock(
        return_value=httpx.Response(
            status_code=200,
            json={
                "data": [
                    {
                        "cd_ItemNumber": "12345",
                        "Value": 99.99
                    },
                    {
                        "cd_ItemNumber": "12346",
                        "Value": 149.99
                    }
                ],
                "total": 2,
                "page": 1
            }
        )
    )

    config = ConnectorConfig(
        name="priceedge",
        type="rest",
        base_url="https://yourcompany-staging.priceedge.eu/papi",
        auth=AuthConfig(
            type="api_key",
            credentials={
                "header": "Authorization",
                "key": "ApiKey test_key:abc123def456ghi789jkl012mno345pqr678stu901vwx234yz567"
            }
        ),
        timeout=30,
        retry_attempts=3,
    )

    async with httpx.AsyncClient() as client:
        from flexlink.connectors.rest_connector import RestConnector
        connector = RestConnector(config, client)

        # Send request
        response = await connector.send_request(
            method="POST",
            path="/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price",
            data={
                "page": 1,
                "nrOfRecords": 10,
                "filters": [
                    {
                        "columnName": "cd_ItemNumber",
                        "op": "containsAny",
                        "value": "12345,12346"
                    }
                ],
                "fields": ["cd_ItemNumber", "Value"]
            }
        )

        # Verify response
        assert response.status_code == 200
        assert "data" in response.body
        assert len(response.body["data"]) == 2
        assert response.body["data"][0]["cd_ItemNumber"] == "12345"
        assert response.body["data"][0]["Value"] == 99.99


@pytest.mark.asyncio
@respx.mock
async def test_priceedge_unauthorized(respx_mock: respx.MockRouter):
    """Test handling of invalid API credentials."""
    # Mock 401 Unauthorized response
    respx_mock.post("https://yourcompany-staging.priceedge.eu/papi/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price").mock(
        return_value=httpx.Response(
            status_code=401,
            json={"error": "Invalid API credentials"}
        )
    )

    config = ConnectorConfig(
        name="priceedge",
        type="rest",
        base_url="https://yourcompany-staging.priceedge.eu/papi",
        auth=AuthConfig(
            type="api_key",
            credentials={
                "header": "Authorization",
                "key": "ApiKey invalid_key:wrongtokenwrongtokenwrongtokenwrongtoken123"
            }
        ),
        timeout=30,
        retry_attempts=3,
    )

    async with httpx.AsyncClient() as client:
        from flexlink.connectors.rest_connector import RestConnector
        connector = RestConnector(config, client)

        # Send request
        response = await connector.send_request(
            method="POST",
            path="/api/tables/Item_PriceList_SuggestedPrices_Suggested_Price",
            data={"page": 1, "nrOfRecords": 1}
        )

        # Verify error response (4xx errors are returned, not raised)
        assert response.status_code == 401
        assert response.error is not None
        assert "Invalid API credentials" in str(response.body)
