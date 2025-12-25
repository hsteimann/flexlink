"""
Tests for REST connector query parameter and HTTP method semantics.

Verifies:
- Query parameters are forwarded correctly
- GET/DELETE use query params, not JSON body
- POST/PUT/PATCH use JSON body
- Query params and body can coexist when needed
"""

import httpx
import pytest
import respx

from flexlink.connectors.rest_connector import RestConnector
from flexlink.models.connector import AuthConfig, ConnectorConfig


@pytest.fixture
def http_client():
    """Create HTTP client for tests."""
    return httpx.AsyncClient()


@pytest.fixture
def connector(http_client):
    """Create test REST connector."""
    config = ConnectorConfig(
        name="test",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    return RestConnector(config, http_client)


@pytest.mark.asyncio
@respx.mock
async def test_get_request_uses_query_params_not_body(connector):
    """Test GET requests use query params instead of JSON body."""
    # Mock the API endpoint
    route = respx.get("https://api.test.com/items").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    # Send GET request with query params
    await connector.send_request(
        method="GET",
        path="/items",
        data=None,
        params={"category": "books", "limit": "10"}
    )

    # Verify request was made with query params, not JSON body
    request = route.calls.last.request
    assert request.method == "GET"
    assert "category=books" in str(request.url)
    assert "limit=10" in str(request.url)
    # GET requests should not have a body
    assert request.content == b""


@pytest.mark.asyncio
@respx.mock
async def test_get_request_with_explicit_body(connector):
    """Test GET can still send body if explicitly provided (some APIs support this)."""
    # Mock the API endpoint
    route = respx.get("https://api.test.com/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    # Send GET with explicit body (unusual but allowed)
    await connector.send_request(
        method="GET",
        path="/search",
        data={"query": {"bool": {"must": [{"term": {"status": "active"}}]}}},
        params={"scroll": "1m"}
    )

    # Verify both params and body were sent
    request = route.calls.last.request
    assert request.method == "GET"
    assert "scroll=1m" in str(request.url)
    # Body should be present since explicitly provided
    assert request.content != b""


@pytest.mark.asyncio
@respx.mock
async def test_delete_request_uses_query_params_not_body(connector):
    """Test DELETE requests use query params instead of JSON body."""
    # Mock the API endpoint
    route = respx.delete("https://api.test.com/items").mock(
        return_value=httpx.Response(204)
    )

    # Send DELETE with query params
    await connector.send_request(
        method="DELETE",
        path="/items",
        data=None,
        params={"id": "123", "force": "true"}
    )

    # Verify request was made with query params, not body
    request = route.calls.last.request
    assert request.method == "DELETE"
    assert "id=123" in str(request.url)
    assert "force=true" in str(request.url)
    assert request.content == b""


@pytest.mark.asyncio
@respx.mock
async def test_post_request_uses_json_body(connector):
    """Test POST requests use JSON body as expected."""
    # Mock the API endpoint
    route = respx.post("https://api.test.com/items").mock(
        return_value=httpx.Response(201, json={"id": 123})
    )

    # Send POST with body
    await connector.send_request(
        method="POST",
        path="/items",
        data={"name": "New Item", "price": 19.99},
        params={}
    )

    # Verify request has JSON body
    request = route.calls.last.request
    assert request.method == "POST"
    assert request.content != b""
    # Verify JSON content
    import json
    body = json.loads(request.content)
    assert body["name"] == "New Item"
    assert body["price"] == 19.99


@pytest.mark.asyncio
@respx.mock
async def test_post_request_with_query_params_and_body(connector):
    """Test POST can have both query params and JSON body."""
    # Mock the API endpoint
    route = respx.post("https://api.test.com/items").mock(
        return_value=httpx.Response(201, json={"id": 123})
    )

    # Send POST with both query params and body
    await connector.send_request(
        method="POST",
        path="/items",
        data={"name": "New Item"},
        params={"notify": "true", "async": "false"}
    )

    # Verify both query params and body present
    request = route.calls.last.request
    assert request.method == "POST"
    assert "notify=true" in str(request.url)
    assert "async=false" in str(request.url)
    assert request.content != b""


@pytest.mark.asyncio
@respx.mock
async def test_put_request_uses_json_body(connector):
    """Test PUT requests use JSON body."""
    # Mock the API endpoint
    route = respx.put("https://api.test.com/items/123").mock(
        return_value=httpx.Response(200, json={"id": 123, "updated": True})
    )

    # Send PUT with body
    await connector.send_request(
        method="PUT",
        path="/items/123",
        data={"name": "Updated Item", "price": 29.99}
    )

    # Verify request has JSON body
    request = route.calls.last.request
    assert request.method == "PUT"
    assert request.content != b""


@pytest.mark.asyncio
@respx.mock
async def test_patch_request_uses_json_body(connector):
    """Test PATCH requests use JSON body."""
    # Mock the API endpoint
    route = respx.patch("https://api.test.com/items/123").mock(
        return_value=httpx.Response(200, json={"id": 123, "patched": True})
    )

    # Send PATCH with body
    await connector.send_request(
        method="PATCH",
        path="/items/123",
        data={"price": 24.99}
    )

    # Verify request has JSON body
    request = route.calls.last.request
    assert request.method == "PATCH"
    assert request.content != b""


@pytest.mark.asyncio
@respx.mock
async def test_head_request_uses_query_params(connector):
    """Test HEAD requests use query params, not body."""
    # Mock the API endpoint
    route = respx.head("https://api.test.com/items/123").mock(
        return_value=httpx.Response(200)
    )

    # Send HEAD with query params
    await connector.send_request(
        method="HEAD",
        path="/items/123",
        data=None,
        params={"check": "exists"}
    )

    # Verify request uses query params, no body
    request = route.calls.last.request
    assert request.method == "HEAD"
    assert "check=exists" in str(request.url)
    assert request.content == b""


@pytest.mark.asyncio
@respx.mock
async def test_options_request_uses_query_params(connector):
    """Test OPTIONS requests use query params, not body."""
    # Mock the API endpoint
    route = respx.request("OPTIONS", "https://api.test.com/items").mock(
        return_value=httpx.Response(200, headers={"Allow": "GET, POST, DELETE"})
    )

    # Send OPTIONS with query params
    await connector.send_request(
        method="OPTIONS",
        path="/items",
        data=None,
        params={"verbose": "true"}
    )

    # Verify request uses query params
    request = route.calls.last.request
    assert request.method == "OPTIONS"
    assert "verbose=true" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_empty_query_params_not_sent(connector):
    """Test empty query params dict is not sent."""
    # Mock the API endpoint
    route = respx.get("https://api.test.com/items").mock(
        return_value=httpx.Response(200, json={"items": []})
    )

    # Send GET with empty params
    await connector.send_request(
        method="GET",
        path="/items",
        data=None,
        params={}
    )

    # Verify no query params in URL
    request = route.calls.last.request
    assert "?" not in str(request.url) or str(request.url).endswith("?")


@pytest.mark.asyncio
@respx.mock
async def test_query_params_with_special_characters(connector):
    """Test query params with special characters are properly encoded."""
    # Mock the API endpoint
    route = respx.get("https://api.test.com/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    # Send GET with special characters in params
    await connector.send_request(
        method="GET",
        path="/search",
        data=None,
        params={"query": "hello world", "filter": "name:John Doe"}
    )

    # Verify params are URL-encoded
    request = route.calls.last.request
    url_str = str(request.url)
    # Spaces should be encoded
    assert "hello+world" in url_str or "hello%20world" in url_str
    # Colons should be encoded or preserved
    assert "name" in url_str and "John" in url_str
