"""Tests for ConnectorRegistry (registry.py)."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import yaml

from flexlink.core.registry import ConnectorRegistry
from flexlink.models.connector import AuthConfig, ConnectorConfig


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        connectors_dir = config_dir / "connectors"
        connectors_dir.mkdir()
        yield config_dir


@pytest.fixture
async def http_client():
    """Create httpx async client for testing."""
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture
def registry():
    """Create fresh ConnectorRegistry instance."""
    return ConnectorRegistry()


# =============================================================================
# Tests for __init__()
# =============================================================================


class TestRegistryInitialization:
    """Test registry initialization."""

    def test_registry_initialization(self):
        """Test that registry initializes with empty connectors."""
        registry = ConnectorRegistry()

        assert len(registry._connectors) == 0
        assert len(registry._configs) == 0
        assert len(registry) == 0

    def test_registry_repr(self):
        """Test string representation of registry."""
        registry = ConnectorRegistry()

        assert repr(registry) == "ConnectorRegistry(connectors=0)"


# =============================================================================
# Tests for load_connectors()
# =============================================================================


class TestLoadConnectors:
    """Test loading connectors from configuration."""

    @pytest.mark.asyncio
    async def test_load_connectors_empty_directory(self, registry, temp_config_dir, http_client):
        """Test loading from empty connectors directory."""
        await registry.load_connectors(http_client, temp_config_dir)

        assert len(registry) == 0
        assert registry.list_connectors() == []

    @pytest.mark.asyncio
    async def test_load_connectors_no_configs_found(self, registry, temp_config_dir, http_client, caplog):
        """Test warning when no connector configurations found."""
        await registry.load_connectors(http_client, temp_config_dir)

        assert "No connector configurations found" in caplog.text

    @pytest.mark.asyncio
    async def test_load_connectors_rest_connector(self, registry, temp_config_dir, http_client):
        """Test loading REST connector."""
        # Create REST connector config
        config_file = temp_config_dir / "connectors" / "test_api.yaml"
        config_data = {
            "name": "test_api",
            "type": "rest",
            "enabled": True,
            "base_url": "https://api.example.com",
            "auth": {
                "type": "bearer",
                "credentials": {"token": "test_token"}
            }
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        await registry.load_connectors(http_client, temp_config_dir)

        assert len(registry) == 1
        assert registry.has_connector("test_api")
        connector = registry.get_connector("test_api")
        assert connector.config.type == "rest"

    @pytest.mark.asyncio
    async def test_load_connectors_file_connector(self, registry, temp_config_dir, http_client):
        """Test loading File connector."""
        config_file = temp_config_dir / "connectors" / "file_source.yaml"
        config_data = {
            "name": "file_source",
            "type": "file",
            "enabled": True,
            "base_url": "data/samples"
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        await registry.load_connectors(http_client, temp_config_dir)

        assert len(registry) == 1
        assert registry.has_connector("file_source")
        connector = registry.get_connector("file_source")
        assert connector.config.type == "file"

    @pytest.mark.asyncio
    async def test_load_connectors_disabled_connector_skipped(
        self, registry, temp_config_dir, http_client, caplog
    ):
        """Test that disabled connectors are skipped."""
        config_file = temp_config_dir / "connectors" / "disabled.yaml"
        config_data = {
            "name": "disabled",
            "type": "rest",
            "enabled": False,
            "base_url": "https://api.example.com"
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with caplog.at_level("INFO"):
            await registry.load_connectors(http_client, temp_config_dir)

        assert len(registry) == 0
        assert not registry.has_connector("disabled")
        assert "Skipping disabled connector: disabled" in caplog.text

    @pytest.mark.asyncio
    async def test_load_connectors_multiple_connectors(self, registry, temp_config_dir, http_client):
        """Test loading multiple connectors."""
        # Create first connector
        config1 = temp_config_dir / "connectors" / "api1.yaml"
        with open(config1, "w") as f:
            yaml.dump({
                "name": "api1",
                "type": "rest",
                "enabled": True,
                "base_url": "https://api1.example.com"
            }, f)

        # Create second connector
        config2 = temp_config_dir / "connectors" / "api2.yaml"
        with open(config2, "w") as f:
            yaml.dump({
                "name": "api2",
                "type": "file",
                "enabled": True,
                "base_url": "data/files"
            }, f)

        await registry.load_connectors(http_client, temp_config_dir)

        assert len(registry) == 2
        assert registry.has_connector("api1")
        assert registry.has_connector("api2")

    @pytest.mark.asyncio
    async def test_load_connectors_creation_failure_raises(
        self, registry, temp_config_dir, http_client
    ):
        """Test that connector creation failure raises exception."""
        config_file = temp_config_dir / "connectors" / "invalid.yaml"
        config_data = {
            "name": "invalid",
            "type": "unknown_type",  # This will cause creation to fail
            "enabled": True,
            "base_url": "https://api.example.com"
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError, match="Unknown connector"):
            await registry.load_connectors(http_client, temp_config_dir)


# =============================================================================
# Tests for _create_connector()
# =============================================================================


class TestCreateConnector:
    """Test connector creation logic."""

    @pytest.mark.asyncio
    async def test_create_rest_connector_requires_http_client(self, registry):
        """Test that REST connector creation requires HTTP client."""
        config = ConnectorConfig(
            name="test_api",
            type="rest",
            base_url="https://api.example.com"
        )

        with pytest.raises(ValueError, match="HTTP client required for REST connectors"):
            await registry._create_connector(config, http_client=None)

    @pytest.mark.asyncio
    async def test_create_webhook_connector_requires_http_client(self, registry):
        """Test that webhook connector creation requires HTTP client."""
        config = ConnectorConfig(
            name="test_webhook",
            type="webhook",
            base_url="https://api.example.com",
            headers={
                "webhook_url": "https://destination.example.com",
                "timeout_seconds": 30
            }
        )

        with pytest.raises(ValueError, match="HTTP client required for webhook connectors"):
            await registry._create_connector(config, http_client=None)

    @pytest.mark.asyncio
    async def test_create_unknown_connector_type(self, registry, http_client):
        """Test that unknown connector type raises ValueError."""
        config = ConnectorConfig(
            name="unknown",
            type="unknown_type",
            base_url="https://api.example.com"
        )

        with pytest.raises(ValueError, match="Unknown connector"):
            await registry._create_connector(config, http_client)

    @pytest.mark.asyncio
    async def test_create_postgresql_connector(self, registry):
        """Test creating PostgreSQL connector."""
        config = ConnectorConfig(
            name="test_db",
            type="postgresql",
            base_url="postgresql://localhost/testdb",
            headers={
                "connection_string": "postgresql://user:pass@localhost/testdb",
                "database_type": "postgresql",
                "table_name": "orders"
            }
        )

        # Mock the initialize_pool method
        with patch(
            "flexlink.connectors.postgresql_connector.PostgreSQLConnector.initialize_pool",
            new_callable=AsyncMock
        ):
            connector = await registry._create_connector(config)

        assert connector.config.name == "test_db"
        assert connector.config.type == "postgresql"

    @pytest.mark.asyncio
    async def test_create_webhook_connector(self, registry, http_client):
        """Test creating webhook connector."""
        config = ConnectorConfig(
            name="test_webhook",
            type="webhook",
            base_url="https://api.example.com",
            headers={
                "webhook_url": "https://destination.example.com",
                "timeout_seconds": 30
            }
        )

        connector = await registry._create_connector(config, http_client)

        assert connector.config.name == "test_webhook"
        assert connector.config.type == "webhook"

    @pytest.mark.asyncio
    async def test_create_priceedge_specialized_connector(self, registry, http_client):
        """Test creating PriceEdge specialized connector using name-first lookup."""
        config = ConnectorConfig(
            name="priceedge",
            type="rest",
            base_url="https://api.priceedge.eu"
        )

        connector = await registry._create_connector(config, http_client)

        # Should create PriceEdgeConnector, not generic RestConnector
        assert connector.__class__.__name__ == "PriceEdgeConnector"
        assert connector.config.name == "priceedge"

    @pytest.mark.asyncio
    async def test_create_connector_import_error(self, registry, http_client):
        """Test that ImportError is raised for invalid module."""
        config = ConnectorConfig(
            name="test",
            type="rest",
            base_url="https://api.example.com"
        )

        # Mock importlib to raise ImportError
        with patch("flexlink.core.registry.importlib.import_module") as mock_import:
            mock_import.side_effect = ImportError("Module not found")

            with pytest.raises(ImportError, match="Failed to import connector class"):
                await registry._create_connector(config, http_client)

    @pytest.mark.asyncio
    async def test_create_connector_attribute_error(self, registry, http_client):
        """Test that ImportError is raised for missing class."""
        config = ConnectorConfig(
            name="test",
            type="rest",
            base_url="https://api.example.com"
        )

        # Mock the module to not have the expected class
        with patch("flexlink.core.registry.importlib.import_module") as mock_import:
            mock_module = MagicMock(spec=[])  # Empty module with no attributes
            mock_import.return_value = mock_module
            # When getattr is called on mock_module, it will raise AttributeError
            del mock_module.RestConnector

            with pytest.raises(ImportError, match="Connector class .* not found"):
                await registry._create_connector(config, http_client)


# =============================================================================
# Tests for register()
# =============================================================================


class TestRegisterConnector:
    """Test manual connector registration."""

    def test_register_connector(self, registry, caplog):
        """Test manually registering a connector."""
        mock_connector = MagicMock()
        mock_connector.config.name = "manual"

        with caplog.at_level("INFO"):
            registry.register("manual", mock_connector)

        assert registry.has_connector("manual")
        assert registry.get_connector("manual") == mock_connector
        assert "Manually registered connector: manual" in caplog.text

    def test_register_multiple_connectors(self, registry):
        """Test registering multiple connectors."""
        connector1 = MagicMock()
        connector2 = MagicMock()

        registry.register("conn1", connector1)
        registry.register("conn2", connector2)

        assert len(registry) == 2
        assert registry.list_connectors() == ["conn1", "conn2"]


# =============================================================================
# Tests for get_connector()
# =============================================================================


class TestGetConnector:
    """Test getting connectors from registry."""

    def test_get_connector_success(self, registry):
        """Test getting existing connector."""
        mock_connector = MagicMock()
        registry.register("test", mock_connector)

        result = registry.get_connector("test")

        assert result == mock_connector

    def test_get_connector_not_found(self, registry):
        """Test that KeyError is raised for non-existent connector."""
        registry.register("existing", MagicMock())

        with pytest.raises(KeyError, match="Connector 'missing' not found"):
            registry.get_connector("missing")

    def test_get_connector_error_lists_available(self, registry):
        """Test that error message lists available connectors."""
        registry.register("conn1", MagicMock())
        registry.register("conn2", MagicMock())

        with pytest.raises(KeyError, match="Available connectors: conn1, conn2"):
            registry.get_connector("missing")


# =============================================================================
# Tests for list_connectors()
# =============================================================================


class TestListConnectors:
    """Test listing registered connectors."""

    def test_list_connectors_empty(self, registry):
        """Test listing when no connectors registered."""
        assert registry.list_connectors() == []

    def test_list_connectors_multiple(self, registry):
        """Test listing multiple connectors."""
        registry.register("conn1", MagicMock())
        registry.register("conn2", MagicMock())
        registry.register("conn3", MagicMock())

        connectors = registry.list_connectors()

        assert len(connectors) == 3
        assert "conn1" in connectors
        assert "conn2" in connectors
        assert "conn3" in connectors


# =============================================================================
# Tests for get_connector_config()
# =============================================================================


class TestGetConnectorConfig:
    """Test getting connector configurations."""

    def test_get_connector_config_success(self, registry):
        """Test getting existing connector configuration."""
        config = ConnectorConfig(
            name="test",
            type="rest",
            base_url="https://api.example.com"
        )
        registry._configs["test"] = config

        result = registry.get_connector_config("test")

        assert result == config
        assert result.name == "test"

    def test_get_connector_config_not_found(self, registry):
        """Test that KeyError is raised for non-existent config."""
        registry._configs["existing"] = ConnectorConfig(
            name="existing",
            type="rest",
            base_url="https://api.example.com"
        )

        with pytest.raises(KeyError, match="Connector configuration 'missing' not found"):
            registry.get_connector_config("missing")


# =============================================================================
# Tests for has_connector()
# =============================================================================


class TestHasConnector:
    """Test checking connector existence."""

    def test_has_connector_exists(self, registry):
        """Test has_connector returns True for existing connector."""
        registry.register("test", MagicMock())

        assert registry.has_connector("test") is True

    def test_has_connector_not_exists(self, registry):
        """Test has_connector returns False for non-existent connector."""
        assert registry.has_connector("missing") is False

    def test_has_connector_after_removal(self, registry):
        """Test has_connector after connector is removed."""
        registry.register("test", MagicMock())
        assert registry.has_connector("test") is True

        # Remove connector
        del registry._connectors["test"]

        assert registry.has_connector("test") is False


# =============================================================================
# Tests for get_connector_status()
# =============================================================================


class TestGetConnectorStatus:
    """Test getting connector status information."""

    def test_get_connector_status_empty(self, registry):
        """Test status for empty registry."""
        status = registry.get_connector_status()

        assert status == {}

    def test_get_connector_status_single_connector(self, registry):
        """Test status for single connector."""
        mock_connector = MagicMock()
        mock_connector.is_enabled.return_value = True
        mock_connector.config.type = "rest"
        mock_connector.get_base_url.return_value = "https://api.example.com"

        registry.register("test", mock_connector)

        status = registry.get_connector_status()

        assert "test" in status
        assert status["test"]["enabled"] is True
        assert status["test"]["type"] == "rest"
        assert status["test"]["base_url"] == "https://api.example.com"

    def test_get_connector_status_multiple_connectors(self, registry):
        """Test status for multiple connectors."""
        mock_conn1 = MagicMock()
        mock_conn1.is_enabled.return_value = True
        mock_conn1.config.type = "rest"
        mock_conn1.get_base_url.return_value = "https://api1.example.com"

        mock_conn2 = MagicMock()
        mock_conn2.is_enabled.return_value = False
        mock_conn2.config.type = "file"
        mock_conn2.get_base_url.return_value = "data/files"

        registry.register("conn1", mock_conn1)
        registry.register("conn2", mock_conn2)

        status = registry.get_connector_status()

        assert len(status) == 2
        assert status["conn1"]["enabled"] is True
        assert status["conn2"]["enabled"] is False


# =============================================================================
# Tests for __len__()
# =============================================================================


class TestRegistryLength:
    """Test registry length operations."""

    def test_len_empty_registry(self, registry):
        """Test length of empty registry."""
        assert len(registry) == 0

    def test_len_with_connectors(self, registry):
        """Test length with multiple connectors."""
        registry.register("conn1", MagicMock())
        registry.register("conn2", MagicMock())
        registry.register("conn3", MagicMock())

        assert len(registry) == 3

    def test_len_after_registration(self, registry):
        """Test that length updates after registration."""
        assert len(registry) == 0

        registry.register("test", MagicMock())
        assert len(registry) == 1

        registry.register("test2", MagicMock())
        assert len(registry) == 2


# =============================================================================
# Tests for __repr__()
# =============================================================================


class TestRegistryRepr:
    """Test registry string representation."""

    def test_repr_empty(self, registry):
        """Test repr for empty registry."""
        assert repr(registry) == "ConnectorRegistry(connectors=0)"

    def test_repr_with_connectors(self, registry):
        """Test repr with connectors."""
        registry.register("conn1", MagicMock())
        registry.register("conn2", MagicMock())

        assert repr(registry) == "ConnectorRegistry(connectors=2)"

    def test_repr_updates_dynamically(self, registry):
        """Test that repr updates as connectors are added."""
        assert repr(registry) == "ConnectorRegistry(connectors=0)"

        registry.register("test", MagicMock())
        assert repr(registry) == "ConnectorRegistry(connectors=1)"
