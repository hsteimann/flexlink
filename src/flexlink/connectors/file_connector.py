"""File-based connector for CSV, JSON, and XML processing."""

import logging
from typing import Any

from flexlink.core.connector import BaseConnector
from flexlink.models.connector import ConnectorConfig
from flexlink.models.file import FileFormat, FileProcessingResult
from flexlink.models.request import IntegrationResponse
from flexlink.parsers.parser_factory import ParserFactory

logger = logging.getLogger(__name__)


class FileConnector(BaseConnector):
    """
    Connector for processing file-based data (CSV, JSON, XML).

    Supports:
    - File parsing from bytes
    - Format conversion (CSV ↔ JSON ↔ XML)
    - Data transformation using pandas DataFrames
    - File generation in different formats
    """

    # Maximum file size in bytes (10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, config: ConnectorConfig):
        """
        Initialize file connector.

        Args:
            config: Connector configuration
        """
        super().__init__(config)
        self.parser_factory = ParserFactory()

    async def send_request(
        self,
        method: str,
        path: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> IntegrationResponse:
        """
        Process file request (not typically used for file connector).

        File connector primarily uses process_file() and convert_format() methods.

        Args:
            method: Operation type (e.g., "PARSE", "CONVERT")
            path: File format or operation
            data: Request data
            **kwargs: Additional parameters

        Returns:
            IntegrationResponse with processing results
        """
        # This is a minimal implementation for interface compliance
        # Real file processing happens in process_file() and convert_format()
        return IntegrationResponse(
            status_code=200,
            body={"message": "File connector ready"},
        )

    async def process_file(
        self,
        file_content: bytes,
        source_format: FileFormat,
        target_format: FileFormat | None = None,
    ) -> FileProcessingResult:
        """
        Process file content: parse and optionally convert format.

        Args:
            file_content: Raw file content as bytes
            source_format: Source file format
            target_format: Target format for conversion (optional)

        Returns:
            FileProcessingResult with processing details
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Validate file is not empty
        if len(file_content) == 0:
            errors.append("File is empty")
            return FileProcessingResult(
                success=False,
                records_processed=0,
                output_format=source_format,
                output_filename="",
                errors=errors,
                warnings=warnings,
            )

        # Validate file size
        if len(file_content) > self.MAX_FILE_SIZE:
            errors.append(
                f"File size {len(file_content)} bytes exceeds maximum "
                f"{self.MAX_FILE_SIZE} bytes (10MB)"
            )
            return FileProcessingResult(
                success=False,
                records_processed=0,
                output_format=source_format,
                output_filename="",
                errors=errors,
                warnings=warnings,
            )

        try:
            # Parse source file
            source_parser = self.parser_factory.get_parser(source_format)
            df = await source_parser.parse(file_content)

            records_processed = len(df)
            logger.info(
                f"Parsed {source_format.value} file: {records_processed} records, "
                f"{len(df.columns)} columns"
            )

            # Convert to target format if specified
            if target_format and target_format != source_format:
                target_parser = self.parser_factory.get_parser(target_format)
                _ = await target_parser.generate(df)
                output_format = target_format
                logger.info(f"Converted {source_format.value} → {target_format.value}")
            else:
                # No conversion, use source format
                output_format = source_format

            return FileProcessingResult(
                success=True,
                records_processed=records_processed,
                output_format=output_format,
                output_filename=f"processed.{output_format.value}",
                errors=errors,
                warnings=warnings,
            )

        except ValueError as e:
            logger.error(f"File processing failed: {e}")
            errors.append(str(e))
            return FileProcessingResult(
                success=False,
                records_processed=0,
                output_format=source_format,
                output_filename="",
                errors=errors,
                warnings=warnings,
            )

    async def convert_format(
        self,
        file_content: bytes,
        source_format: FileFormat,
        target_format: FileFormat,
    ) -> bytes:
        """
        Convert file from one format to another.

        Args:
            file_content: Source file content as bytes
            source_format: Source file format
            target_format: Target file format

        Returns:
            Converted file content as bytes

        Raises:
            ValueError: If conversion fails or file is invalid
        """
        # Validate file size
        if len(file_content) > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size {len(file_content)} bytes exceeds maximum "
                f"{self.MAX_FILE_SIZE} bytes (10MB)"
            )

        # If same format, return as-is
        if source_format == target_format:
            logger.info(f"No conversion needed: {source_format.value} → {target_format.value}")
            return file_content

        # Parse source
        source_parser = self.parser_factory.get_parser(source_format)
        df = await source_parser.parse(file_content)

        logger.info(
            f"Converting {source_format.value} → {target_format.value}: "
            f"{len(df)} records"
        )

        # Generate target
        target_parser = self.parser_factory.get_parser(target_format)
        output_content = await target_parser.generate(df)

        logger.info(
            f"Conversion complete: {len(file_content)} bytes → {len(output_content)} bytes"
        )

        return output_content

    async def transform_request(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform request data (default: no transformation for file connector).

        Args:
            data: Request data

        Returns:
            Transformed data (unchanged by default)
        """
        return data

    async def transform_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Transform response data (default: no transformation for file connector).

        Args:
            data: Response data

        Returns:
            Transformed data (unchanged by default)
        """
        return data
