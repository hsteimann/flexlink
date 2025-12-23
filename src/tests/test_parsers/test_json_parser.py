"""Tests for JSON parser."""

from io import BytesIO

import pytest

from flexlink.parsers.json_parser import JSONParser


@pytest.mark.asyncio
async def test_parse_valid_json_array():
    """Test parsing valid JSON array."""
    json_data = b'[{"id": 1, "name": "John"}, {"id": 2, "name": "Jane"}]'
    parser = JSONParser()

    df = await parser.parse(json_data)

    assert len(df) == 2
    assert list(df.columns) == ["id", "name"]
    assert df.iloc[0]["name"] == "John"


@pytest.mark.asyncio
async def test_parse_json_with_bytesio():
    """Test parsing JSON from BytesIO."""
    json_data = BytesIO(b'[{"id": 1, "name": "Alice"}]')
    parser = JSONParser()

    df = await parser.parse(json_data)

    assert len(df) == 1
    assert df.iloc[0]["name"] == "Alice"


@pytest.mark.asyncio
async def test_parse_invalid_json():
    """Test parsing invalid JSON raises error."""
    invalid_json = b"{invalid json"
    parser = JSONParser()

    with pytest.raises(ValueError, match="Failed to parse JSON"):
        await parser.parse(invalid_json)


@pytest.mark.asyncio
async def test_generate_json():
    """Test generating JSON from DataFrame."""
    import pandas as pd

    df = pd.DataFrame({"id": [1, 2], "name": ["John", "Jane"]})
    parser = JSONParser()

    json_bytes = await parser.generate(df)
    json_str = json_bytes.decode("utf-8")

    assert '"id"' in json_str
    assert '"name"' in json_str
    assert "John" in json_str


@pytest.mark.asyncio
async def test_parse_and_generate_roundtrip():
    """Test that parse -> generate -> parse produces same data."""
    original_data = b'[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]'
    parser = JSONParser()

    # Parse original
    df1 = await parser.parse(original_data)

    # Generate JSON
    generated = await parser.generate(df1)

    # Parse generated
    df2 = await parser.parse(generated)

    assert df1.equals(df2)


@pytest.mark.asyncio
async def test_validate_json():
    """Test JSON validation."""
    valid_json = b'[{"id": 1}]'
    invalid_json = b"not json"

    parser = JSONParser()

    assert await parser.validate(valid_json) is True
    assert await parser.validate(invalid_json) is False
