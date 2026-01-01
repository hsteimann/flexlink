"""Tests for main application (main.py)."""

import logging

import pytest
from fastapi.testclient import TestClient

from flexlink.main import NiceGUIErrorFilter, app


class TestNiceGUIErrorFilter:
    """Test the NiceGUI error filter."""

    def test_filter_suppresses_request_not_set_errors(self):
        """Test that 'Request is not set' errors are filtered."""
        filter_obj = NiceGUIErrorFilter()
        record = logging.LogRecord(
            name="nicegui",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Request is not set",
            args=(),
            exc_info=None
        )

        result = filter_obj.filter(record)

        assert result is False  # Should be suppressed

    def test_filter_allows_other_nicegui_errors(self):
        """Test that other NiceGUI errors are not filtered."""
        filter_obj = NiceGUIErrorFilter()
        record = logging.LogRecord(
            name="nicegui",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Some other error",
            args=(),
            exc_info=None
        )

        result = filter_obj.filter(record)

        assert result is True  # Should not be suppressed

    def test_filter_allows_non_error_nicegui_logs(self):
        """Test that non-error NiceGUI logs are not filtered."""
        filter_obj = NiceGUIErrorFilter()
        record = logging.LogRecord(
            name="nicegui",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Request is not set",
            args=(),
            exc_info=None
        )

        result = filter_obj.filter(record)

        assert result is True  # INFO level should not be suppressed

    def test_filter_allows_other_logger_errors(self):
        """Test that errors from other loggers are not filtered."""
        filter_obj = NiceGUIErrorFilter()
        record = logging.LogRecord(
            name="other_logger",
            level=logging.ERROR,
            pathname="",
            lineno=0,
            msg="Request is not set",
            args=(),
            exc_info=None
        )

        result = filter_obj.filter(record)

        assert result is True  # Other loggers should not be affected


class TestFastAPIApp:
    """Test FastAPI application configuration."""

    def test_app_has_correct_title(self):
        """Test that app has correct title."""
        assert app.title == "FlexLink Middleware"

    def test_app_has_correct_version(self):
        """Test that app has correct version."""
        assert app.version == "0.1.0"

    def test_app_has_docs_url(self):
        """Test that app has API documentation URL."""
        assert app.docs_url == "/api/docs"

    def test_app_has_redoc_url(self):
        """Test that app has ReDoc URL."""
        assert app.redoc_url == "/api/redoc"

    def test_app_has_openapi_url(self):
        """Test that app has OpenAPI schema URL."""
        assert app.openapi_url == "/api/openapi.json"


class TestAPIRootEndpoint:
    """Test the API root endpoint."""

    def test_api_root_returns_200(self):
        """Test that API root endpoint returns 200."""
        client = TestClient(app)
        response = client.get("/api")

        assert response.status_code == 200

    def test_api_root_returns_json(self):
        """Test that API root returns JSON response."""
        client = TestClient(app)
        response = client.get("/api")

        assert response.headers["content-type"] == "application/json"

    def test_api_root_contains_message(self):
        """Test that API root contains message."""
        client = TestClient(app)
        response = client.get("/api")
        data = response.json()

        assert "message" in data
        assert data["message"] == "FlexLink Middleware API"

    def test_api_root_contains_version(self):
        """Test that API root contains version information."""
        client = TestClient(app)
        response = client.get("/api")
        data = response.json()

        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_api_root_contains_documentation_links(self):
        """Test that API root contains links to documentation."""
        client = TestClient(app)
        response = client.get("/api")
        data = response.json()

        assert "docs" in data
        assert data["docs"] == "/api/docs"
        assert "redoc" in data
        assert data["redoc"] == "/api/redoc"

    def test_api_root_contains_health_endpoint(self):
        """Test that API root contains health endpoint."""
        client = TestClient(app)
        response = client.get("/api")
        data = response.json()

        assert "health" in data
        assert data["health"] == "/api/health"
