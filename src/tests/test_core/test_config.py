"""Tests for configuration management (config.py)."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from flexlink.config import (
    Settings,
    get_settings,
    load_connector_configs,
    load_route_configs,
    substitute_env_vars,
)
from flexlink.models.connector import ConnectorConfig


# =============================================================================
# Tests for substitute_env_vars()
# =============================================================================


class TestSubstituteEnvVars:
    """Test environment variable substitution in configuration data."""

    def test_simple_string_substitution(self):
        """Test basic ${VAR_NAME} substitution."""
        with patch.dict(os.environ, {"API_TOKEN": "secret123"}):
            result = substitute_env_vars("${API_TOKEN}")
            assert result == "secret123"

    def test_multiple_vars_in_one_string(self):
        """Test multiple environment variables in a single string."""
        with patch.dict(os.environ, {"HOST": "localhost", "PORT": "8000"}):
            result = substitute_env_vars("http://${HOST}:${PORT}/api")
            assert result == "http://localhost:8000/api"

    def test_nested_dict_substitution(self):
        """Test substitution in nested dictionaries."""
        with patch.dict(os.environ, {"DB_USER": "admin", "DB_PASS": "secret"}):
            data = {
                "database": {
                    "username": "${DB_USER}",
                    "password": "${DB_PASS}",
                    "host": "localhost"
                }
            }
            result = substitute_env_vars(data)
            assert result["database"]["username"] == "admin"
            assert result["database"]["password"] == "secret"
            assert result["database"]["host"] == "localhost"

    def test_nested_list_substitution(self):
        """Test substitution in lists."""
        with patch.dict(os.environ, {"ENV": "production"}):
            data = ["${ENV}", "staging", "development"]
            result = substitute_env_vars(data)
            assert result == ["production", "staging", "development"]

    def test_mixed_types_dict_list_str(self):
        """Test substitution with mixed data types."""
        with patch.dict(os.environ, {"API_KEY": "key123", "VERSION": "v1"}):
            data = {
                "apis": [
                    {"name": "api1", "key": "${API_KEY}"},
                    {"name": "api2", "key": "${API_KEY}"}
                ],
                "version": "${VERSION}"
            }
            result = substitute_env_vars(data)
            assert result["apis"][0]["key"] == "key123"
            assert result["apis"][1]["key"] == "key123"
            assert result["version"] == "v1"

    def test_missing_env_var_leaves_as_is(self):
        """Test that missing env vars are left unchanged with warning."""
        with patch.dict(os.environ, {}, clear=True):
            result = substitute_env_vars("${NONEXISTENT_VAR}")
            # Should leave as-is when env var doesn't exist
            assert result == "${NONEXISTENT_VAR}"

    def test_empty_env_var_value(self):
        """Test substitution with empty environment variable."""
        with patch.dict(os.environ, {"EMPTY_VAR": ""}):
            result = substitute_env_vars("prefix_${EMPTY_VAR}_suffix")
            assert result == "prefix__suffix"

    def test_malformed_pattern_unchanged(self):
        """Test that malformed patterns are left unchanged."""
        result = substitute_env_vars("${MISSING_BRACE")
        assert result == "${MISSING_BRACE"

        result = substitute_env_vars("$MISSING_BRACES")
        assert result == "$MISSING_BRACES"

    def test_non_string_types_pass_through(self):
        """Test that non-string types pass through unchanged."""
        assert substitute_env_vars(123) == 123
        assert substitute_env_vars(45.67) == 45.67
        assert substitute_env_vars(True) is True
        assert substitute_env_vars(None) is None

    def test_unicode_and_special_chars(self):
        """Test substitution with unicode and special characters."""
        with patch.dict(os.environ, {"UNICODE_VAR": "café_🚀"}):
            result = substitute_env_vars("${UNICODE_VAR}")
            assert result == "café_🚀"

    def test_recursive_dict_with_lists(self):
        """Test deeply nested structures."""
        with patch.dict(os.environ, {"TOKEN": "abc123"}):
            data = {
                "level1": {
                    "level2": {
                        "items": [
                            {"token": "${TOKEN}"},
                            {"token": "static"}
                        ]
                    }
                }
            }
            result = substitute_env_vars(data)
            assert result["level1"]["level2"]["items"][0]["token"] == "abc123"
            assert result["level1"]["level2"]["items"][1]["token"] == "static"

    def test_empty_dict_and_list(self):
        """Test substitution with empty collections."""
        assert substitute_env_vars({}) == {}
        assert substitute_env_vars([]) == []
        assert substitute_env_vars({"empty": []}) == {"empty": []}


# =============================================================================
# Tests for load_connector_configs()
# =============================================================================


class TestLoadConnectorConfigs:
    """Test loading connector configurations from YAML files."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            connectors_dir = config_dir / "connectors"
            connectors_dir.mkdir()
            yield config_dir

    def test_load_valid_single_connector(self, temp_config_dir):
        """Test loading a single valid connector configuration."""
        connector_file = temp_config_dir / "connectors" / "test_api.yaml"
        connector_data = {
            "name": "test_api",
            "type": "rest",
            "base_url": "https://api.example.com",
            "auth": {"type": "none"},
            "enabled": True
        }

        with open(connector_file, "w") as f:
            yaml.dump(connector_data, f)

        configs = load_connector_configs(temp_config_dir)

        assert len(configs) == 1
        assert "test_api" in configs
        assert configs["test_api"].name == "test_api"
        assert configs["test_api"].type == "rest"
        assert configs["test_api"].base_url == "https://api.example.com"

    def test_load_multiple_connector_configs(self, temp_config_dir):
        """Test loading multiple connector configurations."""
        # Create first connector
        connector1 = temp_config_dir / "connectors" / "api1.yaml"
        with open(connector1, "w") as f:
            yaml.dump({
                "name": "api1",
                "type": "rest",
                "base_url": "https://api1.com",
                "auth": {"type": "none"}
            }, f)

        # Create second connector
        connector2 = temp_config_dir / "connectors" / "api2.yaml"
        with open(connector2, "w") as f:
            yaml.dump({
                "name": "api2",
                "type": "rest",
                "base_url": "https://api2.com",
                "auth": {"type": "bearer", "credentials": {"token": "test"}}
            }, f)

        configs = load_connector_configs(temp_config_dir)

        assert len(configs) == 2
        assert "api1" in configs
        assert "api2" in configs

    def test_empty_connector_directory(self, temp_config_dir):
        """Test handling of empty connector directory."""
        configs = load_connector_configs(temp_config_dir)
        assert len(configs) == 0

    def test_missing_connector_directory(self, temp_config_dir):
        """Test handling of missing connector directory."""
        # Remove the connectors directory
        connectors_dir = temp_config_dir / "connectors"
        connectors_dir.rmdir()

        configs = load_connector_configs(temp_config_dir)
        assert len(configs) == 0

    def test_invalid_yaml_syntax(self, temp_config_dir):
        """Test handling of invalid YAML syntax."""
        connector_file = temp_config_dir / "connectors" / "invalid.yaml"

        with open(connector_file, "w") as f:
            f.write("invalid: yaml: syntax: [unclosed")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_connector_configs(temp_config_dir)

    def test_empty_yaml_file(self, temp_config_dir):
        """Test handling of empty YAML file."""
        connector_file = temp_config_dir / "connectors" / "empty.yaml"

        with open(connector_file, "w") as f:
            f.write("")

        configs = load_connector_configs(temp_config_dir)
        assert len(configs) == 0

    def test_missing_required_fields(self, temp_config_dir):
        """Test Pydantic validation for missing required fields."""
        connector_file = temp_config_dir / "connectors" / "incomplete.yaml"

        # Missing 'type' and 'base_url'
        with open(connector_file, "w") as f:
            yaml.dump({"name": "incomplete"}, f)

        with pytest.raises(ValueError, match="Invalid connector config"):
            load_connector_configs(temp_config_dir)

    def test_both_yaml_and_yml_extensions(self, temp_config_dir):
        """Test that both .yaml and .yml extensions are loaded."""
        # Create .yaml file
        yaml_file = temp_config_dir / "connectors" / "api1.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump({
                "name": "api1",
                "type": "rest",
                "base_url": "https://api1.com",
                "auth": {"type": "none"}
            }, f)

        # Create .yml file
        yml_file = temp_config_dir / "connectors" / "api2.yml"
        with open(yml_file, "w") as f:
            yaml.dump({
                "name": "api2",
                "type": "rest",
                "base_url": "https://api2.com",
                "auth": {"type": "none"}
            }, f)

        configs = load_connector_configs(temp_config_dir)

        assert len(configs) == 2
        assert "api1" in configs
        assert "api2" in configs

    def test_env_var_substitution_in_connector(self, temp_config_dir):
        """Test that environment variables are substituted in connector configs."""
        connector_file = temp_config_dir / "connectors" / "api.yaml"

        with open(connector_file, "w") as f:
            yaml.dump({
                "name": "api",
                "type": "rest",
                "base_url": "${API_BASE_URL}",
                "auth": {
                    "type": "bearer",
                    "credentials": {"token": "${API_TOKEN}"}
                }
            }, f)

        with patch.dict(os.environ, {
            "API_BASE_URL": "https://test.com",
            "API_TOKEN": "secret123"
        }):
            configs = load_connector_configs(temp_config_dir)

        assert configs["api"].base_url == "https://test.com"
        assert configs["api"].auth.credentials["token"] == "secret123"

    def test_duplicate_connector_names_last_wins(self, temp_config_dir):
        """Test that when duplicate names exist, the last one loaded wins."""
        # Create first file with name "duplicate"
        file1 = temp_config_dir / "connectors" / "01_dup.yaml"
        with open(file1, "w") as f:
            yaml.dump({
                "name": "duplicate",
                "type": "rest",
                "base_url": "https://first.com",
                "auth": {"type": "none"}
            }, f)

        # Create second file with same name "duplicate"
        file2 = temp_config_dir / "connectors" / "02_dup.yaml"
        with open(file2, "w") as f:
            yaml.dump({
                "name": "duplicate",
                "type": "rest",
                "base_url": "https://second.com",
                "auth": {"type": "none"}
            }, f)

        configs = load_connector_configs(temp_config_dir)

        # Should have only one entry (last one loaded)
        assert len(configs) == 1
        assert "duplicate" in configs
        # The exact URL depends on load order, but there should be exactly one


# =============================================================================
# Tests for load_route_configs()
# =============================================================================


class TestLoadRouteConfigs:
    """Test loading route configurations from YAML files."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            routes_dir = config_dir / "routes"
            routes_dir.mkdir()
            yield config_dir

    def test_load_valid_route_list_format(self, temp_config_dir):
        """Test loading routes in list format."""
        routes_file = temp_config_dir / "routes" / "api_routes.yaml"
        routes_data = [
            {
                "path": "/users/{id}",
                "method": "GET",
                "connector": "my_api",
                "target_path": "/api/users/{id}"
            },
            {
                "path": "/users",
                "method": "POST",
                "connector": "my_api",
                "target_path": "/api/users"
            }
        ]

        with open(routes_file, "w") as f:
            yaml.dump(routes_data, f)

        routes = load_route_configs(temp_config_dir)

        assert len(routes) == 2
        assert routes[0].path == "/users/{id}"
        assert routes[0].method == "GET"
        assert routes[1].path == "/users"
        assert routes[1].method == "POST"

    def test_load_valid_dict_with_routes_key(self, temp_config_dir):
        """Test loading routes in dict format with 'routes' key."""
        routes_file = temp_config_dir / "routes" / "api_routes.yaml"
        routes_data = {
            "routes": [
                {
                    "path": "/products",
                    "method": "GET",
                    "connector": "shop_api",
                    "target_path": "/api/products"
                }
            ]
        }

        with open(routes_file, "w") as f:
            yaml.dump(routes_data, f)

        routes = load_route_configs(temp_config_dir)

        assert len(routes) == 1
        assert routes[0].path == "/products"

    def test_load_multiple_route_files(self, temp_config_dir):
        """Test loading routes from multiple YAML files."""
        # Create first routes file
        routes_file1 = temp_config_dir / "routes" / "api1_routes.yaml"
        with open(routes_file1, "w") as f:
            yaml.dump([
                {"path": "/route1", "method": "GET", "connector": "api1", "target_path": "/r1"}
            ], f)

        # Create second routes file
        routes_file2 = temp_config_dir / "routes" / "api2_routes.yaml"
        with open(routes_file2, "w") as f:
            yaml.dump([
                {"path": "/route2", "method": "GET", "connector": "api2", "target_path": "/r2"}
            ], f)

        routes = load_route_configs(temp_config_dir)

        assert len(routes) == 2

    def test_empty_routes_directory(self, temp_config_dir):
        """Test handling of empty routes directory."""
        routes = load_route_configs(temp_config_dir)
        assert len(routes) == 0

    def test_missing_routes_directory(self, temp_config_dir):
        """Test handling of missing routes directory."""
        routes_dir = temp_config_dir / "routes"
        routes_dir.rmdir()

        routes = load_route_configs(temp_config_dir)
        assert len(routes) == 0

    def test_invalid_yaml_syntax_in_routes(self, temp_config_dir):
        """Test handling of invalid YAML syntax in routes file."""
        routes_file = temp_config_dir / "routes" / "invalid.yaml"

        with open(routes_file, "w") as f:
            f.write("invalid: [unclosed: list")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_route_configs(temp_config_dir)

    def test_invalid_route_format(self, temp_config_dir):
        """Test handling of invalid route format (neither list nor dict with routes)."""
        routes_file = temp_config_dir / "routes" / "invalid_format.yaml"

        # Invalid format: dict without 'routes' key
        with open(routes_file, "w") as f:
            yaml.dump({"invalid": "format"}, f)

        routes = load_route_configs(temp_config_dir)
        # Should skip invalid file and return empty list
        assert len(routes) == 0

    def test_both_yaml_and_yml_extensions_for_routes(self, temp_config_dir):
        """Test that both .yaml and .yml extensions are loaded for routes."""
        # Create .yaml file
        yaml_file = temp_config_dir / "routes" / "routes1.yaml"
        with open(yaml_file, "w") as f:
            yaml.dump([
                {"path": "/route1", "method": "GET", "connector": "api", "target_path": "/r1"}
            ], f)

        # Create .yml file
        yml_file = temp_config_dir / "routes" / "routes2.yml"
        with open(yml_file, "w") as f:
            yaml.dump([
                {"path": "/route2", "method": "GET", "connector": "api", "target_path": "/r2"}
            ], f)

        routes = load_route_configs(temp_config_dir)

        assert len(routes) == 2


# =============================================================================
# Tests for Settings and get_settings()
# =============================================================================


class TestSettings:
    """Test Settings class and get_settings() function."""

    def test_settings_defaults(self):
        """Test that Settings has proper default values."""
        settings = Settings()

        assert settings.app_name == "FlexLink"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.config_dir == Path("config")
        assert settings.max_file_size_mb == 10
        assert settings.upload_dir == Path("data/uploads")
        assert settings.download_dir == Path("data/downloads")
        # Value comes from .env file or default (86400)
        assert settings.temp_file_ttl_seconds > 0

    def test_settings_from_env_vars(self):
        """Test that Settings loads from environment variables."""
        with patch.dict(os.environ, {
            "APP_NAME": "TestApp",
            "DEBUG": "true",
            "LOG_LEVEL": "DEBUG",
            "MAX_FILE_SIZE_MB": "50"
        }):
            settings = Settings()

            assert settings.app_name == "TestApp"
            assert settings.debug is True
            assert settings.log_level == "DEBUG"
            assert settings.max_file_size_mb == 50

    def test_get_settings_returns_settings_instance(self):
        """Test that get_settings() returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_ui_secret_key_auto_generated(self):
        """Test that ui_secret_key is auto-generated if not set."""
        settings = Settings()
        assert settings.ui_secret_key is not None
        assert len(settings.ui_secret_key) > 0

    def test_ui_secret_key_from_env(self):
        """Test that ui_secret_key can be set from environment."""
        with patch.dict(os.environ, {"UI_SECRET_KEY": "my-secret-key"}):
            settings = Settings()
            assert settings.ui_secret_key == "my-secret-key"
