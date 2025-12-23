"""Tests for BaseConnector abstract class."""

import pytest

from flexlink.core.connector import BaseConnector
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.request import IntegrationResponse


@pytest.fixture
def mock_config():
    """Create a mock connector configuration."""
    return ConnectorConfig(
        name="test_connector",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(type="none"),
        timeout=30,
        retry_attempts=3,
    )


def test_base_connector_cannot_instantiate(mock_config):
    """Test that BaseConnector cannot be instantiated directly (ABC enforcement)."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseConnector(mock_config)


def test_subclass_missing_methods_raises_error(mock_config):
    """Test that subclass with missing abstract methods raises TypeError."""

    class IncompleteConnector(BaseConnector):
        """Incomplete connector missing abstract methods."""

        pass

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteConnector(mock_config)


def test_subclass_with_all_methods_works(mock_config):
    """Test that subclass with all abstract methods implemented works correctly."""

    class CompleteConnector(BaseConnector):
        """Complete connector with all abstract methods implemented."""

        async def send_request(self, method, path, data=None, **kwargs):
            """Implement send_request."""
            return IntegrationResponse(
                status_code=200,
                body={"message": "success"}
            )

        async def transform_request(self, data):
            """Implement transform_request."""
            return data

        async def transform_response(self, data):
            """Implement transform_response."""
            return data

    # Should instantiate without errors
    connector = CompleteConnector(mock_config)
    assert connector.get_name() == "test_connector"
    assert connector.is_enabled() is True
    assert connector.get_base_url() == "https://api.example.com"


def test_connector_properties(mock_config):
    """Test connector helper methods."""

    class TestConnector(BaseConnector):
        async def send_request(self, method, path, data=None, **kwargs):
            return IntegrationResponse(status_code=200)

        async def transform_request(self, data):
            return data

        async def transform_response(self, data):
            return data

    connector = TestConnector(mock_config)

    assert connector.get_name() == "test_connector"
    assert connector.is_enabled() is True
    assert connector.get_base_url() == "https://api.example.com"


def test_connector_disabled(mock_config):
    """Test that disabled connector is recognized."""
    mock_config.enabled = False

    class TestConnector(BaseConnector):
        async def send_request(self, method, path, data=None, **kwargs):
            return IntegrationResponse(status_code=200)

        async def transform_request(self, data):
            return data

        async def transform_response(self, data):
            return data

    connector = TestConnector(mock_config)
    assert connector.is_enabled() is False


def test_connector_repr(mock_config):
    """Test connector string representation."""

    class TestConnector(BaseConnector):
        async def send_request(self, method, path, data=None, **kwargs):
            return IntegrationResponse(status_code=200)

        async def transform_request(self, data):
            return data

        async def transform_response(self, data):
            return data

    connector = TestConnector(mock_config)
    repr_str = repr(connector)

    assert "TestConnector" in repr_str
    assert "test_connector" in repr_str
    assert "rest" in repr_str
    assert "enabled=True" in repr_str
