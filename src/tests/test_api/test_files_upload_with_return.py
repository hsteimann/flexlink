"""
Tests for file upload with return_file parameter.

Verifies:
- Upload returns metadata by default (backward compatible)
- Upload with return_file=True returns file content
- File content is correctly processed and returned
"""

import io
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from flexlink.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_upload_returns_metadata_by_default(client):
    """Test that upload returns metadata by default (backward compatible)."""
    # Create CSV content
    csv_content = "name,age\nAlice,30\nBob,25"

    # Upload file
    response = client.post(
        "/api/v1/files/upload?source_format=csv",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # Should return JSON metadata (FileProcessingResult)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    result = response.json()
    assert result["success"] is True
    assert result["records_processed"] == 2
    assert result["output_format"] == "csv"
    assert "output_filename" in result


def test_upload_with_return_file_returns_content(client):
    """Test that upload with return_file=True returns file content."""
    # Create CSV content
    csv_content = "name,age\nAlice,30\nBob,25"

    # Upload file with return_file=True
    response = client.post(
        "/api/v1/files/upload?source_format=csv&return_file=true",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # Should return file content
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "attachment" in response.headers["content-disposition"]
    assert "processed.csv" in response.headers["content-disposition"]

    # Verify content is CSV
    content = response.content.decode()
    assert "name,age" in content or "name" in content
    assert "Alice" in content
    assert "Bob" in content


def test_upload_with_conversion_and_return_file(client):
    """Test upload with format conversion and return_file=True."""
    # Create CSV content
    csv_content = "name,age\nAlice,30\nBob,25"

    # Upload CSV and convert to JSON
    response = client.post(
        "/api/v1/files/upload?source_format=csv&target_format=json&return_file=true",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # Should return JSON file content
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert "processed.json" in response.headers["content-disposition"]

    # Verify content is valid JSON
    content = response.content
    data = json.loads(content)
    assert len(data) == 2
    assert data[0]["name"] == "Alice"
    assert data[0]["age"] == 30


def test_upload_csv_to_xml_with_return_file(client):
    """Test upload CSV to XML conversion with return_file."""
    # Create CSV content
    csv_content = "product,price\nLaptop,999\nMouse,25"

    # Upload and convert to XML
    response = client.post(
        "/api/v1/files/upload?source_format=csv&target_format=xml&return_file=true",
        files={"file": ("products.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # Should return XML file
    assert response.status_code == 200
    assert "processed.xml" in response.headers["content-disposition"]

    # Verify content is XML
    content = response.content.decode()
    assert "<root>" in content or "<?xml" in content
    assert "Laptop" in content
    assert "999" in content


def test_upload_json_with_return_file(client):
    """Test uploading JSON with return_file."""
    # Create JSON content
    json_content = json.dumps([
        {"user": "Alice", "score": 95},
        {"user": "Bob", "score": 88}
    ])

    # Upload JSON
    response = client.post(
        "/api/v1/files/upload?source_format=json&return_file=true",
        files={"file": ("data.json", io.BytesIO(json_content.encode()), "application/json")},
    )

    # Should return JSON file
    assert response.status_code == 200
    assert "processed.json" in response.headers["content-disposition"]

    # Verify content
    content = response.content
    data = json.loads(content)
    assert len(data) == 2
    assert data[0]["user"] == "Alice"


def test_upload_xml_to_csv_with_return_file(client):
    """Test upload XML to CSV conversion with return_file."""
    # Create XML content
    xml_content = """<?xml version="1.0"?>
    <root>
        <record><name>Alice</name><city>NYC</city></record>
        <record><name>Bob</name><city>LA</city></record>
    </root>
    """

    # Upload and convert to CSV
    response = client.post(
        "/api/v1/files/upload?source_format=xml&target_format=csv&return_file=true",
        files={"file": ("data.xml", io.BytesIO(xml_content.encode()), "application/xml")},
    )

    # Should return CSV file
    assert response.status_code == 200
    assert "processed.csv" in response.headers["content-disposition"]

    # Verify content is CSV
    content = response.content.decode()
    assert "name" in content or "Alice" in content
    assert "city" in content or "NYC" in content


def test_upload_metadata_and_file_consistent(client):
    """Test that metadata-only and return_file produce consistent results."""
    # Create CSV content
    csv_content = "item,quantity\nApple,10\nBanana,20"

    # Upload without return_file (metadata only)
    response1 = client.post(
        "/api/v1/files/upload?source_format=csv",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )
    metadata = response1.json()

    # Upload with return_file (file content)
    response2 = client.post(
        "/api/v1/files/upload?source_format=csv&return_file=true",
        files={"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # Metadata should match (same number of records processed)
    # We can't directly compare since response2 returns file content,
    # but we can verify the file is valid and has the same data
    content = response2.content.decode()

    # Count lines (header + 2 data rows)
    lines = [line for line in content.strip().split('\n') if line]
    # Should have at least 2 records worth of data
    assert len(lines) >= 2
    assert metadata["records_processed"] == 2


def test_upload_empty_file_error_handling(client):
    """Test error handling with empty file."""
    # Create empty file
    csv_content = ""

    # Upload empty file with return_file
    response = client.post(
        "/api/v1/files/upload?source_format=csv&return_file=true",
        files={"file": ("empty.csv", io.BytesIO(csv_content.encode()), "text/csv")},
    )

    # Should return error response as JSON (not file)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    # Should have error about empty file
    result = response.json()
    assert result["success"] is False
    assert any("empty" in error.lower() for error in result["errors"])
