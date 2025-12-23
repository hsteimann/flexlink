"""Parser factory for selecting appropriate file format parser."""

import logging

from flexlink.models.file import FileFormat
from flexlink.parsers.base_parser import BaseParser
from flexlink.parsers.csv_parser import CSVParser
from flexlink.parsers.json_parser import JSONParser
from flexlink.parsers.xml_parser import XMLParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory for creating file format parsers.

    This factory returns the appropriate parser instance based on
    the requested file format.
    """

    def __init__(self) -> None:
        """Initialize parser factory."""
        self._parsers: dict[FileFormat, type[BaseParser]] = {
            FileFormat.CSV: CSVParser,
            FileFormat.JSON: JSONParser,
            FileFormat.XML: XMLParser,
        }

    def get_parser(self, file_format: FileFormat) -> BaseParser:
        """
        Get parser instance for the specified file format.

        Args:
            file_format: File format enum value

        Returns:
            Parser instance for the format

        Raises:
            ValueError: If format is not supported
        """
        parser_class = self._parsers.get(file_format)

        if parser_class is None:
            supported = ", ".join(f.value for f in self._parsers.keys())
            raise ValueError(
                f"Unsupported file format: {file_format.value}. "
                f"Supported formats: {supported}"
            )

        logger.debug(f"Created {parser_class.__name__} for format: {file_format.value}")
        return parser_class()

    def supports_format(self, file_format: FileFormat) -> bool:
        """
        Check if a file format is supported.

        Args:
            file_format: File format to check

        Returns:
            True if format is supported, False otherwise
        """
        return file_format in self._parsers

    def get_supported_formats(self) -> list[FileFormat]:
        """
        Get list of all supported file formats.

        Returns:
            List of supported FileFormat enum values
        """
        return list(self._parsers.keys())
