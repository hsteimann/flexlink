"""
Tests for API routes HTTP status code propagation.

Verifies that HTTP status codes in IntegrationResponse are properly
propagated to the actual HTTP response status code.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from flexlink.api.dependencies import get_registry, get_router
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.main import app
from flexlink.models.request import IntegrationResponse


@pytest.fixture
def mock_router():
    """Create mock router for testing."""
    router = MagicMock(spec=RequestRouter)
    router.route_request = AsyncMock()
    return router


@pytest.fixture
def client(mock_router):
    """Create test client with mocked dependencies."""
    # Override dependencies
    app.dependency_overrides[get_router] = lambda: mock_router
    app.dependency_overrides[get_registry] = lambda: MagicMock(spec=ConnectorRegistry)

    client = TestClient(app)
    yield client

    # Clean up
    app.dependency_overrides.clear()


def test_success_response_returns_http_200(client, mock_router):
    """Test that successful responses return HTTP 200."""
    # Mock successful response
    mock_router.route_request.return_value = IntegrationResponse(
        status_code=200,
        body={"result": "success"}
    )

    # Make request
    response = client.post("/api/v1/route", json={
        "route": "/test",
        "method": "GET"
    })

    # Verify HTTP status code matches
    assert response.status_code == 200
    assert response.json()["status_code"] == 200
    assert response.json()["body"]["result"] == "success"


def test_not_found_returns_http_404(client, mock_router):
    """Test that route not found returns HTTP 404."""
    # Mock 404 response
    mock_router.route_request.return_value = IntegrationResponse(
        status_code=404,
        error="No route configured for: GET /nonexistent"
    )

    # Make request
    response = client.post("/api/v1/route", json={
        "route": "/nonexistent",
        "method": "GET"
    })

    # Verify HTTP status code is 404, not 200
    assert response.status_code == 404
    assert response.json()["status_code"] == 404
    assert "No route configured" in response.json()["error"]


def test_internal_error_returns_http_500(client, mock_router):
    """Test that internal errors return HTTP 500."""
    # Mock 500 response
    mock_router.route_request.return_value = IntegrationResponse(
        status_code=500,
        error="Connector not found: missing_connector"
    )

    # Make request
    response = client.post("/api/v1/route", json={
        "route": "/test",
        "method": "POST"
    })

    # Verify HTTP status code is 500
    assert response.status_code == 500
    assert response.json()["status_code"] == 500
    assert "Connector not found" in response.json()["error"]


def test_bad_request_returns_http_400(client, mock_router):
    """Test that bad requests return HTTP 400."""
    # Mock 400 response (e.g., transformation failed)
    mock_router.route_request.return_value = IntegrationResponse(
        status_code=400,
        error="Request transformation failed: invalid type"
    )

    # Make request
    response = client.post("/api/v1/route", json={
        "route": "/test",
        "method": "POST",
        "body": {"invalid": "data"}
    })

    # Verify HTTP status code is 400
    assert response.status_code == 400
    assert response.json()["status_code"] == 400
    assert "transformation failed" in response.json()["error"]


def test_connector_client_error_returns_http_4xx(client, mock_router):
    """Test that connector 4xx errors are propagated correctly."""
    # Mock 403 Forbidden from connector
    mock_router.route_request.return_value = IntegrationResponse(
        status_code=403,
        error="Forbidden: Invalid API credentials"
    )

    # Make request
    response = client.post("/api/v1/route", json={
        "route": "/test",
        "method": "GET"
    })

    # Verify HTTP status code is 403
    assert response.status_code == 403
    assert response.json()["status_code"] == 403
    assert "Forbidden" in response.json()["error"]


def test_connector_server_error_returns_http_5xx(client, mock_router):
    """Test that connector 5xx errors are propagated correctly."""
    # Mock 503 Service Unavailable from connector
    mock_router.route_request.return_value = IntegrationResponse(
        status_code=503,
        error="Service Unavailable: Downstream API is down"
    )

    # Make request
    response = client.post("/api/v1/route", json={
        "route": "/test",
        "method": "GET"
    })

    # Verify HTTP status code is 503
    assert response.status_code == 503
    assert response.json()["status_code"] == 503
    assert "Service Unavailable" in response.json()["error"]


def test_created_response_returns_http_201(client, mock_router):
    """Test that 201 Created responses are propagated correctly."""
    # Mock 201 response
    mock_router.route_request.return_value = IntegrationResponse(
        status_code=201,
        body={"id": 123, "created": True}
    )

    # Make request
    response = client.post("/api/v1/route", json={
        "route": "/items",
        "method": "POST",
        "body": {"name": "New Item"}
    })

    # Verify HTTP status code is 201
    assert response.status_code == 201
    assert response.json()["status_code"] == 201
    assert response.json()["body"]["created"] is True


def test_no_content_response_returns_http_204(client, mock_router):
    """Test that 204 No Content responses are propagated correctly."""
    # Mock 204 response
    mock_router.route_request.return_value = IntegrationResponse(
        status_code=204,
        body=None
    )

    # Make request
    response = client.post("/api/v1/route", json={
        "route": "/items/123",
        "method": "DELETE"
    })

    # Verify HTTP status code is 204
    # Note: FastAPI/Starlette may return empty content for 204
    assert response.status_code == 204

    # 204 responses may have no content or the IntegrationResponse model
    if response.content:
        response_data = response.json()
        assert response_data["status_code"] == 204
        assert response_data["body"] is None


def test_list_connectors_endpoint(client):
    """Test /connectors endpoint returns 200."""
    response = client.get("/api/v1/connectors")

    # This endpoint should always return 200
    assert response.status_code == 200
    assert "connectors" in response.json()


def test_list_routes_endpoint(client):
    """Test /routes endpoint returns 200."""
    response = client.get("/api/v1/routes")

    # This endpoint should always return 200
    assert response.status_code == 200
    assert "routes" in response.json()
