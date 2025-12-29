"""File upload and download API routes."""

import io
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse

from flexlink.api.dependencies import get_registry, get_router
from flexlink.config import get_settings
from flexlink.connectors.file_connector import FileConnector
from flexlink.core.router import RequestRouter
from flexlink.models.file import FileFormat, FileForwardResult
from flexlink.models.request import IntegrationRequest

# File storage configuration from settings
settings = get_settings()
DOWNLOADS_DIR = settings.download_dir
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

# TTL for downloaded files (from settings, converted from seconds to hours for readability)
FILE_TTL_SECONDS = settings.temp_file_ttl_seconds

router = APIRouter(prefix="/api/v1/files", tags=["files"])


def get_file_connector() -> FileConnector:
    """
    Get file connector from registry.

    Returns:
        FileConnector instance from registry

    Raises:
        HTTPException: If file connector not found in registry
    """
    registry = get_registry()
    try:
        connector = registry.get_connector("file")
        if not isinstance(connector, FileConnector):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="File connector has incorrect type",
            )
        return connector
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File connector not registered. Check config/connectors/file.yaml exists and is loaded.",
        )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    source_format: FileFormat = Query(..., description="Source file format"),
    target_format: FileFormat | None = Query(
        None, description="Convert to this format (optional)"
    ),
    return_file: bool = Query(
        False, description="Return the processed file content instead of just metadata"
    ),
    save_file: bool = Query(
        True, description="Save processed file for later download (creates download_url)"
    ),
):
    """
    Upload and process a file.

    Features:
    - Validates file size (max 10MB)
    - Parses file in source format (CSV, JSON, XML)
    - Optionally converts to target format
    - Saves processed file for async download (default)
    - Returns processing results with record count
    - Optionally returns the processed file content immediately

    Args:
        file: Uploaded file
        source_format: Source file format (csv, json, xml)
        target_format: Optional target format for conversion
        return_file: If True, returns file content immediately; if False, returns metadata
        save_file: If True (default), saves file and returns download_url

    Returns:
        StreamingResponse with file content if return_file=True,
        FileProcessingResult (JSON) with download_url if save_file=True

    Raises:
        HTTPException: If file processing fails
    """
    try:
        # Read file content
        content = await file.read()

        # Process file
        connector = get_file_connector()
        result, output_content = await connector.process_file(
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

        # Save file for later download if requested
        if save_file and output_content:
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            file_extension = result.output_format.value
            saved_filename = f"{file_id}.{file_extension}"
            file_path = DOWNLOADS_DIR / saved_filename

            # Write file to disk
            file_path.write_bytes(output_content)

            # Set download URL
            result.download_url = f"/api/v1/files/download/{file_id}"

        # Return file content immediately if requested
        if return_file and output_content:
            return StreamingResponse(
                io.BytesIO(output_content),
                media_type="application/octet-stream",
                headers={
                    "Content-Disposition": f"attachment; filename={result.output_filename}"
                },
            )

        # Otherwise return metadata (with download_url if saved)
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


@router.get("/download/{file_id}")
async def download_file(file_id: str) -> FileResponse:
    """
    Download a previously processed file.

    Files are stored temporarily (default 24 hours) after upload processing.
    Use the download_url from the upload response to retrieve files asynchronously.

    Args:
        file_id: UUID of the saved file (from download_url)

    Returns:
        FileResponse with the saved file

    Raises:
        HTTPException 404: If file not found or expired
        HTTPException 400: If file_id format is invalid
    """
    try:
        # Validate UUID format
        uuid.UUID(file_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file ID format: {file_id}",
        )

    # Find file with any supported extension
    file_path = None
    for format in FileFormat:
        candidate_path = DOWNLOADS_DIR / f"{file_id}.{format.value}"
        if candidate_path.exists():
            file_path = candidate_path
            break

    if not file_path:
        # Calculate TTL in hours for user-friendly message
        ttl_hours = FILE_TTL_SECONDS / 3600
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_id} (may have expired after {ttl_hours:.1f} hours)",
        )

    # Determine media type based on extension
    extension = file_path.suffix.lstrip(".")
    media_type_map = {
        "csv": "text/csv",
        "json": "application/json",
        "xml": "application/xml",
    }
    media_type = media_type_map.get(extension, "application/octet-stream")

    # Return file
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=file_path.name,
    )


@router.get("/formats")
async def list_formats() -> dict[str, list[str]]:
    """
    List supported file formats.

    Returns:
        Dictionary with list of supported formats
    """
    return {"formats": [format.value for format in FileFormat]}


@router.delete("/cleanup")
async def cleanup_expired_files() -> dict[str, int]:
    """
    Clean up expired temporary files.

    Removes files older than the configured TTL (temp_file_ttl_seconds from settings).
    This endpoint can be called manually or automated via cron/scheduler.

    Returns:
        Dictionary with count of deleted files
    """
    deleted_count = 0
    current_time = datetime.now()
    expiry_threshold = current_time - timedelta(seconds=FILE_TTL_SECONDS)

    # Iterate through all files in downloads directory
    for file_path in DOWNLOADS_DIR.iterdir():
        if file_path.is_file():
            # Check file modification time
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_mtime < expiry_threshold:
                file_path.unlink()
                deleted_count += 1

    return {"deleted_files": deleted_count}


@router.post("/forward")
async def forward_file_to_rest(
    file: UploadFile = File(...),
    source_format: FileFormat = Query(..., description="Source file format"),
    target_route: str = Query(..., description="Target route to forward data to"),
    target_method: str = Query(
        "POST", description="HTTP method for forwarding (POST, PUT, PATCH)"
    ),
    batch_mode: str = Query(
        "individual",
        description="Forwarding mode: 'individual' (one request per record) or 'batch' (all records in one request)",
    ),
    request_router: RequestRouter = Depends(get_router),
) -> FileForwardResult:
    """
    Parse file and forward records through the routing/transformation pipeline.

    This endpoint bridges file processing with the REST connector pipeline,
    enabling batch ingestion workflows where file data is parsed, transformed,
    and forwarded to REST APIs.

    **Workflow:**
    1. Parse file into records (CSV/JSON/XML → list of dicts)
    2. For each record (or batch):
       - Create IntegrationRequest
       - Route through RequestRouter (applies route-level and connector transformations)
       - Forward to target REST connector
    3. Aggregate and return results

    **Example Use Cases:**
    - Upload CSV of customers → Transform → POST each to /api/customers
    - Upload JSON batch → Apply field mapping → Forward to external API
    - File-based ETL: Parse → Transform → Load via REST

    Args:
        file: File to upload and parse
        source_format: Source file format (csv, json, xml)
        target_route: Route configured in routing (e.g., "/users")
        target_method: HTTP method (POST, PUT, PATCH)
        batch_mode: "individual" (one request per record) or "batch" (all records in one array)
        request_router: RequestRouter instance (injected)

    Returns:
        FileForwardResult with aggregated forwarding statistics

    Raises:
        HTTPException: If file parsing or forwarding fails
    """
    errors: list[str] = []

    try:
        # Read file content
        content = await file.read()

        # Parse file into records
        connector = get_file_connector()
        records = await connector.parse_to_records(
            file_content=content,
            source_format=source_format,
        )

        records_parsed = len(records)

        if records_parsed == 0:
            return FileForwardResult(
                success=False,
                records_parsed=0,
                records_forwarded=0,
                records_failed=0,
                batch_mode=batch_mode,
                target_route=target_route,
                responses=[],
                errors=["No records found in file"],
            )

        # Forward records through router
        records_forwarded = 0
        records_failed = 0
        response_summary: dict[int, int] = {}  # status_code -> count

        if batch_mode == "batch":
            # Forward all records in a single request
            request = IntegrationRequest(
                route=target_route,
                method=target_method,
                body={"records": records},  # Wrap in object with "records" key
            )

            response = await request_router.route_request(request)

            if 200 <= response.status_code < 300:
                records_forwarded = records_parsed
            else:
                records_failed = records_parsed
                errors.append(
                    f"Batch request failed with status {response.status_code}: "
                    f"{response.error or 'Unknown error'}"
                )

            response_summary[response.status_code] = 1

        else:  # individual mode
            # Forward each record as a separate request
            for idx, record in enumerate(records):
                request = IntegrationRequest(
                    route=target_route,
                    method=target_method,
                    body=record,
                )

                response = await request_router.route_request(request)

                # Track response status
                response_summary[response.status_code] = (
                    response_summary.get(response.status_code, 0) + 1
                )

                if 200 <= response.status_code < 300:
                    records_forwarded += 1
                else:
                    records_failed += 1
                    errors.append(
                        f"Record {idx + 1} failed with status {response.status_code}: "
                        f"{response.error or 'Unknown error'}"
                    )

        # Build response summary
        responses = [
            {"status_code": status_code, "count": count}
            for status_code, count in sorted(response_summary.items())
        ]

        success = records_failed == 0

        return FileForwardResult(
            success=success,
            records_parsed=records_parsed,
            records_forwarded=records_forwarded,
            records_failed=records_failed,
            batch_mode=batch_mode,
            target_route=target_route,
            responses=responses,
            errors=errors[:10],  # Limit to first 10 errors
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File parsing failed: {str(e)}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get("/health")
async def file_service_health() -> dict[str, str]:
    """
    Health check for file processing service.

    Returns:
        Health status
    """
    return {"status": "healthy", "service": "file_processing"}
