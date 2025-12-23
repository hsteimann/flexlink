"""Tests for CSV parser."""

from io import BytesIO

import pytest

from flexlink.parsers.csv_parser import CSVParser


@pytest.mark.asyncio
async def test_parse_valid_csv():
    """Test parsing valid CSV data."""
    csv_data = b"id,name,email\n1,John,john@test.com\n2,Jane,jane@test.com"
    parser = CSVParser()

    df = await parser.parse(csv_data)

    assert len(df) == 2
    assert list(df.columns) == ["id", "name", "email"]
    assert df.iloc[0]["name"] == "John"
    assert df.iloc[1]["email"] == "jane@test.com"


@pytest.mark.asyncio
async def test_parse_csv_with_bytesio():
    """Test parsing CSV from BytesIO."""
    csv_data = BytesIO(b"id,name\n1,Alice\n2,Bob")
    parser = CSVParser()

    df = await parser.parse(csv_data)

    assert len(df) == 2
    assert df.iloc[0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_parse_empty_csv():
    """Test parsing empty CSV raises error."""
    csv_data = b""
    parser = CSVParser()

    with pytest.raises(ValueError, match="empty"):
        await parser.parse(csv_data)


@pytest.mark.asyncio
async def test_generate_csv():
    """Test generating CSV from DataFrame."""
    import pandas as pd

    df = pd.DataFrame({"id": [1, 2], "name": ["John", "Jane"]})
    parser = CSVParser()

    csv_bytes = await parser.generate(df)

    assert b"id,name" in csv_bytes
    assert b"John" in csv_bytes
    assert b"Jane" in csv_bytes


@pytest.mark.asyncio
async def test_parse_and_generate_roundtrip():
    """Test that parse -> generate -> parse produces same data."""
    original_data = b"id,name,status\n1,Alice,active\n2,Bob,inactive"
    parser = CSVParser()

    # Parse original
    df1 = await parser.parse(original_data)

    # Generate CSV
    generated = await parser.generate(df1)

    # Parse generated
    df2 = await parser.parse(generated)

    assert df1.equals(df2)


@pytest.mark.asyncio
async def test_validate_csv():
    """Test CSV validation."""
    valid_csv = b"id,name\n1,John"

    parser = CSVParser()

    assert await parser.validate(valid_csv) is True
