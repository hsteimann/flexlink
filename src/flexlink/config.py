"""Application configuration management."""

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings

from flexlink.models.connector import ConnectorConfig

logger = logging.getLogger(__name__)


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
        default=3600,
        description="Time to live for temporary files in seconds"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
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
                data: dict[str, Any] = yaml.safe_load(f)

                if not data:
                    logger.warning(f"Empty configuration file: {config_file}")
                    continue

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


def get_settings() -> Settings:
    """
    Get application settings singleton.

    Returns:
        Settings instance with values from environment variables and .env file
    """
    return Settings()
