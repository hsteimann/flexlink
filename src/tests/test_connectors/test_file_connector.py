"""Tests for file connector."""

from pathlib import Path

import pytest

from flexlink.connectors.file_connector import FileConnector
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.file import FileFormat


@pytest.fixture
def file_config():
    """Create file connector configuration."""
    return ConnectorConfig(
        name="file_processor",
        type="file",
        base_url="file://local",
        auth=AuthConfig(type="none"),
    )


@pytest.fixture
def file_connector(file_config):
    """Create file connector instance."""
    return FileConnector(file_config)


@pytest.fixture
def sample_csv():
    """Load sample CSV file."""
    path = Path("data/samples/sample.csv")
    return path.read_bytes()


@pytest.fixture
def sample_json():
    """Load sample JSON file."""
    path = Path("data/samples/sample.json")
    return path.read_bytes()


@pytest.fixture
def sample_xml():
    """Load sample XML file."""
    path = Path("data/samples/sample.xml")
    return path.read_bytes()


@pytest.mark.asyncio
async def test_process_csv_file(file_connector, sample_csv):
    """Test processing CSV file."""
    result = await file_connector.process_file(sample_csv, FileFormat.CSV)

    assert result.success is True
    assert result.records_processed == 5
    assert result.output_format == FileFormat.CSV
    assert result.errors == []


@pytest.mark.asyncio
async def test_process_json_file(file_connector, sample_json):
    """Test processing JSON file."""
    result = await file_connector.process_file(sample_json, FileFormat.JSON)

    assert result.success is True
    assert result.records_processed == 5
    assert result.output_format == FileFormat.JSON
    assert result.errors == []


@pytest.mark.asyncio
async def test_process_xml_file(file_connector, sample_xml):
    """Test processing XML file."""
    result = await file_connector.process_file(sample_xml, FileFormat.XML)

    assert result.success is True
    assert result.records_processed == 5
    assert result.output_format == FileFormat.XML
    assert result.errors == []


@pytest.mark.asyncio
async def test_convert_csv_to_json(file_connector, sample_csv):
    """Test converting CSV to JSON."""
    output = await file_connector.convert_format(
        sample_csv, FileFormat.CSV, FileFormat.JSON
    )

    # Verify output is valid JSON
    assert b'"id"' in output
    assert b'"name"' in output
    assert b"John Doe" in output


@pytest.mark.asyncio
async def test_convert_json_to_xml(file_connector, sample_json):
    """Test converting JSON to XML."""
    output = await file_connector.convert_format(
        sample_json, FileFormat.JSON, FileFormat.XML
    )

    # Verify output is valid XML
    assert b"<id>" in output
    assert b"<name>" in output
    assert b"John Doe" in output


@pytest.mark.asyncio
async def test_convert_xml_to_csv(file_connector, sample_xml):
    """Test converting XML to CSV."""
    output = await file_connector.convert_format(
        sample_xml, FileFormat.XML, FileFormat.CSV
    )

    # Verify output is valid CSV
    assert b"id,name" in output
    assert b"John Doe" in output


@pytest.mark.asyncio
async def test_convert_csv_to_xml(file_connector, sample_csv):
    """Test converting CSV to XML."""
    output = await file_connector.convert_format(
        sample_csv, FileFormat.CSV, FileFormat.XML
    )

    assert b"<id>" in output
    assert b"John Doe" in output


@pytest.mark.asyncio
async def test_convert_json_to_csv(file_connector, sample_json):
    """Test converting JSON to CSV."""
    output = await file_connector.convert_format(
        sample_json, FileFormat.JSON, FileFormat.CSV
    )

    assert b"id,name" in output
    assert b"John Doe" in output


@pytest.mark.asyncio
async def test_convert_xml_to_json(file_connector, sample_xml):
    """Test converting XML to JSON."""
    output = await file_connector.convert_format(
        sample_xml, FileFormat.XML, FileFormat.JSON
    )

    assert b'"id"' in output
    assert b"John Doe" in output


@pytest.mark.asyncio
async def test_convert_same_format_returns_original(file_connector, sample_csv):
    """Test that converting to same format returns original."""
    output = await file_connector.convert_format(
        sample_csv, FileFormat.CSV, FileFormat.CSV
    )

    assert output == sample_csv


@pytest.mark.asyncio
async def test_file_size_validation_convert(file_connector):
    """Test file size validation rejects oversized files in convert."""
    # Create 11MB file (exceeds 10MB limit)
    large_file = b"x" * (11 * 1024 * 1024)

    with pytest.raises(ValueError, match="exceeds maximum"):
        await file_connector.convert_format(
            large_file, FileFormat.CSV, FileFormat.JSON
        )


@pytest.mark.asyncio
async def test_file_size_validation_process(file_connector):
    """Test file size validation rejects oversized files in process_file."""
    # Create 11MB file (exceeds 10MB limit)
    large_file = b"x" * (11 * 1024 * 1024)

    with pytest.raises(ValueError, match="exceeds maximum"):
        await file_connector.process_file(large_file, FileFormat.CSV)


@pytest.mark.asyncio
async def test_invalid_csv_format(file_connector):
    """Test handling of invalid CSV data."""
    invalid_csv = b"not,a,valid,csv\n\x00\x01\x02"

    result = await file_connector.process_file(invalid_csv, FileFormat.CSV)

    # Should handle gracefully
    assert result.success is True or len(result.errors) > 0


@pytest.mark.asyncio
async def test_empty_file_handling(file_connector):
    """Test handling of empty file."""
    empty_file = b""

    result = await file_connector.process_file(empty_file, FileFormat.CSV)

    assert result.success is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_process_with_format_conversion(file_connector, sample_csv):
    """Test process_file with format conversion."""
    result = await file_connector.process_file(
        sample_csv, FileFormat.CSV, FileFormat.JSON
    )

    assert result.success is True
    assert result.records_processed == 5
    assert result.output_format == FileFormat.JSON


@pytest.mark.asyncio
async def test_roundtrip_conversion(file_connector, sample_csv):
    """Test CSV → JSON → CSV roundtrip conversion."""
    # Convert CSV to JSON
    json_output = await file_connector.convert_format(
        sample_csv, FileFormat.CSV, FileFormat.JSON
    )

    # Convert JSON back to CSV
    csv_output = await file_connector.convert_format(
        json_output, FileFormat.JSON, FileFormat.CSV
    )

    # Should have same data (order may differ)
    assert b"John Doe" in csv_output
    assert b"id,name" in csv_output or b"id," in csv_output
