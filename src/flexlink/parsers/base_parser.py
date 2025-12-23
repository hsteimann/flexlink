"""Base parser interface for file format handling."""

from abc import ABC, abstractmethod
from io import BytesIO

import pandas as pd


class BaseParser(ABC):
    """
    Abstract base class for file format parsers.

    All parser implementations must inherit from this class and implement
    the abstract methods for parsing and generating files.
    """

    @abstractmethod
    async def parse(self, file_content: bytes | BytesIO) -> pd.DataFrame:
        """
        Parse file content into a pandas DataFrame.

        Args:
            file_content: File content as bytes or BytesIO

        Returns:
            Parsed data as pandas DataFrame

        Raises:
            ValueError: If file content is invalid or cannot be parsed
        """
        pass

    @abstractmethod
    async def generate(self, df: pd.DataFrame) -> bytes:
        """
        Generate file content from a pandas DataFrame.

        Args:
            df: DataFrame to convert to file format

        Returns:
            File content as bytes

        Raises:
            ValueError: If DataFrame cannot be converted to this format
        """
        pass

    async def validate(self, file_content: bytes | BytesIO) -> bool:
        """
        Validate file content (optional - can be overridden).

        Args:
            file_content: File content to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            await self.parse(file_content)
            return True
        except Exception:
            return False
