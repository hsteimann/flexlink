"""Tests for database connector models."""

import pytest
from pydantic import ValidationError

from flexlink.models.database import (
    BatchConfig,
    ConnectionPoolConfig,
    DatabaseConnectorConfig,
    DatabaseOperation,
    DatabaseType,
    DatabaseWriteResult
)


def test_database_operation_enum():
    """Test DatabaseOperation enum values."""
    assert DatabaseOperation.INSERT == "insert"
    assert DatabaseOperation.UPDATE == "update"
    assert DatabaseOperation.UPSERT == "upsert"
    assert DatabaseOperation.DELETE == "delete"


def test_database_type_enum():
    """Test DatabaseType enum values."""
    assert DatabaseType.POSTGRESQL == "postgresql"
    assert DatabaseType.MYSQL == "mysql"
    assert DatabaseType.SQLITE == "sqlite"


def test_batch_config_defaults():
    """Test BatchConfig default values."""
    config = BatchConfig()
    assert config.enabled is True
    assert config.size == 1000
    assert config.timeout_seconds == 5.0
    assert config.use_copy is True


def test_batch_config_validation():
    """Test BatchConfig field validation."""
    # Valid config
    config = BatchConfig(size=500, timeout_seconds=10.0)
    assert config.size == 500

    # Invalid batch size (too large)
    with pytest.raises(ValidationError):
        BatchConfig(size=20000)

    # Invalid timeout (negative)
    with pytest.raises(ValidationError):
        BatchConfig(timeout_seconds=-1.0)


def test_connection_pool_config_defaults():
    """Test ConnectionPoolConfig default values."""
    config = ConnectionPoolConfig()
    assert config.min_size == 2
    assert config.max_size == 10
    assert config.timeout_seconds == 30.0
    assert config.max_idle_seconds == 300.0


def test_connection_pool_config_validation():
    """Test ConnectionPoolConfig max >= min validation."""
    # Valid config
    config = ConnectionPoolConfig(min_size=5, max_size=20)
    assert config.min_size == 5
    assert config.max_size == 20

    # Invalid: max < min
    with pytest.raises(ValidationError, match="max_size.*must be >= min_size"):
        ConnectionPoolConfig(min_size=10, max_size=5)


def test_database_connector_config_minimal():
    """Test DatabaseConnectorConfig with minimal required fields."""
    config = DatabaseConnectorConfig(
        connection_string="postgresql://user:pass@localhost:5432/db",
        database_type=DatabaseType.POSTGRESQL,
        table_name="test_table"
    )

    assert config.connection_string == "postgresql://user:pass@localhost:5432/db"
    assert config.database_type == DatabaseType.POSTGRESQL
    assert config.table_name == "test_table"
    assert config.default_operation == DatabaseOperation.INSERT
    assert config.ssl_enabled is True


def test_database_connector_config_with_all_fields():
    """Test DatabaseConnectorConfig with all fields."""
    config = DatabaseConnectorConfig(
        connection_string="postgresql://user:pass@localhost:5432/db",
        database_type=DatabaseType.POSTGRESQL,
        table_name="users",
        schema_name="public",
        default_operation=DatabaseOperation.UPSERT,
        conflict_columns=["id", "email"],
        pool=ConnectionPoolConfig(min_size=5, max_size=20),
        batch=BatchConfig(size=2000, timeout_seconds=10.0),
        auto_create_table=False,
        ssl_enabled=True
    )

    assert config.schema_name == "public"
    assert config.default_operation == DatabaseOperation.UPSERT
    assert config.conflict_columns == ["id", "email"]
    assert config.pool.min_size == 5
    assert config.pool.max_size == 20
    assert config.batch.size == 2000


def test_database_write_result_success():
    """Test DatabaseWriteResult model for successful operation."""
    result = DatabaseWriteResult(
        success=True,
        rows_affected=10,
        duration_ms=45.5
    )
    assert result.success is True
    assert result.rows_affected == 10
    assert result.error is None


def test_database_write_result_failure():
    """Test DatabaseWriteResult model for failed operation."""
    result = DatabaseWriteResult(
        success=False,
        rows_failed=5,
        error="Database connection failed",
        duration_ms=100.0
    )
    assert result.success is False
    assert result.rows_failed == 5
    assert result.error == "Database connection failed"


def test_database_connector_config_from_dict():
    """Test creating DatabaseConnectorConfig from dict (as loaded from YAML)."""
    config_dict = {
        "connection_string": "postgresql://user:pass@localhost:5432/db",
        "database_type": "postgresql",
        "table_name": "test_table",
        "schema_name": "public",
        "default_operation": "insert",
        "conflict_columns": ["id"],
        "pool": {
            "min_size": 2,
            "max_size": 10,
            "timeout_seconds": 30.0,
            "max_idle_seconds": 300.0
        },
        "batch": {
            "enabled": False,
            "size": 1000,
            "timeout_seconds": 5.0,
            "use_copy": False
        },
        "auto_create_table": False,
        "ssl_enabled": True
    }

    config = DatabaseConnectorConfig.model_validate(config_dict)
    assert config.database_type == DatabaseType.POSTGRESQL
    assert config.table_name == "test_table"
    assert config.pool.min_size == 2
    assert config.batch.enabled is False
