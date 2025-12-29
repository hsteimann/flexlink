"""Database connector configuration models."""

from enum import Enum

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class DatabaseOperation(str, Enum):
    """Database operation types."""
    INSERT = "insert"
    UPDATE = "update"
    UPSERT = "upsert"
    DELETE = "delete"


class DatabaseType(str, Enum):
    """Supported database types."""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"  # For testing only


class BatchConfig(BaseModel):
    """Batch processing configuration."""

    enabled: bool = Field(default=True, description="Enable batch processing")

    size: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum batch size (records per batch)"
    )

    timeout_seconds: float = Field(
        default=5.0,
        ge=0.1,
        le=60.0,
        description="Maximum time to wait before flushing partial batch"
    )

    use_copy: bool = Field(
        default=True,
        description="Use PostgreSQL COPY protocol for bulk inserts (PostgreSQL only)"
    )


class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""

    min_size: int = Field(default=2, ge=1, le=100, description="Minimum pool size")
    max_size: int = Field(default=10, ge=1, le=100, description="Maximum pool size")

    max_idle_seconds: float = Field(
        default=300.0,
        ge=1.0,
        description="Maximum time a connection can be idle before closing"
    )

    timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        description="Connection acquisition timeout"
    )

    @field_validator('max_size')
    @classmethod
    def max_must_be_gte_min(cls, v: int, info: ValidationInfo) -> int:
        """Validate max_size >= min_size."""
        min_size = info.data.get('min_size', 2)
        if v < min_size:
            raise ValueError(f"max_size ({v}) must be >= min_size ({min_size})")
        return v


class DatabaseConnectorConfig(BaseModel):
    """Database connector configuration."""

    # Connection settings
    connection_string: str = Field(
        ...,
        description="Database connection string (e.g., postgresql://user:pass@host:port/db)"
    )

    database_type: DatabaseType = Field(
        ...,
        description="Database type (postgresql, mysql, sqlite)"
    )

    # Table configuration
    table_name: str = Field(..., description="Target table name")

    schema_name: str | None = Field(
        default=None,
        description="Schema name (PostgreSQL only, default: public)"
    )

    # Operation configuration
    default_operation: DatabaseOperation = Field(
        default=DatabaseOperation.INSERT,
        description="Default database operation"
    )

    conflict_columns: list[str] = Field(
        default_factory=list,
        description="Columns to check for conflicts in UPSERT (e.g., ['id', 'email'])"
    )

    # Connection pool settings
    pool: ConnectionPoolConfig = Field(
        default_factory=ConnectionPoolConfig,
        description="Connection pool configuration"
    )

    # Batch processing settings
    batch: BatchConfig = Field(
        default_factory=BatchConfig,
        description="Batch processing configuration"
    )

    # Additional settings
    auto_create_table: bool = Field(
        default=False,
        description="Automatically create table if it doesn't exist (use with caution!)"
    )

    ssl_enabled: bool = Field(
        default=True,
        description="Enable SSL/TLS for database connections"
    )


class DatabaseWriteResult(BaseModel):
    """Result of database write operation."""

    success: bool = Field(..., description="Whether operation succeeded")
    rows_affected: int = Field(default=0, description="Number of rows affected")
    rows_failed: int = Field(default=0, description="Number of rows that failed")
    error: str | None = Field(default=None, description="Error message if failed")
    duration_ms: float = Field(default=0.0, description="Operation duration in milliseconds")
