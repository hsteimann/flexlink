"""Tests for REST connector with authentication and retry logic."""

import httpx
import pytest
import respx

from flexlink.connectors.rest_connector import RestConnector
from flexlink.models.connector import AuthConfig, ConnectorConfig


@pytest.fixture
async def http_client():
    """Create async HTTP client for tests."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def rest_config():
    """Create a basic REST connector configuration."""
    return ConnectorConfig(
        name="test_rest",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(type="none"),
        timeout=30,
        retry_attempts=3,
    )


@pytest.mark.asyncio
@respx.mock
async def test_successful_get_request(http_client, rest_config):
    """Test successful GET request."""
    connector = RestConnector(rest_config, http_client)

    mock_route = respx.get("https://api.example.com/users").mock(
        return_value=httpx.Response(200, json={"users": ["user1", "user2"]})
    )

    response = await connector.send_request("GET", "/users")

    assert response.status_code == 200
    assert response.body == {"users": ["user1", "user2"]}
    assert mock_route.called


@pytest.mark.asyncio
@respx.mock
async def test_successful_post_request(http_client, rest_config):
    """Test successful POST request with data."""
    connector = RestConnector(rest_config, http_client)

    mock_route = respx.post("https://api.example.com/users").mock(
        return_value=httpx.Response(201, json={"id": 1, "name": "John"})
    )

    response = await connector.send_request("POST", "/users", data={"name": "John"})

    assert response.status_code == 201
    assert response.body == {"id": 1, "name": "John"}
    assert mock_route.called


@pytest.mark.asyncio
@respx.mock
async def test_bearer_auth_header(http_client):
    """Test that Bearer authentication adds correct Authorization header."""
    config = ConnectorConfig(
        name="auth_test",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(type="bearer", credentials={"token": "test-token-123"}),
    )
    connector = RestConnector(config, http_client)

    mock_route = respx.get("https://api.example.com/protected").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    await connector.send_request("GET", "/protected")

    # Verify Authorization header was sent
    assert mock_route.called
    request = mock_route.calls.last.request
    assert request.headers["Authorization"] == "Bearer test-token-123"


@pytest.mark.asyncio
@respx.mock
async def test_basic_auth_header(http_client):
    """Test that Basic authentication encodes credentials correctly."""
    config = ConnectorConfig(
        name="auth_test",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(
            type="basic",
            credentials={"username": "user", "password": "pass"},
        ),
    )
    connector = RestConnector(config, http_client)

    mock_route = respx.get("https://api.example.com/protected").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    await connector.send_request("GET", "/protected")

    # Verify Basic auth header
    assert mock_route.called
    request = mock_route.calls.last.request
    auth_header = request.headers["Authorization"]
    assert auth_header.startswith("Basic ")
    # user:pass in base64 is dXNlcjpwYXNz
    assert auth_header == "Basic dXNlcjpwYXNz"


@pytest.mark.asyncio
@respx.mock
async def test_api_key_auth_header(http_client):
    """Test that API key authentication adds correct header."""
    config = ConnectorConfig(
        name="auth_test",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(type="api_key", credentials={"key": "my-api-key"}),
    )
    connector = RestConnector(config, http_client)

    mock_route = respx.get("https://api.example.com/protected").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    await connector.send_request("GET", "/protected")

    # Verify API key header (default header name is X-API-Key)
    assert mock_route.called
    request = mock_route.calls.last.request
    assert request.headers["X-API-Key"] == "my-api-key"


@pytest.mark.asyncio
@respx.mock
async def test_api_key_custom_header(http_client):
    """Test API key with custom header name."""
    config = ConnectorConfig(
        name="auth_test",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(
            type="api_key",
            credentials={"key": "my-api-key", "header": "X-Custom-API-Key"},
        ),
    )
    connector = RestConnector(config, http_client)

    mock_route = respx.get("https://api.example.com/protected").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )

    await connector.send_request("GET", "/protected")

    request = mock_route.calls.last.request
    assert request.headers["X-Custom-API-Key"] == "my-api-key"


@pytest.mark.asyncio
@respx.mock
async def test_retry_on_5xx_errors(http_client, rest_config):
    """Test that connector retries on 5xx server errors."""
    rest_config.retry_attempts = 3
    connector = RestConnector(rest_config, http_client)

    mock_route = respx.get("https://api.example.com/flaky").mock(
        side_effect=[
            httpx.Response(503),  # First attempt fails
            httpx.Response(503),  # Second attempt fails
            httpx.Response(200, json={"status": "ok"}),  # Third succeeds
        ]
    )

    response = await connector.send_request("GET", "/flaky")

    assert response.status_code == 200
    assert response.body == {"status": "ok"}
    assert mock_route.call_count == 3  # Verify 3 attempts were made


@pytest.mark.asyncio
@respx.mock
async def test_no_retry_on_4xx_errors(http_client, rest_config):
    """Test that connector does NOT retry on 4xx client errors."""
    connector = RestConnector(rest_config, http_client)

    mock_route = respx.get("https://api.example.com/notfound").mock(
        return_value=httpx.Response(404, json={"error": "Not found"})
    )

    response = await connector.send_request("GET", "/notfound")

    # Should return error response without retry
    assert response.status_code == 404
    assert response.error is not None
    assert mock_route.call_count == 1  # Only one attempt, no retry


@pytest.mark.asyncio
@respx.mock
async def test_timeout_with_retry(http_client, rest_config):
    """Test timeout handling with retry."""
    rest_config.retry_attempts = 2
    rest_config.timeout = 1
    connector = RestConnector(rest_config, http_client)

    # Mock timeouts followed by success
    mock_route = respx.get("https://api.example.com/slow").mock(
        side_effect=[
            httpx.TimeoutException("Request timed out"),
            httpx.Response(200, json={"status": "ok"}),
        ]
    )

    response = await connector.send_request("GET", "/slow")

    assert response.status_code == 200
    assert mock_route.call_count == 2


@pytest.mark.asyncio
async def test_transform_request(http_client, rest_config):
    """Test that transform_request can be overridden."""

    class CustomConnector(RestConnector):
        async def transform_request(self, data):
            # Add a custom field
            return {**data, "transformed": True}

    connector = CustomConnector(rest_config, http_client)

    # Test transformation
    original = {"name": "test"}
    transformed = await connector.transform_request(original)

    assert transformed == {"name": "test", "transformed": True}


@pytest.mark.asyncio
async def test_transform_response(http_client, rest_config):
    """Test that transform_response can be overridden."""

    class CustomConnector(RestConnector):
        async def transform_response(self, data):
            # Uppercase all values
            return {k: v.upper() if isinstance(v, str) else v for k, v in data.items()}

    connector = CustomConnector(rest_config, http_client)

    # Test transformation
    original = {"name": "john", "age": 30}
    transformed = await connector.transform_response(original)

    assert transformed == {"name": "JOHN", "age": 30}


@pytest.mark.asyncio
@respx.mock
async def test_request_with_custom_headers(http_client, rest_config):
    """Test that custom headers are merged correctly."""
    rest_config.headers = {"X-Default": "default-value"}
    connector = RestConnector(rest_config, http_client)

    mock_route = respx.get("https://api.example.com/test").mock(
        return_value=httpx.Response(200, json={})
    )

    await connector.send_request(
        "GET", "/test", headers={"X-Custom": "custom-value"}
    )

    request = mock_route.calls.last.request
    assert request.headers["X-Default"] == "default-value"
    assert request.headers["X-Custom"] == "custom-value"


@pytest.mark.asyncio
async def test_invalid_auth_type_raises_error(http_client):
    """Test that invalid auth type raises ValueError."""
    config = ConnectorConfig(
        name="invalid_auth",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(type="invalid_type", credentials={}),
    )
    connector = RestConnector(config, http_client)

    with pytest.raises(ValueError, match="Unsupported auth type"):
        connector._get_auth_headers()
