"""Base connector abstraction for all integration connectors."""

import logging
from abc import ABC, abstractmethod
from typing import Any

from flexlink.models.connector import ConnectorConfig
from flexlink.models.request import IntegrationResponse


class BaseConnector(ABC):
    """
    Abstract base class for all connectors.

    All connector implementations must inherit from this class and implement
    the abstract methods for sending requests and transforming data.
    """

    def __init__(self, config: ConnectorConfig):
        """
        Initialize the connector with configuration.

        Args:
            config: Connector configuration from YAML
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.name}")
        self.logger.info(f"Initializing connector: {config.name}")

    @abstractmethod
    async def send_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> IntegrationResponse:
        """
        Send request to target system.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: Request path/endpoint
            data: Request body data
            **kwargs: Additional request parameters (headers, query params, etc.)

        Returns:
            IntegrationResponse with status code, headers, and body

        Raises:
            Exception: If request fails after all retry attempts
        """
        pass

    @abstractmethod
    async def transform_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform request data before sending to target system.

        Subclasses can override this to apply custom transformations
        specific to the target system's API requirements.

        Args:
            data: Original request data

        Returns:
            Transformed request data
        """
        pass

    @abstractmethod
    async def transform_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform response data before returning to caller.

        Subclasses can override this to normalize response data
        from the target system into a standard format.

        Args:
            data: Original response data from target system

        Returns:
            Transformed response data
        """
        pass

    def is_enabled(self) -> bool:
        """
        Check if connector is enabled.

        Returns:
            True if connector is enabled, False otherwise
        """
        return self.config.enabled

    def get_name(self) -> str:
        """
        Get connector name.

        Returns:
            Connector name from configuration
        """
        return self.config.name

    def get_base_url(self) -> str:
        """
        Get connector base URL.

        Returns:
            Base URL from configuration
        """
        return self.config.base_url

    def __repr__(self) -> str:
        """String representation of connector."""
        return (
            f"{self.__class__.__name__}("
            f"name={self.config.name}, "
            f"type={self.config.type}, "
            f"enabled={self.config.enabled})"
        )
