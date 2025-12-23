"""CSV file parser using pandas."""

import logging
from io import BytesIO

import pandas as pd

from flexlink.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class CSVParser(BaseParser):
    """CSV file parser using pandas with encoding detection."""

    async def parse(self, file_content: bytes | BytesIO) -> pd.DataFrame:
        """
        Parse CSV file content into DataFrame.

        Args:
            file_content: CSV file content as bytes or BytesIO

        Returns:
            Parsed data as DataFrame

        Raises:
            ValueError: If CSV cannot be parsed
        """
        try:
            # Handle both bytes and BytesIO
            if isinstance(file_content, bytes):
                file_content = BytesIO(file_content)

            # Try UTF-8 encoding first
            try:
                df = pd.read_csv(file_content, encoding="utf-8")
                logger.debug(f"Parsed CSV file: {len(df)} rows, {len(df.columns)} columns")
                return df
            except UnicodeDecodeError:
                # Fallback to latin-1 if UTF-8 fails
                logger.warning("UTF-8 decoding failed, trying latin-1")
                file_content.seek(0)
                df = pd.read_csv(file_content, encoding="latin-1")
                logger.debug(
                    f"Parsed CSV file with latin-1: {len(df)} rows, {len(df.columns)} columns"
                )
                return df

        except pd.errors.EmptyDataError:
            raise ValueError("CSV file is empty")
        except pd.errors.ParserError as e:
            raise ValueError(f"Failed to parse CSV: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file: {e}") from e

    async def generate(self, df: pd.DataFrame) -> bytes:
        """
        Generate CSV file content from DataFrame.

        Args:
            df: DataFrame to convert to CSV

        Returns:
            CSV file content as bytes

        Raises:
            ValueError: If DataFrame cannot be converted to CSV
        """
        try:
            buffer = BytesIO()
            df.to_csv(buffer, index=False, encoding="utf-8")
            buffer.seek(0)
            content = buffer.getvalue()
            logger.debug(f"Generated CSV: {len(content)} bytes")
            return content
        except Exception as e:
            raise ValueError(f"Failed to generate CSV file: {e}") from e
