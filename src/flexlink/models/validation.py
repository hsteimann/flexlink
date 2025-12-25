"""Data validation models for ensuring data quality."""

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field


class ValidationErrorStrategy(str, Enum):
    """Strategy for handling validation errors."""

    SKIP_ROW = "skip_row"              # Skip invalid rows, continue processing
    FAIL_PIPELINE = "fail_pipeline"     # Stop entire pipeline on validation error
    LOG_AND_CONTINUE = "log_and_continue"  # Log error but don't skip row


class ValidationRule(BaseModel):
    """Validation rule for a single field."""

    field: str = Field(..., description="Field path to validate (supports dot notation)")

    # Type validation
    type: Literal["string", "int", "float", "bool", "date", "datetime"] | None = Field(
        default=None,
        description="Expected field type"
    )

    # Range validation (for numeric types)
    min: float | None = Field(default=None, description="Minimum value (inclusive)")
    max: float | None = Field(default=None, description="Maximum value (inclusive)")

    # Pattern validation (for string types)
    pattern: str | None = Field(
        default=None,
        description="Regex pattern for string validation"
    )

    # Required field check
    required: bool = Field(default=False, description="Whether field is required")

    # Custom validation function name (optional - for Phase 2C)
    custom_validator: str | None = Field(
        default=None,
        description="Name of custom validation function (future enhancement)"
    )

    # Error message template
    error_message: str | None = Field(
        default=None,
        description="Custom error message template (can use {field}, {value}, {rule})"
    )


class ValidationConfig(BaseModel):
    """Validation configuration for a mapping."""

    rules: list[ValidationRule] = Field(
        default_factory=list,
        description="List of validation rules to apply"
    )

    on_validation_error: ValidationErrorStrategy = Field(
        default=ValidationErrorStrategy.SKIP_ROW,
        description="Strategy for handling validation errors"
    )

    log_errors: bool = Field(
        default=True,
        description="Whether to log validation errors"
    )


class ValidationError(BaseModel):
    """Validation error details."""

    field: str = Field(..., description="Field that failed validation")
    value: Any = Field(..., description="Value that failed validation")
    rule: str = Field(..., description="Validation rule that failed")
    message: str = Field(..., description="Error message")


class ValidationResult(BaseModel):
    """Result of validation operation."""

    valid: bool = Field(..., description="Whether data passed validation")
    errors: list[ValidationError] = Field(
        default_factory=list,
        description="List of validation errors (if any)"
    )
    validated_data: dict[str, Any] | None = Field(
        default=None,
        description="Validated data (None if validation failed with fail_pipeline strategy)"
    )
