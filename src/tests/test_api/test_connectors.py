"""Tests for connectors API endpoints - UI MVP Support."""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from flexlink.api.connectors import get_connector_registry, router
from flexlink.core.registry import ConnectorRegistry


@pytest.fixture
def test_app():
    """Create minimal test app with connectors router."""
    app = FastAPI()
    app.include_router(router)
    return app


def test_list_connectors_success(test_app):
    """Test listing all connectors for UI dropdown/selection."""
    # Mock registry with multiple connectors
    mock_registry = Mock(spec=ConnectorRegistry)
    mock_registry.list_connectors.return_value = [
        "api-source",
        "database-target",
        "file-connector"
    ]

    # Mock different connector types
    def get_connector_mock(name):
        if name == "api-source":
            mock_rest = Mock()
            mock_rest.__class__.__name__ = "RestConnector"
            return mock_rest
        elif name == "database-target":
            mock_db = Mock()
            mock_db.__class__.__name__ = "DatabaseConnector"
            return mock_db
        else:
            mock_file = Mock()
            mock_file.__class__.__name__ = "FileConnector"
            return mock_file

    mock_registry.get_connector.side_effect = get_connector_mock

    test_app.dependency_overrides[get_connector_registry] = lambda: mock_registry

    client = TestClient(test_app)
    response = client.get("/v1/connectors")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure for UI
    assert "connectors" in data
    assert "count" in data
    assert data["count"] == 3
    assert isinstance(data["connectors"], list)

    # Verify connector metadata
    connectors = {c["name"]: c for c in data["connectors"]}
    assert "api-source" in connectors
    assert connectors["api-source"]["type"] == "rest"
    assert "description" in connectors["api-source"]

    test_app.dependency_overrides.clear()


def test_list_connectors_empty(test_app):
    """Test empty connector list for UI."""
    mock_registry = Mock(spec=ConnectorRegistry)
    mock_registry.list_connectors.return_value = []

    test_app.dependency_overrides[get_connector_registry] = lambda: mock_registry

    client = TestClient(test_app)
    response = client.get("/v1/connectors")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 0
    assert data["connectors"] == []

    test_app.dependency_overrides.clear()


def test_connectors_response_format(test_app):
    """Test connector response format matches UI expectations."""
    mock_registry = Mock(spec=ConnectorRegistry)
    mock_registry.list_connectors.return_value = ["test-connector"]

    mock_connector = Mock()
    mock_connector.__class__.__name__ = "RestConnector"
    mock_registry.get_connector.return_value = mock_connector

    test_app.dependency_overrides[get_connector_registry] = lambda: mock_registry

    client = TestClient(test_app)
    response = client.get("/v1/connectors")

    assert response.status_code == 200
    data = response.json()

    # Verify each connector has required fields for UI
    connector = data["connectors"][0]
    assert "name" in connector
    assert "type" in connector
    assert "description" in connector
    assert isinstance(connector["name"], str)
    assert isinstance(connector["type"], str)

    test_app.dependency_overrides.clear()
