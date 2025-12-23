"""File upload and download API routes."""

import io

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse

from flexlink.connectors.file_connector import FileConnector
from flexlink.models.connector import AuthConfig, ConnectorConfig
from flexlink.models.file import FileFormat, FileProcessingResult

router = APIRouter(prefix="/api/v1/files", tags=["files"])


def get_file_connector() -> FileConnector:
    """
    Create FileConnector instance.

    Returns:
        FileConnector instance
    """
    config = ConnectorConfig(
        name="file_connector",
        type="file",
        base_url="",  # Not used for file connector
        auth=AuthConfig(type="none"),
    )
    return FileConnector(config)


@router.post("/upload", response_model=FileProcessingResult)
async def upload_file(
    file: UploadFile = File(...),
    source_format: FileFormat = Query(..., description="Source file format"),
    target_format: FileFormat | None = Query(
        None, description="Convert to this format (optional)"
    ),
) -> FileProcessingResult:
    """
    Upload and process a file.

    Features:
    - Validates file size (max 10MB)
    - Parses file in source format (CSV, JSON, XML)
    - Optionally converts to target format
    - Returns processing results with record count

    Args:
        file: Uploaded file
        source_format: Source file format (csv, json, xml)
        target_format: Optional target format for conversion

    Returns:
        FileProcessingResult with success status and details

    Raises:
        HTTPException: If file processing fails
    """
    try:
        # Read file content
        content = await file.read()

        # Process file
        connector = get_file_connector()
        result = await connector.process_file(
            file_content=content,
            source_format=source_format,
            target_format=target_format,
        )

        # Check if processing failed
        if not result.success:
            # Distinguish between request errors and processing errors
            # File size errors should return 400, other errors return 200 with success=False
            if result.errors and any("File size" in error for error in result.errors):
                error_detail = "; ".join(result.errors)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error_detail,
                )
            # For other processing errors (parsing, validation), return the result
            # with success=False so caller can see details

        return result

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File processing failed: {str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.post("/convert", response_class=StreamingResponse)
async def convert_file(
    file: UploadFile = File(...),
    source_format: FileFormat = Query(..., description="Source file format"),
    target_format: FileFormat = Query(..., description="Target file format"),
) -> StreamingResponse:
    """
    Convert file from one format to another.

    Supports all conversion paths:
    - CSV ↔ JSON
    - CSV ↔ XML
    - JSON ↔ XML

    Args:
        file: Uploaded file to convert
        source_format: Source file format
        target_format: Target file format

    Returns:
        Converted file as downloadable attachment

    Raises:
        HTTPException: If conversion fails
    """
    try:
        # Read file content
        content = await file.read()

        # Convert format
        connector = get_file_connector()
        converted_content = await connector.convert_format(
            file_content=content,
            source_format=source_format,
            target_format=target_format,
        )

        # Determine filename
        original_filename = file.filename or "file"
        # Remove extension from original filename
        base_filename = original_filename.rsplit(".", 1)[0]
        output_filename = f"{base_filename}.{target_format.value}"

        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(converted_content),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={output_filename}"},
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File conversion failed: {str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get("/formats")
async def list_formats() -> dict[str, list[str]]:
    """
    List supported file formats.

    Returns:
        Dictionary with list of supported formats
    """
    return {"formats": [format.value for format in FileFormat]}


@router.get("/health")
async def file_service_health() -> dict[str, str]:
    """
    Health check for file processing service.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "file_processing"}
