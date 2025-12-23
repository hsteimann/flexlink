"""JSON file parser using pandas."""

import logging
from io import BytesIO

import pandas as pd

from flexlink.parsers.base_parser import BaseParser

logger = logging.getLogger(__name__)


class JSONParser(BaseParser):
    """JSON file parser using pandas with automatic orient detection."""

    async def parse(self, file_content: bytes | BytesIO) -> pd.DataFrame:
        """
        Parse JSON file content into DataFrame.

        Args:
            file_content: JSON file content as bytes or BytesIO

        Returns:
            Parsed data as DataFrame

        Raises:
            ValueError: If JSON cannot be parsed
        """
        try:
            # Handle both bytes and BytesIO
            if isinstance(file_content, bytes):
                file_content = BytesIO(file_content)

            # Try orient='records' first (most common: [{}, {}])
            try:
                df = pd.read_json(file_content, orient="records")
                logger.debug(f"Parsed JSON file: {len(df)} rows, {len(df.columns)} columns")
                return df
            except (ValueError, pd.errors.ParserError):
                # Auto-detect orient if records fails
                logger.debug("orient='records' failed, trying auto-detect")
                file_content.seek(0)
                df = pd.read_json(file_content)
                logger.debug(
                    f"Parsed JSON with auto-detect: {len(df)} rows, {len(df.columns)} columns"
                )
                return df

        except pd.errors.EmptyDataError:
            raise ValueError("JSON file is empty")
        except Exception as e:
            raise ValueError(f"Failed to parse JSON file: {e}") from e

    async def generate(self, df: pd.DataFrame) -> bytes:
        """
        Generate JSON file content from DataFrame.

        Args:
            df: DataFrame to convert to JSON

        Returns:
            JSON file content as bytes

        Raises:
            ValueError: If DataFrame cannot be converted to JSON
        """
        try:
            # Use orient='records' for array of objects [{}, {}]
            json_str = df.to_json(orient="records", indent=2)
            content = json_str.encode("utf-8")
            logger.debug(f"Generated JSON: {len(content)} bytes")
            return content
        except Exception as e:
            raise ValueError(f"Failed to generate JSON file: {e}") from e
