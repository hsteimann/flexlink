"""Tests for XML parser."""

from io import BytesIO

import pytest

from flexlink.parsers.xml_parser import XMLParser


@pytest.mark.asyncio
async def test_parse_valid_xml():
    """Test parsing valid XML data."""
    xml_data = b"""<?xml version="1.0"?>
    <data>
        <row><id>1</id><name>John</name></row>
        <row><id>2</id><name>Jane</name></row>
    </data>"""
    parser = XMLParser()

    df = await parser.parse(xml_data)

    assert len(df) == 2
    assert "id" in df.columns
    assert "name" in df.columns


@pytest.mark.asyncio
async def test_parse_xml_with_bytesio():
    """Test parsing XML from BytesIO."""
    xml_data = BytesIO(
        b'<?xml version="1.0"?><data><row><id>1</id><name>Alice</name></row></data>'
    )
    parser = XMLParser()

    df = await parser.parse(xml_data)

    assert len(df) == 1
    assert df.iloc[0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_parse_invalid_xml():
    """Test parsing invalid XML raises error."""
    invalid_xml = b"<invalid>xml"
    parser = XMLParser()

    with pytest.raises(ValueError, match="Failed to parse XML"):
        await parser.parse(invalid_xml)


@pytest.mark.asyncio
async def test_generate_xml():
    """Test generating XML from DataFrame."""
    import pandas as pd

    df = pd.DataFrame({"id": [1, 2], "name": ["John", "Jane"]})
    parser = XMLParser()

    xml_bytes = await parser.generate(df)
    xml_str = xml_bytes.decode("utf-8")

    assert "<id>" in xml_str
    assert "<name>" in xml_str
    assert "John" in xml_str


@pytest.mark.asyncio
async def test_parse_and_generate_roundtrip():
    """Test that parse -> generate -> parse produces same data."""
    original_data = b"""<?xml version="1.0"?>
    <data>
        <row><id>1</id><name>Alice</name></row>
        <row><id>2</id><name>Bob</name></row>
    </data>"""
    parser = XMLParser()

    # Parse original
    df1 = await parser.parse(original_data)

    # Generate XML
    generated = await parser.generate(df1)

    # Parse generated
    df2 = await parser.parse(generated)

    assert df1.equals(df2)


@pytest.mark.asyncio
async def test_validate_xml():
    """Test XML validation."""
    valid_xml = b'<?xml version="1.0"?><data><row><id>1</id></row></data>'
    invalid_xml = b"<not>valid"

    parser = XMLParser()

    assert await parser.validate(valid_xml) is True
    assert await parser.validate(invalid_xml) is False
