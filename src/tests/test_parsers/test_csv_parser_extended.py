"""Extended tests for CSV parser edge cases."""

from io import BytesIO

import pandas as pd
import pytest

from flexlink.parsers.csv_parser import CSVParser


class TestCSVParserEdgeCases:
    """Test CSV parser edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_parse_empty_csv_raises_error(self):
        """Test that empty CSV file raises ValueError."""
        parser = CSVParser()

        with pytest.raises(ValueError, match="CSV file is empty"):
            await parser.parse(b"")

    @pytest.mark.asyncio
    async def test_parse_csv_with_only_headers(self):
        """Test parsing CSV with headers but no data rows."""
        parser = CSVParser()
        csv_content = b"name,age,city\n"

        df = await parser.parse(csv_content)

        assert len(df) == 0
        assert list(df.columns) == ["name", "age", "city"]

    @pytest.mark.asyncio
    async def test_parse_csv_with_special_characters(self):
        """Test parsing CSV with special characters."""
        parser = CSVParser()
        csv_content = b'name,description\n"O\'Reilly","Quote with commas, and quotes"\n'

        df = await parser.parse(csv_content)

        assert len(df) == 1
        assert df["name"][0] == "O'Reilly"
        assert "Quote with commas" in df["description"][0]

    @pytest.mark.asyncio
    async def test_parse_csv_with_unicode_utf8(self):
        """Test parsing CSV with Unicode characters (UTF-8)."""
        parser = CSVParser()
        csv_content = "name,city\nJohn,Paris\nMarie,café\n".encode("utf-8")

        df = await parser.parse(csv_content)

        assert len(df) == 2
        assert df["city"][1] == "café"

    @pytest.mark.asyncio
    async def test_parse_csv_with_unicode_latin1_fallback(self):
        """Test parsing CSV with Latin-1 encoding (fallback)."""
        parser = CSVParser()
        # Create content that's valid Latin-1 but invalid UTF-8
        csv_content = b"name,city\nJohn,Caf\xe9\n"  # \xe9 is é in Latin-1

        df = await parser.parse(csv_content)

        assert len(df) == 1
        assert "caf" in df["city"][0].lower()

    @pytest.mark.asyncio
    async def test_parse_csv_from_bytesio(self):
        """Test parsing CSV from BytesIO object."""
        parser = CSVParser()
        csv_content = BytesIO(b"name,age\nJohn,30\n")

        df = await parser.parse(csv_content)

        assert len(df) == 1
        assert df["name"][0] == "John"

    @pytest.mark.asyncio
    async def test_parse_csv_with_missing_values(self):
        """Test parsing CSV with missing/null values."""
        parser = CSVParser()
        csv_content = b"name,age,city\nJohn,30,NYC\nJane,,LA\nBob,25,\n"

        df = await parser.parse(csv_content)

        assert len(df) == 3
        assert pd.isna(df["age"][1])
        assert pd.isna(df["city"][2])

    @pytest.mark.asyncio
    async def test_parse_malformed_csv_raises_error(self):
        """Test that malformed CSV raises ValueError."""
        parser = CSVParser()
        # Mismatched quotes
        csv_content = b'name,age\n"John,30\n'

        with pytest.raises(ValueError, match="Failed to parse CSV"):
            await parser.parse(csv_content)

    @pytest.mark.asyncio
    async def test_generate_csv_from_dataframe(self):
        """Test generating CSV from DataFrame."""
        parser = CSVParser()
        df = pd.DataFrame({"name": ["John", "Jane"], "age": [30, 25]})

        csv_bytes = await parser.generate(df)

        assert isinstance(csv_bytes, bytes)
        assert b"name,age" in csv_bytes
        assert b"John,30" in csv_bytes

    @pytest.mark.asyncio
    async def test_generate_csv_from_empty_dataframe(self):
        """Test generating CSV from empty DataFrame."""
        parser = CSVParser()
        df = pd.DataFrame(columns=["name", "age"])

        csv_bytes = await parser.generate(df)

        assert b"name,age" in csv_bytes
        assert len(csv_bytes.split(b"\n")) == 2  # Header + empty line

    @pytest.mark.asyncio
    async def test_generate_csv_with_special_characters(self):
        """Test generating CSV with special characters."""
        parser = CSVParser()
        df = pd.DataFrame({"name": ["O'Reilly"], "description": ['Quote: "Hello"']})

        csv_bytes = await parser.generate(df)

        # Should be properly quoted/escaped
        assert b"O'Reilly" in csv_bytes

    @pytest.mark.asyncio
    async def test_parse_and_generate_roundtrip(self):
        """Test that parse -> generate -> parse produces same data."""
        parser = CSVParser()
        original_df = pd.DataFrame({
            "name": ["John", "Jane"],
            "age": [30, 25],
            "city": ["NYC", "LA"]
        })

        # Generate CSV
        csv_bytes = await parser.generate(original_df)

        # Parse it back
        parsed_df = await parser.parse(csv_bytes)

        # Should match original
        pd.testing.assert_frame_equal(original_df, parsed_df)
