"""Extended tests for XML parser edge cases."""

from io import BytesIO

import pandas as pd
import pytest

from flexlink.parsers.xml_parser import XMLParser


class TestXMLParserEdgeCases:
    """Test XML parser edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_parse_empty_xml_raises_error(self):
        """Test that empty XML file raises ValueError."""
        parser = XMLParser()

        with pytest.raises(ValueError, match="Failed to parse XML"):
            await parser.parse(b"")

    @pytest.mark.asyncio
    async def test_parse_malformed_xml_raises_error(self):
        """Test that malformed XML raises ValueError."""
        parser = XMLParser()
        xml_content = b"<root><item><field>unclosed"

        with pytest.raises(ValueError, match="Failed to parse XML"):
            await parser.parse(xml_content)

    @pytest.mark.asyncio
    async def test_parse_standard_xml(self):
        """Test parsing standard XML structure."""
        parser = XMLParser()
        xml_content = b"""
        <data>
            <row>
                <name>John</name>
                <age>30</age>
            </row>
            <row>
                <name>Jane</name>
                <age>25</age>
            </row>
        </data>
        """

        df = await parser.parse(xml_content)

        assert len(df) == 2
        assert "name" in df.columns
        assert df["name"][0] == "John"

    @pytest.mark.asyncio
    async def test_parse_nested_field_structure(self):
        """Test parsing XML with nested <field name='...'> structure."""
        parser = XMLParser()
        xml_content = b"""
        <data>
            <item>
                <field name="item_no">12345</field>
                <field name="description">Test Product</field>
            </item>
            <item>
                <field name="item_no">67890</field>
                <field name="description">Another Product</field>
            </item>
        </data>
        """

        df = await parser.parse(xml_content)

        assert len(df) == 2
        assert "item_no" in df.columns
        assert "description" in df.columns
        assert df["item_no"][0] == "12345"
        assert df["description"][1] == "Another Product"

    @pytest.mark.asyncio
    async def test_parse_nested_fields_with_null_values(self):
        """Test parsing nested fields with missing/null values."""
        parser = XMLParser()
        xml_content = b"""
        <data>
            <item>
                <field name="item_no">12345</field>
                <field name="description"></field>
            </item>
            <item>
                <field name="item_no">67890</field>
            </item>
        </data>
        """

        df = await parser.parse(xml_content)

        assert len(df) == 2
        assert pd.isna(df["description"][0]) or df["description"][0] == ""

    @pytest.mark.asyncio
    async def test_parse_xml_from_bytesio(self):
        """Test parsing XML from BytesIO object."""
        parser = XMLParser()
        xml_content = BytesIO(b"""
        <data>
            <row><name>John</name></row>
        </data>
        """)

        df = await parser.parse(xml_content)

        assert len(df) == 1
        assert df["name"][0] == "John"

    @pytest.mark.asyncio
    async def test_parse_xml_with_unicode(self):
        """Test parsing XML with Unicode characters."""
        parser = XMLParser()
        xml_content = """
        <data>
            <row>
                <name>Café</name>
                <city>Paris</city>
            </row>
        </data>
        """.encode("utf-8")

        df = await parser.parse(xml_content)

        assert df["name"][0] == "Café"

    @pytest.mark.asyncio
    async def test_parse_xml_with_special_characters(self):
        """Test parsing XML with special/escaped characters."""
        parser = XMLParser()
        xml_content = b"""
        <data>
            <row>
                <text>Value with &lt;brackets&gt; and &amp; ampersand</text>
            </row>
        </data>
        """

        df = await parser.parse(xml_content)

        assert "<brackets>" in df["text"][0]
        assert "&" in df["text"][0]

    @pytest.mark.asyncio
    async def test_generate_xml_from_dataframe(self):
        """Test generating XML from DataFrame."""
        parser = XMLParser()
        df = pd.DataFrame({"name": ["John", "Jane"], "age": [30, 25]})

        xml_bytes = await parser.generate(df)

        assert isinstance(xml_bytes, bytes)
        assert b"<name>John</name>" in xml_bytes
        assert b"<age>30</age>" in xml_bytes

    @pytest.mark.asyncio
    async def test_generate_xml_from_empty_dataframe(self):
        """Test generating XML from empty DataFrame."""
        parser = XMLParser()
        df = pd.DataFrame(columns=["name", "age"])

        xml_bytes = await parser.generate(df)

        assert isinstance(xml_bytes, bytes)
        # Should still have XML structure
        assert b"<" in xml_bytes and b">" in xml_bytes

    @pytest.mark.asyncio
    async def test_parse_and_generate_roundtrip(self):
        """Test that parse -> generate -> parse produces similar data."""
        parser = XMLParser()
        original_df = pd.DataFrame({
            "name": ["John", "Jane"],
            "age": [30, 25]
        })

        # Generate XML
        xml_bytes = await parser.generate(original_df)

        # Parse it back
        parsed_df = await parser.parse(xml_bytes)

        # Should have same data (column order may differ)
        assert len(parsed_df) == len(original_df)
        assert set(parsed_df.columns) == set(original_df.columns)
        assert parsed_df["name"].tolist() == original_df["name"].tolist()

    @pytest.mark.asyncio
    async def test_parse_nested_fields_empty_item(self):
        """Test parsing nested fields with an empty item."""
        parser = XMLParser()
        xml_content = b"""
        <data>
            <item>
                <field name="item_no">12345</field>
            </item>
            <item>
            </item>
        </data>
        """

        df = await parser.parse(xml_content)

        assert len(df) == 2
