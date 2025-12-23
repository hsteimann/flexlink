"""End-to-end tests for file processing."""

import pytest

from flexlink.connectors.file_connector import FileConnector
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.file import FileFormat


@pytest.fixture
def file_connector():
    """Create file connector for testing."""
    config = ConnectorConfig(
        name="file_connector",
        type="file",
        base_url="",
        auth=AuthConfig(type="none"),
    )
    return FileConnector(config)


@pytest.mark.asyncio
async def test_e2e_csv_processing(file_connector):
    """Test end-to-end CSV file processing."""
    # Create CSV content
    csv_content = b"""id,name,email,country,active
1,Alice,alice@test.com,US,true
2,Bob,bob@test.com,UK,false
3,Charlie,charlie@test.com,CA,true
4,Diana,diana@test.com,AU,false
5,Eve,eve@test.com,NZ,true"""

    # Process CSV
    result = await file_connector.process_file(
        file_content=csv_content, source_format=FileFormat.CSV
    )

    # Verify results
    assert result.success is True
    assert result.records_processed == 5
    assert result.output_format == FileFormat.CSV


@pytest.mark.asyncio
async def test_e2e_json_processing(file_connector):
    """Test end-to-end JSON file processing."""
    # Create JSON content
    json_content = b"""[
  {"id": 1, "name": "Alice", "role": "admin"},
  {"id": 2, "name": "Bob", "role": "user"},
  {"id": 3, "name": "Charlie", "role": "user"}
]"""

    # Process JSON
    result = await file_connector.process_file(
        file_content=json_content, source_format=FileFormat.JSON
    )

    # Verify results
    assert result.success is True
    assert result.records_processed == 3
    assert result.output_format == FileFormat.JSON


@pytest.mark.asyncio
async def test_e2e_xml_processing(file_connector):
    """Test end-to-end XML file processing."""
    # Create XML content
    xml_content = b"""<?xml version="1.0"?>
<data>
    <row><id>1</id><name>Alice</name><department>Engineering</department></row>
    <row><id>2</id><name>Bob</name><department>Sales</department></row>
    <row><id>3</id><name>Charlie</name><department>Marketing</department></row>
    <row><id>4</id><name>Diana</name><department>HR</department></row>
</data>"""

    # Process XML
    result = await file_connector.process_file(
        file_content=xml_content, source_format=FileFormat.XML
    )

    # Verify results
    assert result.success is True
    assert result.records_processed == 4
    assert result.output_format == FileFormat.XML


@pytest.mark.asyncio
async def test_e2e_csv_to_json_conversion(file_connector):
    """Test end-to-end CSV to JSON conversion."""
    # Create CSV content
    csv_content = b"id,product,price,quantity\n1,Widget,19.99,100\n2,Gadget,29.99,50"

    # Convert CSV to JSON
    json_output = await file_connector.convert_format(
        file_content=csv_content,
        source_format=FileFormat.CSV,
        target_format=FileFormat.JSON,
    )

    # Verify output is valid JSON
    assert b'"id"' in json_output
    assert b'"product"' in json_output
    assert b"Widget" in json_output
    assert b"Gadget" in json_output

    # Verify roundtrip: JSON back to CSV
    csv_output = await file_connector.convert_format(
        file_content=json_output,
        source_format=FileFormat.JSON,
        target_format=FileFormat.CSV,
    )

    # Verify CSV headers
    assert b"id,product,price,quantity" in csv_output


@pytest.mark.asyncio
async def test_e2e_json_to_xml_conversion(file_connector):
    """Test end-to-end JSON to XML conversion."""
    # Create JSON content
    json_content = b'[{"user_id": 1, "username": "alice"}, {"user_id": 2, "username": "bob"}]'

    # Convert JSON to XML
    xml_output = await file_connector.convert_format(
        file_content=json_content,
        source_format=FileFormat.JSON,
        target_format=FileFormat.XML,
    )

    # Verify XML structure
    assert b"<user_id>" in xml_output
    assert b"<username>" in xml_output
    assert b"alice" in xml_output


@pytest.mark.asyncio
async def test_e2e_xml_to_csv_conversion(file_connector):
    """Test end-to-end XML to CSV conversion."""
    # Create XML content
    xml_content = b"""<?xml version="1.0"?>
<data>
    <row><order_id>1001</order_id><customer>Alice</customer><total>150.00</total></row>
    <row><order_id>1002</order_id><customer>Bob</customer><total>275.50</total></row>
</data>"""

    # Convert XML to CSV
    csv_output = await file_connector.convert_format(
        file_content=xml_content,
        source_format=FileFormat.XML,
        target_format=FileFormat.CSV,
    )

    # Verify CSV structure
    assert b"order_id,customer,total" in csv_output
    assert b"Alice" in csv_output
    assert b"Bob" in csv_output


@pytest.mark.asyncio
async def test_e2e_large_file_processing(file_connector):
    """Test processing larger file (but under 10MB limit)."""
    # Create large CSV (1000 rows)
    header = b"id,name,email,created_at\n"
    rows = [
        f"{i},User{i},user{i}@test.com,2024-01-{i%28+1:02d}\n".encode()
        for i in range(1, 1001)
    ]
    large_csv = header + b"".join(rows)

    # Process large file
    result = await file_connector.process_file(
        file_content=large_csv, source_format=FileFormat.CSV
    )

    # Verify results
    assert result.success is True
    assert result.records_processed == 1000


@pytest.mark.asyncio
async def test_e2e_file_with_special_characters(file_connector):
    """Test processing file with special characters."""
    # Create CSV with special characters (using encoding)
    csv_text = """id,name,description
1,Cafe,"Coffee shop"
2,Name,"A name"
3,Resume,"Professional resume"
"""
    csv_content = csv_text.encode('utf-8')

    # Process file
    result = await file_connector.process_file(
        file_content=csv_content, source_format=FileFormat.CSV
    )

    # Verify results
    assert result.success is True
    assert result.records_processed == 3


@pytest.mark.asyncio
async def test_e2e_roundtrip_all_formats(file_connector):
    """Test roundtrip conversion through all formats."""
    # Start with CSV
    original_csv = b"id,value,status\n1,100,active\n2,200,inactive"

    # CSV → JSON
    json_data = await file_connector.convert_format(
        file_content=original_csv,
        source_format=FileFormat.CSV,
        target_format=FileFormat.JSON,
    )

    # JSON → XML
    xml_data = await file_connector.convert_format(
        file_content=json_data,
        source_format=FileFormat.JSON,
        target_format=FileFormat.XML,
    )

    # XML → CSV (complete roundtrip)
    final_csv = await file_connector.convert_format(
        file_content=xml_data,
        source_format=FileFormat.XML,
        target_format=FileFormat.CSV,
    )

    # Verify data integrity (headers should match)
    assert b"id" in final_csv
    assert b"value" in final_csv
    assert b"status" in final_csv


@pytest.mark.asyncio
async def test_e2e_file_size_limit_enforcement(file_connector):
    """Test that file size limit is enforced."""
    # Create file larger than 10MB
    large_content = b"x" * (11 * 1024 * 1024)  # 11MB

    # Attempt to process
    result = await file_connector.process_file(
        file_content=large_content, source_format=FileFormat.CSV
    )

    # Verify failure
    assert result.success is False
    assert len(result.errors) > 0
    assert "File size" in result.errors[0]


@pytest.mark.asyncio
async def test_e2e_empty_file_handling(file_connector):
    """Test handling of empty files."""
    # Create empty file
    empty_content = b""

    # Process empty file
    result = await file_connector.process_file(
        file_content=empty_content, source_format=FileFormat.CSV
    )

    # Verify failure with appropriate error
    assert result.success is False
    assert len(result.errors) > 0


@pytest.mark.asyncio
async def test_e2e_malformed_file_handling(file_connector):
    """Test handling of malformed files."""
    # Create malformed JSON
    malformed_json = b'{"incomplete": '

    # Attempt to process
    result = await file_connector.process_file(
        file_content=malformed_json, source_format=FileFormat.JSON
    )

    # Verify failure
    assert result.success is False
    assert len(result.errors) > 0
