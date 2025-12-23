"""Tests for request/response models."""

from flexlink.models.request import IntegrationRequest, IntegrationResponse


def test_integration_request_minimal():
    """Test IntegrationRequest with minimal fields."""
    request = IntegrationRequest(
        route="/users",
        method="GET"
    )
    assert request.route == "/users"
    assert request.method == "GET"
    assert request.headers == {}
    assert request.body is None
    assert request.query_params == {}


def test_integration_request_with_body():
    """Test IntegrationRequest with request body."""
    request = IntegrationRequest(
        route="/users",
        method="POST",
        body={"name": "John Doe", "email": "john@example.com"}
    )
    assert request.body["name"] == "John Doe"
    assert request.body["email"] == "john@example.com"


def test_integration_request_with_headers():
    """Test IntegrationRequest with custom headers."""
    request = IntegrationRequest(
        route="/users",
        method="GET",
        headers={"Authorization": "Bearer token123"}
    )
    assert request.headers["Authorization"] == "Bearer token123"


def test_integration_request_with_query_params():
    """Test IntegrationRequest with query parameters."""
    request = IntegrationRequest(
        route="/users",
        method="GET",
        query_params={"page": "1", "limit": "10"}
    )
    assert request.query_params["page"] == "1"
    assert request.query_params["limit"] == "10"


def test_integration_response_success():
    """Test successful IntegrationResponse."""
    response = IntegrationResponse(
        status_code=200,
        body={"id": 1, "name": "John Doe"}
    )
    assert response.status_code == 200
    assert response.body["id"] == 1
    assert response.error is None


def test_integration_response_error():
    """Test IntegrationResponse with error."""
    response = IntegrationResponse(
        status_code=500,
        error="Internal server error"
    )
    assert response.status_code == 500
    assert response.error == "Internal server error"
    assert response.body is None


def test_integration_response_with_headers():
    """Test IntegrationResponse with response headers."""
    response = IntegrationResponse(
        status_code=200,
        headers={"Content-Type": "application/json"},
        body={"message": "success"}
    )
    assert response.headers["Content-Type"] == "application/json"


def test_integration_request_nested_body():
    """Test IntegrationRequest with nested body structure."""
    request = IntegrationRequest(
        route="/users",
        method="POST",
        body={
            "user": {
                "name": "John",
                "profile": {
                    "email": "john@example.com",
                    "age": 30
                }
            }
        }
    )
    assert request.body["user"]["profile"]["email"] == "john@example.com"
