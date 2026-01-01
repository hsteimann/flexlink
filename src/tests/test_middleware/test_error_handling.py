"""Tests for error handling middleware."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from flexlink.middleware.error_handling import ErrorHandlingMiddleware


@pytest.fixture
def app_with_middleware():
    """Create FastAPI app with error handling middleware."""
    app = FastAPI()
    app.add_middleware(ErrorHandlingMiddleware)

    # Test endpoints that raise different exceptions
    @app.get("/success")
    async def success_endpoint():
        return {"message": "success"}

    @app.get("/value_error")
    async def value_error_endpoint():
        raise ValueError("Test validation error")

    @app.get("/key_error")
    async def key_error_endpoint():
        raise KeyError("missing_key")

    @app.get("/permission_error")
    async def permission_error_endpoint():
        raise PermissionError("Access denied")

    @app.get("/unexpected_error")
    async def unexpected_error_endpoint():
        raise RuntimeError("Unexpected error")

    @app.get("/zero_division")
    async def zero_division_endpoint():
        return 1 / 0

    return app


class TestErrorHandlingMiddleware:
    """Test error handling middleware behavior."""

    def test_middleware_allows_successful_requests(self, app_with_middleware):
        """Test that middleware doesn't interfere with successful requests."""
        client = TestClient(app_with_middleware)
        response = client.get("/success")

        assert response.status_code == 200
        assert response.json() == {"message": "success"}

    def test_middleware_handles_value_error_as_400(self, app_with_middleware):
        """Test that ValueError is converted to 400 Bad Request."""
        client = TestClient(app_with_middleware)
        response = client.get("/value_error")

        assert response.status_code == 400
        assert response.json()["error"] == "Validation error"
        assert "Test validation error" in response.json()["detail"]

    def test_middleware_handles_key_error_as_404(self, app_with_middleware):
        """Test that KeyError is converted to 404 Not Found."""
        client = TestClient(app_with_middleware)
        response = client.get("/key_error")

        assert response.status_code == 404
        assert response.json()["error"] == "Resource not found"
        assert "missing_key" in response.json()["detail"]

    def test_middleware_handles_permission_error_as_403(self, app_with_middleware):
        """Test that PermissionError is converted to 403 Forbidden."""
        client = TestClient(app_with_middleware)
        response = client.get("/permission_error")

        assert response.status_code == 403
        assert response.json()["error"] == "Permission denied"
        assert "Access denied" in response.json()["detail"]

    def test_middleware_handles_unexpected_error_as_500(self, app_with_middleware):
        """Test that unexpected exceptions are converted to 500 Internal Server Error."""
        client = TestClient(app_with_middleware)
        response = client.get("/unexpected_error")

        assert response.status_code == 500
        assert response.json()["error"] == "Internal server error"
        assert response.json()["detail"] == "An unexpected error occurred"

    def test_middleware_handles_zero_division_as_500(self, app_with_middleware):
        """Test that ZeroDivisionError is handled as 500."""
        client = TestClient(app_with_middleware)
        response = client.get("/zero_division")

        assert response.status_code == 500
        assert response.json()["error"] == "Internal server error"

    def test_middleware_response_has_correct_json_structure(self, app_with_middleware):
        """Test that error responses have consistent JSON structure."""
        client = TestClient(app_with_middleware)
        response = client.get("/value_error")

        json_data = response.json()
        assert "error" in json_data
        assert "detail" in json_data
        assert isinstance(json_data["error"], str)
        assert isinstance(json_data["detail"], str)

    def test_middleware_returns_json_response(self, app_with_middleware):
        """Test that middleware always returns JSON responses."""
        client = TestClient(app_with_middleware)
        response = client.get("/unexpected_error")

        assert response.headers["content-type"] == "application/json"

    def test_middleware_logs_errors(self, app_with_middleware, caplog):
        """Test that middleware logs errors appropriately."""
        client = TestClient(app_with_middleware)

        with caplog.at_level("ERROR"):
            client.get("/value_error")

        assert "Validation error" in caplog.text

    def test_middleware_multiple_requests(self, app_with_middleware):
        """Test that middleware handles multiple requests correctly."""
        client = TestClient(app_with_middleware)

        # Multiple requests should work independently
        response1 = client.get("/success")
        response2 = client.get("/value_error")
        response3 = client.get("/success")

        assert response1.status_code == 200
        assert response2.status_code == 400
        assert response3.status_code == 200
