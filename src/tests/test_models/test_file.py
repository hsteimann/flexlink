"""Tests for file processing models."""

import pytest

from flexlink.models.file import FileFormat, FileProcessingResult, FileUploadRequest
from flexlink.models.transformation import TransformationRule


def test_file_format_enum():
    """Test FileFormat enum values."""
    assert FileFormat.CSV == "csv"
    assert FileFormat.JSON == "json"
    assert FileFormat.XML == "xml"


def test_file_format_enum_validation():
    """Test FileFormat enum validation."""
    # Valid formats
    assert FileFormat("csv") == FileFormat.CSV
    assert FileFormat("json") == FileFormat.JSON
    assert FileFormat("xml") == FileFormat.XML

    # Invalid format should raise ValueError
    with pytest.raises(ValueError):
        FileFormat("txt")


def test_file_upload_request_minimal():
    """Test FileUploadRequest with minimal fields."""
    request = FileUploadRequest(
        filename="test.csv",
        format=FileFormat.CSV
    )
    assert request.filename == "test.csv"
    assert request.format == FileFormat.CSV
    assert request.target_format is None
    assert request.apply_transformations is False
    assert request.transformation_rules == []
    assert request.forward_to_connector is None


def test_file_upload_request_with_conversion():
    """Test FileUploadRequest with format conversion."""
    request = FileUploadRequest(
        filename="data.csv",
        format=FileFormat.CSV,
        target_format=FileFormat.JSON
    )
    assert request.format == FileFormat.CSV
    assert request.target_format == FileFormat.JSON


def test_file_upload_request_with_transformations():
    """Test FileUploadRequest with transformation rules."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="fullName",
            transformation="upper"
        )
    ]
    request = FileUploadRequest(
        filename="users.csv",
        format=FileFormat.CSV,
        apply_transformations=True,
        transformation_rules=rules
    )
    assert request.apply_transformations is True
    assert len(request.transformation_rules) == 1
    assert request.transformation_rules[0].source_field == "name"


def test_file_upload_request_with_connector_forward():
    """Test FileUploadRequest with connector forwarding."""
    request = FileUploadRequest(
        filename="orders.json",
        format=FileFormat.JSON,
        forward_to_connector="shopware6"
    )
    assert request.forward_to_connector == "shopware6"


def test_file_processing_result_success():
    """Test successful FileProcessingResult."""
    result = FileProcessingResult(
        success=True,
        records_processed=100,
        output_format=FileFormat.JSON,
        output_filename="output.json",
        download_url="/files/download/output.json"
    )
    assert result.success is True
    assert result.records_processed == 100
    assert result.output_format == FileFormat.JSON
    assert result.download_url == "/files/download/output.json"
    assert result.errors == []
    assert result.warnings == []


def test_file_processing_result_with_errors():
    """Test FileProcessingResult with errors."""
    result = FileProcessingResult(
        success=False,
        records_processed=50,
        output_format=FileFormat.CSV,
        output_filename="partial.csv",
        errors=["Row 5: Invalid data format", "Row 10: Missing required field"]
    )
    assert result.success is False
    assert len(result.errors) == 2
    assert "Row 5" in result.errors[0]


def test_file_processing_result_with_warnings():
    """Test FileProcessingResult with warnings."""
    result = FileProcessingResult(
        success=True,
        records_processed=100,
        output_format=FileFormat.XML,
        output_filename="data.xml",
        warnings=["Some fields contain null values", "Encoding converted from latin-1 to utf-8"]
    )
    assert result.success is True
    assert len(result.warnings) == 2
