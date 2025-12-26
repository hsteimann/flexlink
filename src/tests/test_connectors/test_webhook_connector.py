"""Tests for webhook connector."""

import pytest
import respx
import httpx
from unittest.mock import AsyncMock, patch

from flexlink.connectors.webhook_connector import WebhookConnector
from flexlink.models.connector import ConnectorConfig, AuthConfig
from flexlink.models.webhook import WebhookConfig, WebhookAuthType


@pytest.fixture
def webhook_config():
    """Create test webhook configuration."""
    config = ConnectorConfig(
        name="test-webhook",
        type="webhook",
        base_url="",
        auth=AuthConfig(type="none", credentials={}),
        headers={},
        timeout=30,
        retry_attempts=1,
        enabled=True
    )

    wh_config = WebhookConfig(
        webhook_url="https://hooks.example.com/webhook",
        auth_type=WebhookAuthType.NONE,
        max_retry_attempts=3,
        retry_backoff_factor=2.0,
        timeout_seconds=10
    )

    return config, wh_config


@pytest.fixture
async def http_client():
    """Create async HTTP client."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def webhook_connector(webhook_config, http_client):
    """Create webhook connector instance."""
    config, wh_config = webhook_config
    return WebhookConnector(config, http_client, wh_config)


@pytest.mark.asyncio
@respx.mock
async def test_successful_webhook_delivery(webhook_connector):
    """Test successful webhook delivery."""
    # Mock webhook endpoint
    mock_route = respx.post("https://hooks.example.com/webhook").mock(
        return_value=httpx.Response(200, json={"status": "received"})
    )

    # Send webhook
    data = {"event": "order.created", "order_id": 12345}
    response = await webhook_connector.send_request("POST", "", data=data)

    # Verify
    assert response.status_code == 200
    assert response.body["success"] is True
    assert response.body["attempts"] == 1
    assert mock_route.called

    # Check stats
    stats = webhook_connector.get_stats()
    assert stats["total_deliveries"] == 1
    assert stats["successful_deliveries"] == 1


@pytest.mark.asyncio
@respx.mock
async def test_webhook_with_bearer_auth(http_client):
    """Test webhook with bearer token authentication."""
    config = ConnectorConfig(
        name="test-webhook",
        type="webhook",
        base_url="",
        auth=AuthConfig(type="none", credentials={}),
    )

    wh_config = WebhookConfig(
        webhook_url="https://hooks.example.com/webhook",
        auth_type=WebhookAuthType.BEARER,
        auth_credentials={"token": "secret-token-123"}
    )

    connector = WebhookConnector(config, http_client, wh_config)

    # Mock webhook with auth header check
    def check_auth(request):
        assert "Authorization" in request.headers
        assert request.headers["Authorization"] == "Bearer secret-token-123"
        return httpx.Response(200)

    mock_route = respx.post("https://hooks.example.com/webhook").mock(
        side_effect=check_auth
    )

    # Send webhook
    response = await connector.send_request("POST", "", data={"test": "data"})

    assert response.status_code == 200
    assert mock_route.called


@pytest.mark.asyncio
async def test_webhook_signature_generation(webhook_config, http_client):
    """Test HMAC signature generation."""
    config, wh_config = webhook_config
    wh_config.signature_enabled = True
    wh_config.signature_secret = "my-secret-key"

    connector = WebhookConnector(config, http_client, wh_config)

    # Generate signature
    data = {"event": "test", "id": 123}
    timestamp = "1234567890"
    signature = connector._generate_signature(data, timestamp)

    # Verify signature format
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA256 hex = 64 chars

    # Verify deterministic
    signature2 = connector._generate_signature(data, timestamp)
    assert signature == signature2


@pytest.mark.asyncio
@respx.mock
async def test_webhook_retry_on_5xx(webhook_connector):
    """Test retry logic on 5xx server errors."""
    # Mock webhook to fail twice, then succeed
    call_count = 0

    def mock_response(request):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return httpx.Response(503, json={"error": "Service unavailable"})
        return httpx.Response(200, json={"status": "ok"})

    mock_route = respx.post("https://hooks.example.com/webhook").mock(
        side_effect=mock_response
    )

    # Send webhook
    with patch.object(webhook_connector, '_sleep_with_jitter', new=AsyncMock()):
        response = await webhook_connector.send_request("POST", "", data={"test": "data"})

    # Verify retried 3 times
    assert response.status_code == 200
    assert response.body["attempts"] == 3
    assert call_count == 3


@pytest.mark.asyncio
@respx.mock
async def test_webhook_no_retry_on_4xx(webhook_connector):
    """Test no retry on 4xx client errors."""
    # Mock webhook to return 400
    mock_route = respx.post("https://hooks.example.com/webhook").mock(
        return_value=httpx.Response(400, json={"error": "Bad request"})
    )

    # Send webhook
    response = await webhook_connector.send_request("POST", "", data={"test": "data"})

    # Verify no retries (only 1 attempt)
    assert response.status_code == 400
    assert response.body["attempts"] == 1
    assert mock_route.call_count == 1


@pytest.mark.asyncio
async def test_webhook_only_supports_post(webhook_connector):
    """Test that webhooks only support POST method."""
    response = await webhook_connector.send_request("GET", "", data={"test": "data"})

    assert response.status_code == 405
    assert "only support POST" in response.error


@pytest.mark.asyncio
async def test_webhook_requires_data(webhook_connector):
    """Test that webhooks require data payload."""
    response = await webhook_connector.send_request("POST", "", data=None)

    assert response.status_code == 400
    assert "No data provided" in response.error


@pytest.mark.asyncio
@respx.mock
async def test_webhook_timeout_retry(webhook_connector):
    """Test retry on timeout."""
    # Mock webhook to timeout
    mock_route = respx.post("https://hooks.example.com/webhook").mock(
        side_effect=httpx.TimeoutException("Request timeout")
    )

    # Send webhook
    with patch.object(webhook_connector, '_sleep_with_jitter', new=AsyncMock()):
        response = await webhook_connector.send_request("POST", "", data={"test": "data"})

    # Verify retried max times and failed
    assert response.status_code == 500
    assert response.body["attempts"] == 3  # max_retry_attempts
    assert "timeout" in response.error.lower()


@pytest.mark.asyncio
async def test_webhook_stats_tracking(webhook_connector):
    """Test statistics tracking."""
    # Initial stats
    stats = webhook_connector.get_stats()
    assert stats["total_deliveries"] == 0
    assert stats["success_rate"] == 0.0

    # Simulate deliveries
    webhook_connector.total_deliveries = 10
    webhook_connector.successful_deliveries = 8
    webhook_connector.failed_deliveries = 2

    stats = webhook_connector.get_stats()
    assert stats["total_deliveries"] == 10
    assert stats["successful_deliveries"] == 8
    assert stats["failed_deliveries"] == 2
    assert stats["success_rate"] == 0.8
