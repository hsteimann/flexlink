"""Base database connector for all database implementations (Simplified MVP)."""

import logging
import time
from abc import abstractmethod
from typing import Any

from flexlink.core.connector import BaseConnector
from flexlink.models.connector import ConnectorConfig
from flexlink.models.database import DatabaseConnectorConfig, DatabaseOperation, DatabaseWriteResult
from flexlink.models.request import IntegrationResponse

logger = logging.getLogger(__name__)


class DatabaseConnector(BaseConnector):
    """
    Abstract base class for database connectors (Simplified MVP).

    Simplified version for v0.3.0:
    - Direct writes (no batching)
    - INSERT operation only initially
    - Connection pooling (delegated to subclasses)
    - Simple operation routing

    Future enhancements (v0.4.0+):
    - Batch accumulation and flushing
    - UPDATE and UPSERT operations
    - Transaction management
    """

    def __init__(self, config: ConnectorConfig, db_config: DatabaseConnectorConfig):
        """
        Initialize database connector.

        Args:
            config: Base connector configuration
            db_config: Database-specific configuration
        """
        super().__init__(config)
        self.db_config = db_config

        # Statistics tracking
        self.total_writes = 0
        self.successful_writes = 0
        self.failed_writes = 0

    async def send_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> IntegrationResponse:
        """
        Write data to database.

        For database connectors, 'method' maps to database operation:
        - POST → INSERT
        - PUT → UPDATE (future)
        - PATCH → UPSERT (future)

        Args:
            method: HTTP method (maps to DB operation)
            path: Unused (kept for interface compatibility)
            data: Data to write to database
            **kwargs: Additional parameters (operation override)

        Returns:
            IntegrationResponse with write result
        """
        if not data:
            return IntegrationResponse(
                status_code=400,
                error="No data provided for database write"
            )

        # Determine operation
        operation = kwargs.get("operation") or self._method_to_operation(method)

        # Direct write (no batching in simplified version)
        return await self._write_immediate(data, operation)

    async def _write_immediate(
        self, data: dict[str, Any], operation: DatabaseOperation
    ) -> IntegrationResponse:
        """
        Write data immediately to database.

        Args:
            data: Data to write
            operation: Database operation

        Returns:
            IntegrationResponse with write result
        """
        start_time = time.time()
        self.total_writes += 1

        try:
            result = await self._execute_operation(data, operation)
            duration_ms = (time.time() - start_time) * 1000

            if result.success:
                self.successful_writes += 1
                return IntegrationResponse(
                    status_code=200,
                    body={
                        "success": True,
                        "rows_affected": result.rows_affected,
                        "duration_ms": duration_ms,
                        "operation": operation.value
                    }
                )
            else:
                self.failed_writes += 1
                return IntegrationResponse(
                    status_code=500,
                    error=result.error,
                    body={"duration_ms": duration_ms, "operation": operation.value}
                )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            self.failed_writes += 1
            logger.error(f"Database write failed: {e}")
            return IntegrationResponse(
                status_code=500,
                error=f"Database write failed: {str(e)}",
                body={"duration_ms": duration_ms}
            )

    def _method_to_operation(self, method: str) -> DatabaseOperation:
        """
        Map HTTP method to database operation.

        Args:
            method: HTTP method

        Returns:
            Database operation
        """
        method_upper = method.upper()
        mapping = {
            "POST": DatabaseOperation.INSERT,
            "PUT": DatabaseOperation.UPDATE,
            "PATCH": DatabaseOperation.UPSERT,
            "DELETE": DatabaseOperation.DELETE,
        }
        return mapping.get(method_upper, self.db_config.default_operation)

    def get_stats(self) -> dict[str, Any]:
        """
        Get database connector statistics.

        Returns:
            Dictionary with write statistics
        """
        return {
            "total_writes": self.total_writes,
            "successful_writes": self.successful_writes,
            "failed_writes": self.failed_writes,
            "success_rate": (
                self.successful_writes / self.total_writes
                if self.total_writes > 0
                else 0.0
            ),
        }

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    async def _execute_operation(
        self, data: dict[str, Any], operation: DatabaseOperation
    ) -> DatabaseWriteResult:
        """
        Execute database operation.

        Args:
            data: Data to write
            operation: Database operation type

        Returns:
            DatabaseWriteResult with operation outcome
        """
        pass

    @abstractmethod
    async def initialize_pool(self) -> None:
        """Initialize database connection pool."""
        pass

    @abstractmethod
    async def close_pool(self) -> None:
        """Close database connection pool."""
        pass

    # Default transformer implementations (can be overridden)

    async def transform_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """No transformation by default - data should already be validated."""
        return data

    async def transform_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """No transformation by default."""
        return data
