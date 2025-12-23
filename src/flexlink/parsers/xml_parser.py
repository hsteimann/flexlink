"""XML file parser using pandas and lxml."""

import logging
from io import BytesIO

import pandas as pd

from flexlink.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class XMLParser(BaseParser):
    """XML file parser using pandas with lxml backend."""

    async def parse(self, file_content: bytes | BytesIO) -> pd.DataFrame:
        """
        Parse XML file content into DataFrame.

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
                file_content = BytesIO(file_content)

            # Use lxml parser for better compatibility
            df = pd.read_xml(file_content, parser="lxml")
            logger.debug(f"Parsed XML file: {len(df)} rows, {len(df.columns)} columns")
            return df

        except pd.errors.EmptyDataError:
            raise ValueError("XML file is empty")
        except Exception as e:
            raise ValueError(f"Failed to parse XML file: {e}") from e

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
