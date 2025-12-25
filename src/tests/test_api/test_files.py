"""Tests for file API routes."""

import io

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from flexlink.api.files import router
from flexlink.core.registry import ConnectorRegistry
from flexlink.core.router import RequestRouter
from flexlink.connectors.rest_connector import RestConnector
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.transformation import RouteConfig


@pytest.fixture
def client():
    """Create test client for file routes."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_list_formats(client):
    """Test listing supported file formats."""
    response = client.get("/api/v1/files/formats")

    assert response.status_code == 200
    data = response.json()
    assert "formats" in data
    assert "csv" in data["formats"]
    assert "json" in data["formats"]
    assert "xml" in data["formats"]


def test_file_service_health(client):
    """Test file service health check."""
    response = client.get("/api/v1/files/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "file_processing"


def test_upload_csv_file(client):
    """Test uploading CSV file."""
    csv_content = b"id,name,email\n1,John,john@test.com\n2,Jane,jane@test.com"

    response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv"},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["records_processed"] == 2
    assert data["output_format"] == "csv"


def test_upload_json_file(client):
    """Test uploading JSON file."""
    json_content = b'[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]'

    response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "json"},
        files={"file": ("test.json", io.BytesIO(json_content), "application/json")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["records_processed"] == 2
    assert data["output_format"] == "json"


def test_upload_xml_file(client):
    """Test uploading XML file."""
    xml_content = b"""<?xml version="1.0"?>
    <data>
        <row><id>1</id><name>John</name></row>
        <row><id>2</id><name>Jane</name></row>
    </data>"""

    response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "xml"},
        files={"file": ("test.xml", io.BytesIO(xml_content), "application/xml")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["records_processed"] == 2
    assert data["output_format"] == "xml"


def test_upload_and_convert_csv_to_json(client):
    """Test uploading CSV and converting to JSON."""
    csv_content = b"id,name\n1,John\n2,Jane"

    response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv", "target_format": "json"},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["records_processed"] == 2
    assert data["output_format"] == "json"  # Converted to JSON


def test_upload_file_too_large(client):
    """Test uploading file exceeding size limit."""
    # Create content larger than 10MB
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB

    response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv"},
        files={"file": ("large.csv", io.BytesIO(large_content), "text/csv")},
    )

    assert response.status_code == 400
    assert "File size" in response.json()["detail"]


def test_upload_invalid_csv(client):
    """Test uploading invalid CSV file."""
    invalid_content = b""  # Empty file

    response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv"},
        files={"file": ("test.csv", io.BytesIO(invalid_content), "text/csv")},
    )

    # Empty file returns success=False in result
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert len(data["errors"]) > 0


def test_convert_csv_to_json(client):
    """Test converting CSV to JSON."""
    csv_content = b"id,name,email\n1,John,john@test.com\n2,Jane,jane@test.com"

    response = client.post(
        "/api/v1/files/convert",
        params={"source_format": "csv", "target_format": "json"},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=test.json"

    # Verify content is valid JSON
    content = response.content
    assert b'"id"' in content
    assert b'"name"' in content
    assert b"John" in content


def test_convert_json_to_xml(client):
    """Test converting JSON to XML."""
    json_content = b'[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]'

    response = client.post(
        "/api/v1/files/convert",
        params={"source_format": "json", "target_format": "xml"},
        files={"file": ("test.json", io.BytesIO(json_content), "application/json")},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=test.xml"

    # Verify content is valid XML
    content = response.content
    assert b"<id>" in content
    assert b"<name>" in content


def test_convert_xml_to_csv(client):
    """Test converting XML to CSV."""
    xml_content = b"""<?xml version="1.0"?>
    <data>
        <row><id>1</id><name>John</name></row>
        <row><id>2</id><name>Jane</name></row>
    </data>"""

    response = client.post(
        "/api/v1/files/convert",
        params={"source_format": "xml", "target_format": "csv"},
        files={"file": ("test.xml", io.BytesIO(xml_content), "application/xml")},
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == "attachment; filename=test.csv"

    # Verify content is valid CSV
    content = response.content
    assert b"id,name" in content
    assert b"John" in content


def test_convert_same_format_no_conversion(client):
    """Test converting file to same format (no-op)."""
    csv_content = b"id,name\n1,John"

    response = client.post(
        "/api/v1/files/convert",
        params={"source_format": "csv", "target_format": "csv"},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    # Should return original content
    assert response.content == csv_content


def test_convert_invalid_file(client):
    """Test converting invalid file."""
    invalid_content = b"not valid json"

    response = client.post(
        "/api/v1/files/convert",
        params={"source_format": "json", "target_format": "csv"},
        files={"file": ("test.json", io.BytesIO(invalid_content), "application/json")},
    )

    assert response.status_code == 400


def test_convert_file_too_large(client):
    """Test converting file exceeding size limit."""
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB

    response = client.post(
        "/api/v1/files/convert",
        params={"source_format": "csv", "target_format": "json"},
        files={"file": ("large.csv", io.BytesIO(large_content), "text/csv")},
    )

    assert response.status_code == 400


def test_upload_with_save_creates_download_url(client):
    """Test that upload with save_file=True creates download_url."""
    csv_content = b"id,name\n1,John\n2,Jane"

    response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv", "save_file": True},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["download_url"] is not None
    assert "/api/v1/files/download/" in data["download_url"]


def test_upload_without_save_no_download_url(client):
    """Test that upload with save_file=False doesn't create download_url."""
    csv_content = b"id,name\n1,John\n2,Jane"

    response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv", "save_file": False},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["download_url"] is None


def test_download_saved_file(client):
    """Test downloading a saved file."""
    # First upload a file
    csv_content = b"id,name,email\n1,John,john@test.com\n2,Jane,jane@test.com"

    upload_response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv", "save_file": True},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    download_url = upload_data["download_url"]
    assert download_url is not None

    # Now download the file
    download_response = client.get(download_url)

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "text/csv; charset=utf-8"
    assert b"id,name,email" in download_response.content
    assert b"John" in download_response.content


def test_download_with_format_conversion(client):
    """Test downloading file after format conversion."""
    # Upload CSV and convert to JSON
    csv_content = b"id,name\n1,John\n2,Jane"

    upload_response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv", "target_format": "json", "save_file": True},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert upload_response.status_code == 200
    upload_data = upload_response.json()
    assert upload_data["output_format"] == "json"
    download_url = upload_data["download_url"]

    # Download and verify JSON
    download_response = client.get(download_url)

    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "application/json"
    assert b'"id"' in download_response.content
    assert b'"name"' in download_response.content


def test_download_nonexistent_file(client):
    """Test downloading a file that doesn't exist."""
    # Use a valid UUID that doesn't exist
    fake_uuid = "00000000-0000-0000-0000-000000000000"

    response = client.get(f"/api/v1/files/download/{fake_uuid}")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_download_invalid_file_id(client):
    """Test downloading with invalid file ID format."""
    response = client.get("/api/v1/files/download/invalid-not-a-uuid")

    assert response.status_code == 400
    assert "Invalid file ID format" in response.json()["detail"]


def test_cleanup_expired_files(client):
    """Test cleanup endpoint removes old files."""
    import time
    from pathlib import Path

    # Upload a file
    csv_content = b"id,name\n1,Test"

    upload_response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv", "save_file": True},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    upload_data = upload_response.json()
    download_url = upload_data["download_url"]
    file_id = download_url.split("/")[-1]

    # Verify file exists
    downloads_dir = Path("data/downloads")
    saved_file = downloads_dir / f"{file_id}.csv"
    assert saved_file.exists()

    # Modify file timestamp to make it appear old
    old_time = time.time() - (25 * 60 * 60)  # 25 hours ago
    import os
    os.utime(saved_file, (old_time, old_time))

    # Run cleanup
    cleanup_response = client.delete("/api/v1/files/cleanup")

    assert cleanup_response.status_code == 200
    data = cleanup_response.json()
    assert data["deleted_files"] >= 1

    # Verify file was deleted
    assert not saved_file.exists()


def test_cleanup_preserves_recent_files(client):
    """Test cleanup doesn't remove recent files."""
    from pathlib import Path

    # Upload a file
    csv_content = b"id,name\n1,Test"

    upload_response = client.post(
        "/api/v1/files/upload",
        params={"source_format": "csv", "save_file": True},
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    upload_data = upload_response.json()
    download_url = upload_data["download_url"]
    file_id = download_url.split("/")[-1]

    # Run cleanup immediately (file is fresh)
    cleanup_response = client.delete("/api/v1/files/cleanup")

    assert cleanup_response.status_code == 200

    # Verify file still exists
    downloads_dir = Path("data/downloads")
    saved_file = downloads_dir / f"{file_id}.csv"
    assert saved_file.exists()

    # Clean up after test
    saved_file.unlink()


@pytest.mark.asyncio
@respx.mock
async def test_forward_file_individual_mode():
    """Test forwarding file records in individual mode."""
    from fastapi import FastAPI
    from flexlink.api import dependencies

    # Setup registry and router
    registry = ConnectorRegistry()
    http_client = httpx.AsyncClient()

    # Create REST connector
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["test_api"] = connector

    # Create router with route
    request_router = RequestRouter(registry)
    request_router.add_route(
        RouteConfig(
            path="/users",
            method="POST",
            connector="test_api",
            target_path="/api/users",
            transformations=[],
        )
    )

    # Mock API responses
    respx.post("https://api.test.com/api/users").mock(
        return_value=httpx.Response(201, json={"id": 1, "status": "created"})
    )

    # Setup dependencies
    dependencies.set_registry(registry)
    dependencies.set_router(request_router)

    # Create test app with router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Create CSV file
    csv_content = b"name,email\nJohn,john@test.com\nJane,jane@test.com"

    # Forward file
    response = client.post(
        "/api/v1/files/forward",
        params={
            "source_format": "csv",
            "target_route": "/users",
            "target_method": "POST",
            "batch_mode": "individual",
        },
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["records_parsed"] == 2
    assert data["records_forwarded"] == 2
    assert data["records_failed"] == 0
    assert data["batch_mode"] == "individual"
    assert data["target_route"] == "/users"
    assert len(data["responses"]) == 1
    assert data["responses"][0]["status_code"] == 201
    assert data["responses"][0]["count"] == 2


@pytest.mark.asyncio
@respx.mock
async def test_forward_file_batch_mode():
    """Test forwarding file records in batch mode."""
    from fastapi import FastAPI
    from flexlink.api import dependencies

    # Setup registry and router
    registry = ConnectorRegistry()
    http_client = httpx.AsyncClient()

    # Create REST connector
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["test_api"] = connector

    # Create router with route
    request_router = RequestRouter(registry)
    request_router.add_route(
        RouteConfig(
            path="/batch",
            method="POST",
            connector="test_api",
            target_path="/api/batch",
            transformations=[],
        )
    )

    # Mock API response for batch endpoint
    respx.post("https://api.test.com/api/batch").mock(
        return_value=httpx.Response(200, json={"processed": 3})
    )

    # Setup dependencies
    dependencies.set_registry(registry)
    dependencies.set_router(request_router)

    # Create test app with router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Create JSON file
    json_content = b'[{"id": 1, "name": "A"}, {"id": 2, "name": "B"}, {"id": 3, "name": "C"}]'

    # Forward file in batch mode
    response = client.post(
        "/api/v1/files/forward",
        params={
            "source_format": "json",
            "target_route": "/batch",
            "target_method": "POST",
            "batch_mode": "batch",
        },
        files={"file": ("test.json", io.BytesIO(json_content), "application/json")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["records_parsed"] == 3
    assert data["records_forwarded"] == 3
    assert data["records_failed"] == 0
    assert data["batch_mode"] == "batch"
    assert len(data["responses"]) == 1
    assert data["responses"][0]["status_code"] == 200


@pytest.mark.asyncio
@respx.mock
async def test_forward_file_with_failures():
    """Test forwarding file with some failures."""
    from fastapi import FastAPI
    from flexlink.api import dependencies

    # Setup registry and router
    registry = ConnectorRegistry()
    http_client = httpx.AsyncClient()

    # Create REST connector
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["test_api"] = connector

    # Create router with route
    request_router = RequestRouter(registry)
    request_router.add_route(
        RouteConfig(
            path="/users",
            method="POST",
            connector="test_api",
            target_path="/api/users",
            transformations=[],
        )
    )

    # Mock API responses - first succeeds, second fails
    call_count = 0
    def dynamic_response(request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(201, json={"id": 1})
        else:
            return httpx.Response(400, json={"error": "Invalid data"})

    respx.post("https://api.test.com/api/users").mock(side_effect=dynamic_response)

    # Setup dependencies
    dependencies.set_registry(registry)
    dependencies.set_router(request_router)

    # Create test app with router
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Create CSV file
    csv_content = b"name,email\nJohn,john@test.com\nJane,invalid"

    # Forward file
    response = client.post(
        "/api/v1/files/forward",
        params={
            "source_format": "csv",
            "target_route": "/users",
            "target_method": "POST",
            "batch_mode": "individual",
        },
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["records_parsed"] == 2
    assert data["records_forwarded"] == 1
    assert data["records_failed"] == 1
    assert len(data["errors"]) > 0
    assert "400" in data["errors"][0]


@pytest.mark.asyncio
async def test_forward_empty_file():
    """Test forwarding empty file returns error."""
    from fastapi import FastAPI
    from flexlink.api import dependencies

    # Setup minimal dependencies
    registry = ConnectorRegistry()
    request_router = RequestRouter(registry)
    dependencies.set_registry(registry)
    dependencies.set_router(request_router)

    # Create test app
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Create empty CSV
    csv_content = b""

    # Forward file
    response = client.post(
        "/api/v1/files/forward",
        params={
            "source_format": "csv",
            "target_route": "/users",
            "target_method": "POST",
        },
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 400
    assert "parsing failed" in response.json()["detail"].lower()


@pytest.mark.asyncio
@respx.mock
async def test_forward_file_with_transformations():
    """Test that file forwarding uses route-level transformations."""
    from fastapi import FastAPI
    from flexlink.api import dependencies
    from flexlink.models.transformation import TransformationRule

    # Setup registry and router
    registry = ConnectorRegistry()
    http_client = httpx.AsyncClient()

    # Create REST connector
    config = ConnectorConfig(
        name="test_api",
        type="rest",
        base_url="https://api.test.com",
        auth=AuthConfig(type="none"),
    )
    connector = RestConnector(config, http_client)
    registry._connectors["test_api"] = connector

    # Create router with route that has transformations
    request_router = RequestRouter(registry)
    request_router.add_route(
        RouteConfig(
            path="/users",
            method="POST",
            connector="test_api",
            target_path="/api/users",
            transformations=[
                TransformationRule(
                    source_field="name",
                    target_field="full_name",
                    transformation="upper",
                )
            ],
        )
    )

    # Mock API - capture the request to verify transformations applied
    captured_requests = []
    def capture_request(request):
        captured_requests.append(request)
        return httpx.Response(201, json={"id": 1})

    respx.post("https://api.test.com/api/users").mock(side_effect=capture_request)

    # Setup dependencies
    dependencies.set_registry(registry)
    dependencies.set_router(request_router)

    # Create test app
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # Create CSV file
    csv_content = b"name,email\njohn,john@test.com"

    # Forward file
    response = client.post(
        "/api/v1/files/forward",
        params={
            "source_format": "csv",
            "target_route": "/users",
            "target_method": "POST",
            "batch_mode": "individual",
        },
        files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["records_forwarded"] == 1

    # Verify transformation was applied
    assert len(captured_requests) == 1
    request_body = captured_requests[0].content
    assert b"JOHN" in request_body  # Name should be uppercased
    assert b"full_name" in request_body  # Field should be renamed
