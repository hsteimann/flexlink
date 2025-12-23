"""Tests for file API routes."""

import io

import pytest
from fastapi.testclient import TestClient

from flexlink.api.files import router


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
