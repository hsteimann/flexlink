#!/usr/bin/env python3
"""Test File-to-Database pipeline."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from flexlink.connectors.postgresql_connector import PostgreSQLConnector
from flexlink.models.connector import ConnectorConfig, AuthConfig
from flexlink.models.database import DatabaseConnectorConfig, DatabaseType
from flexlink.parsers.csv_parser import CSVParser


async def test_file_to_database_pipeline():
    """Test parsing CSV file and writing to PostgreSQL."""

    print("=" * 70)
    print("Testing File-to-Database Pipeline")
    print("=" * 70)

    # 1. Parse CSV file
    print("\n1. Parsing CSV file (test_orders.csv)...")
    parser = CSVParser()

    with open("test_orders.csv", "rb") as f:
        csv_content = f.read()

    records_df = await parser.parse(csv_content)
    records = records_df.to_dict('records')  # Convert DataFrame to list of dicts
    print(f"   ✓ Parsed {len(records)} records from CSV")

    # Show first record
    if len(records) > 0:
        print(f"   ✓ Sample record: {records[0]}")

    # 2. Setup PostgreSQL connector
    print("\n2. Setting up PostgreSQL connector...")

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
        ssl_enabled=False
    )

    connector = PostgreSQLConnector(config, db_config)
    await connector.initialize_pool()
    print("   ✓ PostgreSQL connector ready")

    # 3. Write each record to database
    print("\n3. Writing records to PostgreSQL...")

    successful = 0
    failed = 0
    total_duration = 0.0

    for idx, record in enumerate(records, 1):
        # Transform CSV record to match database schema
        db_record = {
            "order_id": int(record["order_id"]),
            "amount": float(record["amount"]),
            "status": record["status"]
        }

        # Write to database
        response = await connector.send_request("POST", "", data=db_record)

        if response.status_code == 200:
            successful += 1
            duration = response.body.get("duration_ms", 0)
            total_duration += duration
            print(f"   ✓ Record {idx}/{len(records)}: order_id={db_record['order_id']}, "
                  f"amount=${db_record['amount']:.2f}, status={db_record['status']} "
                  f"({duration:.2f}ms)")
        else:
            failed += 1
            print(f"   ✗ Record {idx}/{len(records)}: FAILED - {response.error}")

    # 4. Show statistics
    print("\n4. Pipeline Statistics:")
    print(f"   - Records parsed: {len(records)}")
    print(f"   - Successful writes: {successful}")
    print(f"   - Failed writes: {failed}")
    print(f"   - Success rate: {(successful/len(records)*100):.1f}%")
    print(f"   - Average write time: {(total_duration/successful if successful > 0 else 0):.2f}ms")
    print(f"   - Total processing time: {total_duration:.2f}ms")

    # 5. Get connector stats
    print("\n5. Connector Statistics:")
    stats = connector.get_stats()
    print(f"   - Total writes: {stats['total_writes']}")
    print(f"   - Successful: {stats['successful_writes']}")
    print(f"   - Failed: {stats['failed_writes']}")
    print(f"   - Success rate: {stats['success_rate']:.1%}")

    # Cleanup
    await connector.close_pool()
    print("\n✓ Connection pool closed")

    print("\n" + "=" * 70)
    print("File-to-Database Pipeline Test Complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_file_to_database_pipeline())
