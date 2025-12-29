"""PostgreSQL database connector (Simplified MVP)."""

import logging
import time
from typing import Any

import psycopg
from psycopg import sql
from psycopg_pool import AsyncConnectionPool

from flexlink.connectors.database_connector import DatabaseConnector
from flexlink.models.connector import ConnectorConfig
from flexlink.models.database import DatabaseConnectorConfig, DatabaseOperation, DatabaseWriteResult

logger = logging.getLogger(__name__)


class PostgreSQLConnector(DatabaseConnector):
    """
    PostgreSQL database connector (Simplified MVP).

    Features:
    - INSERT operation (primary use case)
    - Connection pooling for production reliability
    - Parameterized queries (SQL injection protection)
    - Async/await for non-blocking I/O

    Future enhancements (v0.4.0+):
    - UPDATE and UPSERT operations
    - Batch processing with COPY protocol
    - Transaction management
    """

    def __init__(self, config: ConnectorConfig, db_config: DatabaseConnectorConfig):
        """
        Initialize PostgreSQL connector.

        Args:
            config: Base connector configuration
            db_config: Database-specific configuration
        """
        super().__init__(config, db_config)
        self.pool: AsyncConnectionPool | None = None

    async def initialize_pool(self) -> None:
        """
        Initialize PostgreSQL connection pool.

        Creates an async connection pool with configured min/max connections.
        """
        try:
            # Build connection string with SSL settings
            conninfo = self.db_config.connection_string
            if self.db_config.ssl_enabled and "sslmode" not in conninfo:
                # Add sslmode as URL parameter
                separator = "?" if "?" not in conninfo else "&"
                conninfo += f"{separator}sslmode=require"

            self.pool = AsyncConnectionPool(
                conninfo=conninfo,
                min_size=self.db_config.pool.min_size,
                max_size=self.db_config.pool.max_size,
                timeout=self.db_config.pool.timeout_seconds,
                max_idle=self.db_config.pool.max_idle_seconds,
                open=True,  # Open pool immediately
            )

            logger.info(
                f"PostgreSQL connection pool initialized: "
                f"min={self.db_config.pool.min_size}, "
                f"max={self.db_config.pool.max_size}, "
                f"table={self.db_config.table_name}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL connection pool: {e}")
            raise

    async def close_pool(self) -> None:
        """Close PostgreSQL connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection pool closed")

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
        if operation == DatabaseOperation.INSERT:
            return await self._execute_insert(data)
        elif operation == DatabaseOperation.UPDATE:
            return await self._execute_update(data)
        elif operation == DatabaseOperation.UPSERT:
            return await self._execute_upsert(data)
        else:
            return DatabaseWriteResult(
                success=False,
                error=f"Unsupported operation: {operation} (only INSERT supported in v0.3.0)"
            )

    async def _execute_insert(self, data: dict[str, Any]) -> DatabaseWriteResult:
        """
        Execute INSERT operation.

        Args:
            data: Data to insert

        Returns:
            DatabaseWriteResult with insert outcome
        """
        if not self.pool:
            return DatabaseWriteResult(
                success=False,
                error="Connection pool not initialized. Call initialize_pool() first."
            )

        start_time = time.time()

        try:
            # Build INSERT query using psycopg.sql for type safety
            table_name = self._get_full_table_name()
            columns = list(data.keys())
            values = [data[col] for col in columns]

            # Parse table name (handle schema.table format)
            if "." in table_name:
                schema_name, simple_table = table_name.split(".", 1)
                table_identifier = sql.Identifier(schema_name, simple_table)
            else:
                table_identifier = sql.Identifier(table_name)

            # Build query: INSERT INTO table (col1, col2) VALUES (%s, %s)
            query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                table_identifier,
                sql.SQL(", ").join(map(sql.Identifier, columns)),
                sql.SQL(", ").join(sql.Placeholder() * len(columns))
            )

            # Execute with connection from pool
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, values)
                    rows_affected = cur.rowcount

            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"INSERT successful: {rows_affected} row(s) inserted "
                f"into {table_name} ({duration_ms:.2f}ms)"
            )

            return DatabaseWriteResult(
                success=True,
                rows_affected=rows_affected,
                duration_ms=duration_ms
            )

        except psycopg.errors.UniqueViolation as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.warning(f"INSERT failed - duplicate key: {e}")
            return DatabaseWriteResult(
                success=False,
                rows_failed=1,
                error=f"Duplicate key violation: {str(e)}",
                duration_ms=duration_ms
            )

        except psycopg.errors.Error as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"INSERT failed - database error: {e}")
            return DatabaseWriteResult(
                success=False,
                rows_failed=1,
                error=f"Database error: {str(e)}",
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(f"INSERT failed - unexpected error: {e}")
            return DatabaseWriteResult(
                success=False,
                rows_failed=1,
                error=f"Unexpected error: {str(e)}",
                duration_ms=duration_ms
            )

    async def _execute_update(self, data: dict[str, Any]) -> DatabaseWriteResult:
        """
        Execute UPDATE operation.

        Note: Not implemented in v0.3.0 (simplified version).
        Will be added in v0.4.0.

        Args:
            data: Data to update (must include primary key)

        Returns:
            DatabaseWriteResult indicating feature not available
        """
        return DatabaseWriteResult(
            success=False,
            error="UPDATE operation not available in v0.3.0. Use INSERT for now. "
                  "UPDATE will be added in v0.4.0."
        )

    async def _execute_upsert(self, data: dict[str, Any]) -> DatabaseWriteResult:
        """
        Execute UPSERT operation (INSERT ... ON CONFLICT DO UPDATE).

        Note: Not implemented in v0.3.0 (simplified version).
        Will be added in v0.4.0.

        Args:
            data: Data to upsert

        Returns:
            DatabaseWriteResult indicating feature not available
        """
        return DatabaseWriteResult(
            success=False,
            error="UPSERT operation not available in v0.3.0. Use INSERT for now. "
                  "UPSERT will be added in v0.4.0."
        )

    def _get_full_table_name(self) -> str:
        """
        Get fully qualified table name with schema.

        Returns:
            Table name with schema prefix (if configured)
        """
        if self.db_config.schema_name:
            return f"{self.db_config.schema_name}.{self.db_config.table_name}"
        return self.db_config.table_name

    async def transform_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform request data before writing to database.

        By default, no transformation (data should be pre-validated).
        Override in subclass if needed.

        Args:
            data: Request data

        Returns:
            Transformed data (default: unchanged)
        """
        return data

    async def transform_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform database response before returning.

        Args:
            data: Response data

        Returns:
            Transformed response (default: unchanged)
        """
        return data
