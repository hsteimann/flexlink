#!/usr/bin/env python3
"""Test PostgreSQL connector with real database."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flexlink.connectors.postgresql_connector import PostgreSQLConnector
from flexlink.models.connector import ConnectorConfig, AuthConfig
from flexlink.models.database import DatabaseConnectorConfig, DatabaseType


async def test_postgresql_connector():
    """Test PostgreSQL connector with real database."""

    print("=" * 60)
    print("Testing PostgreSQL Connector with Real Database")
    print("=" * 60)

    # Create connector configuration
    config = ConnectorConfig(
        name="postgres-test",
        type="postgresql",
        base_url="",
        auth=AuthConfig(type="none", credentials={}),
        headers={},
        timeout=30,
        retry_attempts=1,
        enabled=True
    )

    db_config = DatabaseConnectorConfig(
        connection_string="postgresql://flexlink_user:testpass123@localhost:5432/flexlink_test",
        database_type=DatabaseType.POSTGRESQL,
        table_name="orders",
        schema_name="public",
        ssl_enabled=False  # Disable SSL for local testing
    )

    # Create connector
    print("\n1. Creating PostgreSQL connector...")
    connector = PostgreSQLConnector(config, db_config)
    print(f"   ✓ Connector created: {connector}")
    print(f"   ✓ Table: {connector._get_full_table_name()}")
    print(f"   ✓ Pool config: min={db_config.pool.min_size}, max={db_config.pool.max_size}")

    try:
        # Initialize connection pool
        print("\n2. Initializing connection pool...")
        await connector.initialize_pool()
        print("   ✓ Connection pool initialized")

        # Test INSERT operation
        print("\n3. Testing INSERT operation...")
        test_data = {
            "order_id": 12345,
            "amount": 99.99,
            "status": "pending"
        }

        response = await connector.send_request("POST", "", data=test_data)

        if response.status_code == 200:
            print(f"   ✓ INSERT successful!")
            print(f"     - Rows affected: {response.body['rows_affected']}")
            print(f"     - Duration: {response.body['duration_ms']:.2f}ms")
            print(f"     - Operation: {response.body['operation']}")
        else:
            print(f"   ✗ INSERT failed:")
            print(f"     - Status: {response.status_code}")
            print(f"     - Error: {response.error}")

        # Test another INSERT with different data
        print("\n4. Testing second INSERT...")
        test_data2 = {
            "order_id": 12346,
            "amount": 149.50,
            "status": "completed"
        }

        response2 = await connector.send_request("POST", "", data=test_data2)

        if response2.status_code == 200:
            print(f"   ✓ INSERT successful!")
            print(f"     - Rows affected: {response2.body['rows_affected']}")
            print(f"     - Duration: {response2.body['duration_ms']:.2f}ms")
        else:
            print(f"   ✗ INSERT failed: {response2.error}")

        # Test duplicate INSERT (should fail)
        print("\n5. Testing duplicate INSERT (should fail)...")
        response3 = await connector.send_request("POST", "", data=test_data)

        if response3.status_code == 500:
            print(f"   ✓ Duplicate correctly rejected!")
            print(f"     - Error: {response3.error[:80]}...")
        else:
            print(f"   ⚠ Unexpected result: {response3.status_code}")

        # Get statistics
        print("\n6. Connector statistics:")
        stats = connector.get_stats()
        print(f"   - Total writes: {stats['total_writes']}")
        print(f"   - Successful: {stats['successful_writes']}")
        print(f"   - Failed: {stats['failed_writes']}")
        print(f"   - Success rate: {stats['success_rate']:.1%}")

    finally:
        # Close connection pool
        print("\n7. Closing connection pool...")
        await connector.close_pool()
        print("   ✓ Connection pool closed")

    print("\n" + "=" * 60)
    print("PostgreSQL Connector Test Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_postgresql_connector())
