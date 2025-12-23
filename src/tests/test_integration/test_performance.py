"""Performance and concurrency tests."""

import asyncio
import time

import httpx
import pytest
import respx

from flexlink.connectors.file_connector import FileConnector
from flexlink.connectors.rest_connector import RestConnector
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.core.transformation import TransformationEngine
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.file import FileFormat
from flexlink.models.request import IntegrationRequest
from flexlink.models.transformation import RouteConfig, TransformationRule


@pytest.fixture
def http_client():
    """Create HTTP client."""
    return httpx.AsyncClient()


@pytest.mark.asyncio
async def test_concurrent_file_processing():
    """Test concurrent file processing operations."""
    config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)

    # Create multiple CSV files
    csv_files = [
        f"id,name,value\n{i},User{i},{i*100}".encode() for i in range(1, 11)
    ]

    # Process all files concurrently
    start_time = time.time()
    tasks = [
        connector.process_file(
            file_content=csv_content, source_format=FileFormat.CSV
        )
        for csv_content in csv_files
    ]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time

    # Verify all processed successfully
    assert all(result.success for result in results)
    assert len(results) == 10

    # Should be faster than sequential processing
    print(f"Concurrent processing of 10 files: {duration:.3f}s")


@pytest.mark.asyncio
async def test_concurrent_transformations():
    """Test concurrent transformation operations."""
    # Create transformation rules
    rules = [
        TransformationRule(
            source_field="name", target_field="user_name", transformation="upper"
        ),
        TransformationRule(
            source_field="email", target_field="user_email", transformation="lower"
        ),
        TransformationRule(
            source_field="age", target_field="user_age", transformation="int"
        ),
    ]

    engine = TransformationEngine(rules)

    # Create multiple data items
    data_items = [
        {"name": f"user{i}", "email": f"USER{i}@TEST.COM", "age": f"{20+i}"}
        for i in range(1, 21)
    ]

    # Transform all concurrently
    start_time = time.time()
    tasks = [engine.apply(data.copy()) for data in data_items]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time

    # Verify all transformed
    assert len(results) == 20
    assert all("user_name" in result for result in results)

    print(f"Concurrent transformations of 20 items: {duration:.3f}s")


@pytest.mark.asyncio
@respx.mock
async def test_concurrent_rest_requests(http_client):
    """Test concurrent REST API requests."""
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)

    # Mock API responses for different endpoints
    for i in range(1, 11):
        respx.get(f"https://api.test.com/api/item/{i}").mock(
            return_value=httpx.Response(200, json={"id": i, "value": i * 100})
        )

    # Make concurrent requests
    start_time = time.time()
    tasks = [connector.send_request("GET", f"/api/item/{i}") for i in range(1, 11)]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time

    # Verify all succeeded
    assert all(result.status_code == 200 for result in results)
    assert len(results) == 10

    print(f"Concurrent REST requests (10 items): {duration:.3f}s")


@pytest.mark.asyncio
@respx.mock
async def test_concurrent_router_requests(http_client):
    """Test concurrent routing operations."""
    registry = ConnectorRegistry()
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["test_api"] = connector

    router = RequestRouter(registry)
    router.add_route(
        RouteConfig(
            path="/items/{id}",
            method="GET",
            connector="test_api",
            target_path="/api/items/{id}",
            transformations=[],
        )
    )

    # Mock responses
    for i in range(1, 21):
        respx.get(f"https://api.test.com/api/items/{i}").mock(
            return_value=httpx.Response(200, json={"id": i})
        )

    # Create concurrent requests
    requests = [
        IntegrationRequest(route=f"/items/{i}", method="GET") for i in range(1, 21)
    ]

    start_time = time.time()
    tasks = [router.route_request(req) for req in requests]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time

    # Verify all routed successfully
    assert all(result.status_code == 200 for result in results)
    assert len(results) == 20

    print(f"Concurrent router requests (20 items): {duration:.3f}s")


@pytest.mark.asyncio
async def test_large_file_processing_performance():
    """Test performance with larger files."""
    config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)

    # Create CSV with 1000 rows
    header = b"id,name,email,status,created_at\n"
    rows = [
        f"{i},User{i},user{i}@test.com,active,2024-01-01\n".encode()
        for i in range(1, 1001)
    ]
    large_csv = header + b"".join(rows)

    # Process file
    start_time = time.time()
    result = await connector.process_file(
        file_content=large_csv, source_format=FileFormat.CSV
    )
    duration = time.time() - start_time

    # Verify processing
    assert result.success is True
    assert result.records_processed == 1000

    print(f"Processing 1000-row CSV: {duration:.3f}s")

    # Performance check: should process quickly
    assert duration < 2.0  # Should take less than 2 seconds


@pytest.mark.asyncio
async def test_multiple_format_conversions_performance():
    """Test performance of multiple format conversions."""
    config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)

    # Create initial CSV
    csv_content = b"id,name,value\n" + b"\n".join(
        [f"{i},Item{i},{i*10}".encode() for i in range(1, 101)]
    )

    # Perform multiple conversions
    start_time = time.time()

    # CSV → JSON
    json_content = await connector.convert_format(
        file_content=csv_content,
        source_format=FileFormat.CSV,
        target_format=FileFormat.JSON,
    )

    # JSON → XML
    xml_content = await connector.convert_format(
        file_content=json_content,
        source_format=FileFormat.JSON,
        target_format=FileFormat.XML,
    )

    # XML → CSV (roundtrip)
    final_csv = await connector.convert_format(
        file_content=xml_content,
        source_format=FileFormat.XML,
        target_format=FileFormat.CSV,
    )

    duration = time.time() - start_time

    # Verify conversions
    assert b"id" in final_csv
    assert b"name" in final_csv

    print(f"Triple format conversion (100 rows): {duration:.3f}s")


@pytest.mark.asyncio
async def test_transformation_performance():
    """Test transformation engine performance."""
    # Create complex transformation rules
    rules = [
        TransformationRule(
            source_field=f"field{i}",
            target_field=f"transformed.field{i}",
            transformation="upper" if i % 2 == 0 else "lower",
        )
        for i in range(1, 21)
    ]

    engine = TransformationEngine(rules)

    # Create data with 20 fields
    data = {f"field{i}": f"Value{i}" for i in range(1, 21)}

    # Perform transformation 100 times
    start_time = time.time()
    tasks = [engine.apply(data.copy()) for _ in range(100)]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time

    # Verify transformations
    assert len(results) == 100
    assert all("transformed" in result for result in results)

    print(f"100 transformations with 20 rules each: {duration:.3f}s")

    # Should be fast
    assert duration < 1.0  # Should take less than 1 second


@pytest.mark.asyncio
async def test_mixed_concurrent_operations(http_client):
    """Test mixed concurrent operations (files + API + transformations)."""
    # Setup
    file_config = ConnectorConfig(
        name="file",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    file_connector = FileConnector(file_config)

    rest_config = ConnectorConfig(
        name="api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    rest_connector = RestConnector(rest_config, http_client)

    transform_rules = [
        TransformationRule(
            source_field="name", target_field="user_name", transformation="upper"
        )
    ]
    transform_engine = TransformationEngine(transform_rules)

    # Mock API
    with respx.mock:
        for i in range(1, 6):
            respx.get(f"https://api.test.com/api/data/{i}").mock(
                return_value=httpx.Response(200, json={"id": i})
            )

        # Create mixed tasks
        start_time = time.time()
        tasks = []

        # File processing tasks
        for i in range(5):
            csv = f"id,name\n{i},User{i}".encode()
            tasks.append(
                file_connector.process_file(
                    file_content=csv, source_format=FileFormat.CSV
                )
            )

        # API request tasks
        for i in range(1, 6):
            tasks.append(rest_connector.send_request("GET", f"/api/data/{i}"))

        # Transformation tasks
        for i in range(5):
            data = {"name": f"user{i}"}
            tasks.append(transform_engine.apply(data))

        # Execute all concurrently
        results = await asyncio.gather(*tasks)
        duration = time.time() - start_time

        # Verify all completed
        assert len(results) == 15  # 5 files + 5 API + 5 transforms

        print(f"Mixed concurrent operations (15 total): {duration:.3f}s")


@pytest.mark.asyncio
async def test_registry_concurrent_access():
    """Test concurrent access to connector registry."""
    registry = ConnectorRegistry()

    # Add connector
    config = ConnectorConfig(
        name="shared_connector",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    connector = FileConnector(config)
    registry._connectors["shared_connector"] = connector

    # Access registry concurrently from multiple tasks
    async def get_connector(name: str):
        return registry.get_connector(name)

    start_time = time.time()
    tasks = [get_connector("shared_connector") for _ in range(100)]
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time

    # Verify all got the same connector
    assert all(result is connector for result in results)

    print(f"100 concurrent registry accesses: {duration:.3f}s")

    # Should be very fast (no locking issues)
    assert duration < 0.1
