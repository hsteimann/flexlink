"""XML file parser using pandas and lxml."""

import logging
from io import BytesIO
from typing import Any

import pandas as pd
from lxml import etree

from flexlink.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class XMLParser(BaseParser):
    """XML file parser using pandas with lxml backend."""

    async def parse(self, file_content: bytes | BytesIO) -> pd.DataFrame:
        """
        Parse XML file content into DataFrame.

        Handles both standard XML and nested field structures like:
        <item>
            <field name="item_no">VALUE</field>
            <field name="description">VALUE</field>
        </item>

        Args:
            file_content: XML file content as bytes or BytesIO

        Returns:
            Parsed data as DataFrame

        Raises:
            ValueError: If XML cannot be parsed
        """
        try:
            # Handle both bytes and BytesIO
            if isinstance(file_content, bytes):
                content_bytes = file_content
                file_content = BytesIO(file_content)
            else:
                content_bytes = file_content.getvalue()

            # Try parsing with lxml to detect nested field structure
            tree = etree.parse(BytesIO(content_bytes))
            root = tree.getroot()

            # Check if this is a nested field structure
            items = root.findall('.//item')
            if items and len(items) > 0:
                # Check if first item has nested <field name="..."> elements
                first_item = items[0]
                fields = first_item.findall('./field[@name]')

                if fields and len(fields) > 0:
                    # Use custom parser for nested field structure
                    logger.info("Detected nested field structure, using custom parser")
                    df = self._parse_nested_fields(root)
                    logger.debug(
                        f"Parsed XML with nested fields: {len(df)} rows, "
                        f"{len(df.columns)} columns"
                    )
                    return df

            # Fall back to standard pandas parsing
            df = pd.read_xml(BytesIO(content_bytes), parser="lxml")
            logger.debug(f"Parsed XML file: {len(df)} rows, {len(df.columns)} columns")
            return df

        except pd.errors.EmptyDataError:
            raise ValueError("XML file is empty")
        except Exception as e:
            raise ValueError(f"Failed to parse XML file: {e}") from e

    def _parse_nested_fields(self, root: etree._Element) -> pd.DataFrame:
        """
        Parse XML with nested <field name="...">VALUE</field> structure.

        Args:
            root: XML root element

        Returns:
            DataFrame with one row per item, columns from field names
        """
        items = root.findall('.//item')
        records: list[dict[str, Any]] = []

        for item in items:
            record: dict[str, Any] = {}

            # Extract all direct field children (not nested in collections)
            fields = item.findall('./field[@name]')
            for field in fields:
                name = field.get('name')
                value = field.text
                if name:
                    record[name] = value

            records.append(record)

        logger.debug(f"Extracted {len(records)} records with nested field parsing")
        return pd.DataFrame(records)

    async def generate(self, df: pd.DataFrame) -> bytes:
        """
        Generate XML file content from DataFrame.

        Args:
            df: DataFrame to convert to XML

        Returns:
            XML file content as bytes

        Raises:
            ValueError: If DataFrame cannot be converted to XML
        """
        try:
            xml_str = df.to_xml(index=False)
            content = xml_str.encode("utf-8")
            logger.debug(f"Generated XML: {len(content)} bytes")
            return content
        except Exception as e:
            raise ValueError(f"Failed to generate XML file: {e}") from e
