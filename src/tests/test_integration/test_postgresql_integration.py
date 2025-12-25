"""Integration tests for PostgreSQL connector (with mocks)."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from flexlink.connectors.postgresql_connector import PostgreSQLConnector
from flexlink.models.connector import ConnectorConfig, AuthConfig
from flexlink.models.database import (
    DatabaseConnectorConfig,
    DatabaseType,
    DatabaseOperation
)


@pytest.fixture
def postgres_config():
    """Create test PostgreSQL configuration."""
    config = ConnectorConfig(
        name="test-postgres",
        type="postgresql",
        base_url="",
        auth=AuthConfig(type="none", credentials={}),
        headers={},
        timeout=30,
        retry_attempts=1,
        enabled=True
    )

    db_config = DatabaseConnectorConfig(
        connection_string="postgresql://test:test@localhost:5432/testdb",
        database_type=DatabaseType.POSTGRESQL,
        table_name="test_table",
        schema_name="public"
    )

    return config, db_config


@pytest.fixture
def postgres_connector(postgres_config):
    """Create PostgreSQLConnector instance."""
    config, db_config = postgres_config
    return PostgreSQLConnector(config, db_config)


@pytest.mark.asyncio
async def test_get_full_table_name_with_schema(postgres_connector):
    """Test table name formatting with schema."""
    table_name = postgres_connector._get_full_table_name()
    assert table_name == "public.test_table"


@pytest.mark.asyncio
async def test_get_full_table_name_without_schema(postgres_config):
    """Test table name formatting without schema."""
    config, db_config = postgres_config
    db_config.schema_name = None

    connector = PostgreSQLConnector(config, db_config)
    table_name = connector._get_full_table_name()
    assert table_name == "test_table"


@pytest.mark.asyncio
@patch('flexlink.connectors.postgresql_connector.AsyncConnectionPool')
async def test_initialize_pool(mock_pool_class, postgres_connector):
    """Test connection pool initialization."""
    mock_pool = AsyncMock()
    mock_pool_class.return_value = mock_pool

    await postgres_connector.initialize_pool()

    # Verify pool was created with correct parameters
    mock_pool_class.assert_called_once()
    call_kwargs = mock_pool_class.call_args[1]
    assert "postgresql://test:test@localhost:5432/testdb" in call_kwargs["conninfo"]
    assert call_kwargs["min_size"] == 2
    assert call_kwargs["max_size"] == 10


@pytest.mark.asyncio
async def test_execute_insert_without_pool(postgres_connector):
    """Test INSERT fails gracefully when pool not initialized."""
    result = await postgres_connector._execute_insert({"id": 1, "name": "Test"})

    assert result.success is False
    assert "pool not initialized" in result.error.lower()


@pytest.mark.asyncio
@patch('flexlink.connectors.postgresql_connector.AsyncConnectionPool')
async def test_execute_insert_success(mock_pool_class, postgres_connector):
    """Test successful INSERT operation."""
    # Setup mock cursor
    mock_cursor = AsyncMock()
    mock_cursor.rowcount = 1
    mock_cursor.execute = AsyncMock()

    # Setup cursor context manager
    mock_cursor_context = MagicMock()
    mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_context.__aexit__ = AsyncMock(return_value=None)

    # Setup mock connection
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_context

    # Setup connection context manager
    mock_conn_context = MagicMock()
    mock_conn_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn_context.__aexit__ = AsyncMock(return_value=None)

    # Setup mock pool - connection() should return the context manager directly
    mock_pool = MagicMock()
    mock_pool.connection.return_value = mock_conn_context
    mock_pool_class.return_value = mock_pool

    # Initialize pool
    await postgres_connector.initialize_pool()

    # Execute INSERT
    data = {"id": 1, "name": "Test User", "email": "test@example.com"}
    result = await postgres_connector._execute_insert(data)

    # Verify result
    assert result.success is True
    assert result.rows_affected == 1
    assert result.duration_ms > 0

    # Verify query was executed
    mock_cursor.execute.assert_called_once()
    call_args = mock_cursor.execute.call_args[0]
    query = call_args[0]
    assert "INSERT INTO public.test_table" in query
    # Column order may vary
    assert ("id" in query and "name" in query and "email" in query)


@pytest.mark.asyncio
async def test_send_request_no_data(postgres_connector):
    """Test send_request with no data returns error."""
    response = await postgres_connector.send_request("POST", "/test", data=None)

    assert response.status_code == 400
    assert "No data provided" in response.error


@pytest.mark.asyncio
@patch('flexlink.connectors.postgresql_connector.AsyncConnectionPool')
async def test_send_request_insert_success(mock_pool_class, postgres_connector):
    """Test send_request with INSERT operation."""
    # Setup mock cursor
    mock_cursor = AsyncMock()
    mock_cursor.rowcount = 1
    mock_cursor.execute = AsyncMock()

    # Setup cursor context manager
    mock_cursor_context = MagicMock()
    mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_context.__aexit__ = AsyncMock(return_value=None)

    # Setup mock connection
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_context

    # Setup connection context manager
    mock_conn_context = MagicMock()
    mock_conn_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn_context.__aexit__ = AsyncMock(return_value=None)

    # Setup mock pool
    mock_pool = MagicMock()
    mock_pool.connection.return_value = mock_conn_context
    mock_pool_class.return_value = mock_pool

    await postgres_connector.initialize_pool()

    # Send request (POST → INSERT)
    data = {"id": 1, "name": "Test"}
    response = await postgres_connector.send_request("POST", "/test", data=data)

    # Verify response
    assert response.status_code == 200
    assert response.body["success"] is True
    assert response.body["rows_affected"] == 1
    assert response.body["operation"] == "insert"


@pytest.mark.asyncio
async def test_update_operation_not_supported(postgres_connector):
    """Test that UPDATE operation returns not supported error."""
    result = await postgres_connector._execute_update({"id": 1, "name": "Updated"})

    assert result.success is False
    assert "UPDATE operation not available" in result.error
    assert "v0.3.0" in result.error


@pytest.mark.asyncio
async def test_upsert_operation_not_supported(postgres_connector):
    """Test that UPSERT operation returns not supported error."""
    result = await postgres_connector._execute_upsert({"id": 1, "name": "Upserted"})

    assert result.success is False
    assert "UPSERT operation not available" in result.error
    assert "v0.3.0" in result.error


@pytest.mark.asyncio
async def test_get_stats_tracking(postgres_connector):
    """Test statistics tracking."""
    # Initial stats
    stats = postgres_connector.get_stats()
    assert stats["total_writes"] == 0
    assert stats["successful_writes"] == 0
    assert stats["failed_writes"] == 0

    # Simulate writes by incrementing counters
    postgres_connector.total_writes = 10
    postgres_connector.successful_writes = 8
    postgres_connector.failed_writes = 2

    stats = postgres_connector.get_stats()
    assert stats["total_writes"] == 10
    assert stats["successful_writes"] == 8
    assert stats["failed_writes"] == 2
    assert stats["success_rate"] == 0.8


@pytest.mark.asyncio
@patch('flexlink.connectors.postgresql_connector.AsyncConnectionPool')
async def test_close_pool(mock_pool_class, postgres_connector):
    """Test connection pool closing."""
    mock_pool = AsyncMock()
    mock_pool_class.return_value = mock_pool

    # Initialize and close pool
    await postgres_connector.initialize_pool()
    await postgres_connector.close_pool()

    # Verify close was called
    mock_pool.close.assert_called_once()


@pytest.mark.asyncio
@patch('flexlink.connectors.postgresql_connector.AsyncConnectionPool')
async def test_method_to_operation_mapping(mock_pool_class, postgres_connector):
    """Test HTTP method to database operation mapping."""
    # Setup mock cursor
    mock_cursor = AsyncMock()
    mock_cursor.rowcount = 1
    mock_cursor.execute = AsyncMock()

    # Setup cursor context manager
    mock_cursor_context = MagicMock()
    mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_context.__aexit__ = AsyncMock(return_value=None)

    # Setup mock connection
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor_context

    # Setup connection context manager
    mock_conn_context = MagicMock()
    mock_conn_context.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn_context.__aexit__ = AsyncMock(return_value=None)

    # Setup mock pool
    mock_pool = MagicMock()
    mock_pool.connection.return_value = mock_conn_context
    mock_pool_class.return_value = mock_pool

    await postgres_connector.initialize_pool()

    # Test POST → INSERT
    data = {"id": 1}
    response = await postgres_connector.send_request("POST", "", data=data)
    assert response.body["operation"] == "insert"


@pytest.mark.asyncio
@patch('flexlink.connectors.postgresql_connector.AsyncConnectionPool')
async def test_ssl_enabled_adds_sslmode(mock_pool_class, postgres_connector):
    """Test that SSL is automatically added to connection string."""
    mock_pool = AsyncMock()
    mock_pool_class.return_value = mock_pool

    await postgres_connector.initialize_pool()

    # Verify sslmode was added to connection string
    call_kwargs = mock_pool_class.call_args[1]
    assert "sslmode=require" in call_kwargs["conninfo"]
