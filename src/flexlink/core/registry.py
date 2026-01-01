"""Connector registry for managing connector instances."""

import importlib
import logging
from pathlib import Path
from typing import Any

import httpx

from flexlink.config import load_connector_configs
from flexlink.core.connector import BaseConnector
from flexlink.models.connector import ConnectorConfig

logger = logging.getLogger(__name__)


class ConnectorRegistry:
    """
    Registry for managing connector instances.

    This is a singleton-style registry that maintains all loaded connectors
    and provides methods to access them by name.
    """

    def __init__(self) -> None:
        """Initialize empty connector registry."""
        self._connectors: dict[str, BaseConnector] = {}
        self._configs: dict[str, ConnectorConfig] = {}
        logger.info("Connector registry initialized")

    async def load_connectors(
        self,
        http_client: httpx.AsyncClient | None = None,
        config_dir: Path = Path("config"),
    ) -> None:
        """
        Load connector configurations and instantiate connectors.

        Args:
            http_client: Shared async HTTP client for REST connectors
            config_dir: Configuration directory path

        Raises:
            ValueError: If connector configuration is invalid
            ImportError: If connector class cannot be imported
        """
        # Load connector configurations from YAML files
        configs = load_connector_configs(config_dir)
        self._configs = configs

        if not configs:
            logger.warning("No connector configurations found")
            return

        # Instantiate each connector
        for name, config in configs.items():
            if not config.enabled:
                logger.info(f"Skipping disabled connector: {name}")
                continue

            try:
                connector = await self._create_connector(config, http_client)
                self._connectors[name] = connector
                logger.info(f"Registered connector: {name} ({config.type})")
            except Exception as e:
                logger.error(f"Failed to create connector {name}: {e}")
                raise

        logger.info(f"Loaded {len(self._connectors)} active connectors")

    async def _create_connector(
        self,
        config: ConnectorConfig,
        http_client: httpx.AsyncClient | None = None,
    ) -> BaseConnector:
        """
        Create connector instance based on configuration.

        Args:
            config: Connector configuration
            http_client: Shared async HTTP client (for REST connectors)

        Returns:
            Instantiated connector

        Raises:
            ImportError: If connector class cannot be imported
            ValueError: If connector type is unknown
        """
        # Try connector name first (for specialized connectors like priceedge)
        # Fall back to type for generic connectors (rest, file, etc.)
        connector_type = config.type.lower()

        # Map connector types/names to their module paths
        type_mapping = {
            "rest": "flexlink.connectors.rest_connector.RestConnector",
            "priceedge": "flexlink.connectors.priceedge_connector.PriceEdgeConnector",
            "file": "flexlink.connectors.file_connector.FileConnector",
            "postgresql": "flexlink.connectors.postgresql_connector.PostgreSQLConnector",
            "webhook": "flexlink.connectors.webhook_connector.WebhookConnector",
        }

        # Use name if it matches a specialized connector, otherwise use type
        connector_key = config.name if config.name in type_mapping else connector_type

        # Get the module path for this connector
        module_path = type_mapping.get(connector_key)

        if not module_path:
            raise ValueError(
                f"Unknown connector: {config.name} (type: {config.type}). "
                f"Supported: {list(type_mapping.keys())}"
            )

        # Dynamically import the connector class
        try:
            module_name, class_name = module_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            connector_class = getattr(module, class_name)

            # Instantiate connector with appropriate parameters
            connector: BaseConnector
            if connector_type == "rest":
                if http_client is None:
                    raise ValueError("HTTP client required for REST connectors")
                connector = connector_class(config, http_client)
            elif connector_type == "postgresql":
                # Database connectors need DatabaseConnectorConfig
                # Load from connector config's headers field (temporary storage)
                from flexlink.models.database import DatabaseConnectorConfig
                db_config = DatabaseConnectorConfig.model_validate(config.headers)
                connector = connector_class(config, db_config)
                # Initialize connection pool (database connectors only)
                if hasattr(connector, 'initialize_pool'):
                    # Type checkers don't know about this optional method
                    await connector.initialize_pool()  # pyright: ignore[reportAttributeAccessIssue]
            elif connector_type == "webhook":
                # Webhook connectors need WebhookConfig and shared HTTP client
                if http_client is None:
                    raise ValueError("HTTP client required for webhook connectors")
                from flexlink.models.webhook import WebhookConfig
                webhook_config = WebhookConfig.model_validate(config.headers)
                connector = connector_class(config, http_client, webhook_config)
            else:
                connector = connector_class(config)

            return connector

        except ImportError as e:
            raise ImportError(
                f"Failed to import connector class {module_path}: {e}"
            ) from e
        except AttributeError as e:
            raise ImportError(
                f"Connector class {class_name} not found in module {module_name}: {e}"
            ) from e

    def register(self, name: str, connector: BaseConnector) -> None:
        """
        Manually register a connector instance.

        Args:
            name: Connector name/identifier
            connector: Connector instance to register
        """
        self._connectors[name] = connector
        logger.info(f"Manually registered connector: {name}")

    def get_connector(self, name: str) -> BaseConnector:
        """
        Get connector by name.

        Args:
            name: Connector name

        Returns:
            Connector instance

        Raises:
            KeyError: If connector not found
        """
        if name not in self._connectors:
            available = ", ".join(self._connectors.keys())
            raise KeyError(
                f"Connector '{name}' not found. Available connectors: {available}"
            )

        return self._connectors[name]

    def list_connectors(self) -> list[str]:
        """
        List all registered connector names.

        Returns:
            List of connector names
        """
        return list(self._connectors.keys())

    def get_connector_config(self, name: str) -> ConnectorConfig:
        """
        Get connector configuration by name.

        Args:
            name: Connector name

        Returns:
            Connector configuration

        Raises:
            KeyError: If connector configuration not found
        """
        if name not in self._configs:
            raise KeyError(f"Connector configuration '{name}' not found")

        return self._configs[name]

    def has_connector(self, name: str) -> bool:
        """
        Check if connector exists in registry.

        Args:
            name: Connector name

        Returns:
            True if connector exists, False otherwise
        """
        return name in self._connectors

    def get_connector_status(self) -> dict[str, dict[str, Any]]:
        """
        Get status of all connectors.

        Returns:
            Dictionary mapping connector names to their status information
        """
        return {
            name: {
                "enabled": connector.is_enabled(),
                "type": connector.config.type,
                "base_url": connector.get_base_url(),
            }
            for name, connector in self._connectors.items()
        }

    def __len__(self) -> int:
        """Get number of registered connectors."""
        return len(self._connectors)

    def __repr__(self) -> str:
        """String representation of registry."""
        return f"ConnectorRegistry(connectors={len(self._connectors)})"
