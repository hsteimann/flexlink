"""Tests for connector models."""

import pytest
from pydantic import ValidationError

from flexlink.models.connector import AuthConfig, ConnectorConfig


def test_auth_config_valid():
    """Test valid AuthConfig creation."""
    auth = AuthConfig(
        type="bearer",
        credentials={"token": "test-token"}
    )
    assert auth.type == "bearer"
    assert auth.credentials["token"] == "test-token"


def test_auth_config_none_type():
    """Test AuthConfig with no authentication."""
    auth = AuthConfig(type="none")
    assert auth.type == "none"
    assert auth.credentials == {}


def test_connector_config_minimal():
    """Test ConnectorConfig with minimal required fields."""
    config = ConnectorConfig(
        name="test_connector",
        type="rest",
        base_url="https://api.example.com"
    )
    assert config.name == "test_connector"
    assert config.type == "rest"
    assert config.base_url == "https://api.example.com"
    assert config.timeout == 30  # Default value
    assert config.retry_attempts == 3  # Default value
    assert config.enabled is True  # Default value


def test_connector_config_with_auth():
    """Test ConnectorConfig with authentication."""
    config = ConnectorConfig(
        name="secure_connector",
        type="rest",
        base_url="https://api.example.com",
        auth=AuthConfig(
            type="bearer",
            credentials={"token": "secret-token"}
        )
    )
    assert config.auth.type == "bearer"
    assert config.auth.credentials["token"] == "secret-token"


def test_connector_config_with_headers():
    """Test ConnectorConfig with custom headers."""
    config = ConnectorConfig(
        name="custom_connector",
        type="rest",
        base_url="https://api.example.com",
        headers={"Content-Type": "application/json", "X-Custom": "value"}
    )
    assert config.headers["Content-Type"] == "application/json"
    assert config.headers["X-Custom"] == "value"


def test_connector_config_custom_timeout():
    """Test ConnectorConfig with custom timeout and retry settings."""
    config = ConnectorConfig(
        name="slow_connector",
        type="rest",
        base_url="https://api.example.com",
        timeout=60,
        retry_attempts=5
    )
    assert config.timeout == 60
    assert config.retry_attempts == 5


def test_connector_config_disabled():
    """Test disabled connector."""
    config = ConnectorConfig(
        name="disabled_connector",
        type="rest",
        base_url="https://api.example.com",
        enabled=False
    )
    assert config.enabled is False


def test_connector_config_missing_required_fields():
    """Test that missing required fields raises ValidationError."""
    with pytest.raises(ValidationError):
        ConnectorConfig(name="incomplete")  # Missing type and base_url


def test_connector_config_serialization():
    """Test model serialization to dict."""
    config = ConnectorConfig(
        name="test",
        type="rest",
        base_url="https://api.example.com"
    )
    data = config.model_dump()
    assert data["name"] == "test"
    assert data["type"] == "rest"
    assert data["base_url"] == "https://api.example.com"
