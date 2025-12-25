"""File processing models."""

from enum import Enum

from pydantic import BaseModel, Field

from flexlink.models.transformation import TransformationRule


class FileFormat(str, Enum):
    """Supported file formats."""

    CSV = "csv"
    JSON = "json"
    XML = "xml"


class FileUploadRequest(BaseModel):
    """File upload request metadata."""

    filename: str = Field(..., description="Original filename")
    format: FileFormat = Field(..., description="File format")
    target_format: FileFormat | None = Field(
        default=None,
        description="Target format for conversion (if different from source)"
    )
    apply_transformations: bool = Field(
        default=False,
        description="Whether to apply transformation rules to the data"
    )
    transformation_rules: list[TransformationRule] = Field(
        default_factory=list,
        description="Transformation rules to apply during processing"
    )
    forward_to_connector: str | None = Field(
        default=None,
        description="Optional connector name to forward processed data to"
    )


class FileProcessingResult(BaseModel):
    """Result of file processing operation."""

    success: bool = Field(..., description="Whether processing succeeded")
    records_processed: int = Field(..., description="Number of records processed")
    output_format: FileFormat = Field(..., description="Output file format")
    output_filename: str = Field(..., description="Generated output filename")
    download_url: str | None = Field(
        default=None,
        description="URL to download the processed file"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of errors encountered during processing"
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of warnings during processing"
    )


class FileForwardResult(BaseModel):
    """Result of file-to-REST forwarding operation."""

    success: bool = Field(..., description="Whether forwarding succeeded")
    records_parsed: int = Field(..., description="Number of records parsed from file")
    records_forwarded: int = Field(..., description="Number of records successfully forwarded")
    records_failed: int = Field(..., description="Number of records that failed to forward")
    batch_mode: str = Field(..., description="Forwarding mode used (individual or batch)")
    target_route: str = Field(..., description="Target route for forwarding")
    responses: list[dict] = Field(
        default_factory=list,
        description="Summary of responses (status codes and counts)"
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of errors encountered during forwarding"
    )
