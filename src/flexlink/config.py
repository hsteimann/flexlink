"""Application configuration management."""

import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

from flexlink.models.connector import ConnectorConfig
from flexlink.models.transformation import RouteConfig

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


def substitute_env_vars(data: Any) -> Any:
    """
    Recursively substitute environment variables in configuration data.

    Replaces ${VAR_NAME} patterns with values from environment variables.

    Args:
        data: Configuration data (dict, list, str, or other types)

    Returns:
        Data with environment variables substituted
    """
    if isinstance(data, dict):
        return {k: substitute_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [substitute_env_vars(item) for item in data]
    elif isinstance(data, str):
        # Replace ${VAR_NAME} with environment variable value
        pattern = r'\$\{([^}]+)\}'

        def replace_var(match: re.Match[str]) -> str:
            var_name = match.group(1)
            value = os.getenv(var_name)
            if value is None:
                logger.warning(f"Environment variable {var_name} not set, leaving as-is")
                return match.group(0)
            return value

        return re.sub(pattern, replace_var, data)
    else:
        return data


class Settings(BaseSettings):
    """Application settings from environment variables and .env file."""

    app_name: str = Field(default="FlexLink", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    config_dir: Path = Field(default=Path("config"), description="Configuration directory")

    # File processing settings
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file size in MB for uploads"
    )
    upload_dir: Path = Field(
        default=Path("data/uploads"),
        description="Directory for uploaded files"
    )
    download_dir: Path = Field(
        default=Path("data/downloads"),
        description="Directory for generated/downloaded files"
    )
    temp_file_ttl_seconds: int = Field(
        default=86400,  # 24 hours
        description="Time to live for temporary files in seconds (default: 86400 = 24 hours)"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Allow connector-specific env vars (used in YAML substitution)
    }


def load_connector_configs(config_dir: Path) -> dict[str, ConnectorConfig]:
    """
    Load all connector configurations from YAML files in the config/connectors directory.

    Args:
        config_dir: Base configuration directory path

    Returns:
        Dictionary mapping connector names to their configurations

    Raises:
        FileNotFoundError: If config directory doesn't exist
        ValueError: If connector configuration is invalid
    """
    connectors: dict[str, ConnectorConfig] = {}
    connector_dir = config_dir / "connectors"

    if not connector_dir.exists():
        logger.warning(f"Connector directory not found: {connector_dir}")
        return connectors

    yaml_files = list(connector_dir.glob("*.yaml")) + list(connector_dir.glob("*.yml"))

    if not yaml_files:
        logger.warning(f"No connector configuration files found in {connector_dir}")
        return connectors

    for config_file in yaml_files:
        try:
            with open(config_file, encoding="utf-8") as f:
                raw_data: dict[str, Any] = yaml.safe_load(f)

                if not raw_data:
                    logger.warning(f"Empty configuration file: {config_file}")
                    continue

                # Substitute environment variables
                data = substitute_env_vars(raw_data)

                # Use Pydantic model_validate for validation
                config = ConnectorConfig.model_validate(data)
                connectors[config.name] = config
                logger.info(
                    f"Loaded connector configuration: {config.name} from {config_file.name}"
                )

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file {config_file}: {e}")
            raise ValueError(f"Invalid YAML in {config_file}: {e}") from e
        except Exception as e:
            logger.error(f"Failed to load connector config from {config_file}: {e}")
            raise ValueError(f"Invalid connector config in {config_file}: {e}") from e

    logger.info(f"Loaded {len(connectors)} connector configurations")
    return connectors


def load_route_configs(config_dir: Path) -> list[RouteConfig]:
    """
    Load all route configurations from YAML files in the config/routes directory.

    Args:
        config_dir: Base configuration directory path

    Returns:
        List of route configurations

    Raises:
        FileNotFoundError: If config directory doesn't exist
        ValueError: If route configuration is invalid
    """
    routes: list[RouteConfig] = []
    routes_dir = config_dir / "routes"

    if not routes_dir.exists():
        logger.warning(f"Routes directory not found: {routes_dir}")
        return routes

    yaml_files = list(routes_dir.glob("*.yaml")) + list(routes_dir.glob("*.yml"))

    if not yaml_files:
        logger.warning(f"No route configuration files found in {routes_dir}")
        return routes

    for config_file in yaml_files:
        try:
            with open(config_file, encoding="utf-8") as f:
                data: Any = yaml.safe_load(f)

                if not data:
                    logger.warning(f"Empty configuration file: {config_file}")
                    continue

                # Handle both formats:
                # 1. Direct list: [{"path": "/foo", ...}, ...]
                # 2. Dict with "routes" key: {"routes": [{"path": "/foo", ...}, ...]}
                route_list: list[dict[str, Any]] = []
                if isinstance(data, list):
                    route_list = data
                elif isinstance(data, dict) and "routes" in data:
                    route_list = data["routes"]
                else:
                    logger.warning(
                        f"Invalid route file format in {config_file}. "
                        f"Expected list or dict with 'routes' key"
                    )
                    continue

                # Each YAML file contains a list of routes
                for route_data in route_list:
                    route = RouteConfig.model_validate(route_data)
                    routes.append(route)

                logger.info(
                    f"Loaded {len(route_list)} route configurations from {config_file.name}"
                )

        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML file {config_file}: {e}")
            raise ValueError(f"Invalid YAML in {config_file}: {e}") from e
        except Exception as e:
            logger.error(f"Failed to load route config from {config_file}: {e}")
            raise ValueError(f"Invalid route config in {config_file}: {e}") from e

    logger.info(f"Loaded {len(routes)} total route configurations")
    return routes


def get_settings() -> Settings:
    """
    Get application settings singleton.

    Returns:
        Settings instance with values from environment variables and .env file
    """
    return Settings()
