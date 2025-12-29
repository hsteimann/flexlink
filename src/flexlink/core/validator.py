"""Data validation engine for ensuring data quality."""

import logging
import re
from datetime import datetime
from typing import Any

from flexlink.models.validation import (
    ValidationConfig,
    ValidationError,
    ValidationErrorStrategy,
    ValidationResult,
    ValidationRule,
)

logger = logging.getLogger(__name__)


class Validator:
    """
    Validates data against configured validation rules.

    Supports:
    - Type validation (string, int, float, bool, date, datetime)
    - Range validation (min, max for numeric types)
    - Pattern validation (regex for strings)
    - Required field validation
    - Configurable error handling strategies
    """

    def __init__(self, config: ValidationConfig):
        """
        Initialize validator with configuration.

        Args:
            config: Validation configuration with rules and error strategy
        """
        self.config = config
        self.rules = config.rules
        self.error_strategy = config.on_validation_error
        self.log_errors = config.log_errors

    async def validate(self, data: dict[str, Any]) -> ValidationResult:
        """
        Validate data against all configured rules.

        Args:
            data: Data dictionary to validate

        Returns:
            ValidationResult with validation status and any errors
        """
        errors: list[ValidationError] = []

        for rule in self.rules:
            try:
                rule_errors = await self._validate_rule(rule, data)
                errors.extend(rule_errors)

                # Fail fast if strategy is fail_pipeline
                if errors and self.error_strategy == ValidationErrorStrategy.FAIL_PIPELINE:
                    break

            except Exception as e:
                logger.error(f"Validation rule failed unexpectedly: {rule.field}: {e}")
                errors.append(ValidationError(
                    field=rule.field,
                    value=self._get_field_value(data, rule.field),
                    rule="internal_error",
                    message=f"Validation rule failed: {str(e)}"
                ))

        # Log errors if configured
        if errors and self.log_errors:
            for error in errors:
                logger.warning(
                    f"Validation error: {error.field}={error.value} - {error.message}"
                )

        # Determine result based on strategy
        valid = len(errors) == 0

        return ValidationResult(
            valid=valid,
            errors=errors,
            validated_data=data if valid or self.error_strategy != ValidationErrorStrategy.FAIL_PIPELINE else None
        )

    async def _validate_rule(
        self, rule: ValidationRule, data: dict[str, Any]
    ) -> list[ValidationError]:
        """
        Validate a single rule against data.

        Args:
            rule: Validation rule to apply
            data: Data to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[ValidationError] = []
        field_value = self._get_field_value(data, rule.field)

        # Required field check
        if rule.required and field_value is None:
            errors.append(ValidationError(
                field=rule.field,
                value=None,
                rule="required",
                message=rule.error_message or f"Required field '{rule.field}' is missing"
            ))
            return errors  # No point checking other rules if field is missing

        # If field is None and not required, skip other validations
        if field_value is None:
            return errors

        # Type validation
        if rule.type:
            type_error = self._validate_type(rule, field_value)
            if type_error:
                errors.append(type_error)
                return errors  # Type must be correct before range/pattern checks

        # Range validation (for numeric types)
        if rule.min is not None or rule.max is not None:
            range_error = self._validate_range(rule, field_value)
            if range_error:
                errors.append(range_error)

        # Pattern validation (for string types)
        if rule.pattern:
            pattern_error = self._validate_pattern(rule, field_value)
            if pattern_error:
                errors.append(pattern_error)

        return errors

    def _validate_type(self, rule: ValidationRule, value: Any) -> ValidationError | None:
        """Validate field type."""
        expected_type = rule.type

        try:
            if expected_type == "string":
                if not isinstance(value, str):
                    return ValidationError(
                        field=rule.field,
                        value=value,
                        rule="type",
                        message=rule.error_message or f"Expected string, got {type(value).__name__}"
                    )

            elif expected_type == "int":
                if not isinstance(value, int) or isinstance(value, bool):
                    # Try to convert
                    try:
                        int(value)
                    except (ValueError, TypeError):
                        return ValidationError(
                            field=rule.field,
                            value=value,
                            rule="type",
                            message=rule.error_message or f"Expected int, got {type(value).__name__}"
                        )

            elif expected_type == "float":
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    # Try to convert
                    try:
                        float(value)
                    except (ValueError, TypeError):
                        return ValidationError(
                            field=rule.field,
                            value=value,
                            rule="type",
                            message=rule.error_message or f"Expected float, got {type(value).__name__}"
                        )

            elif expected_type == "bool":
                if not isinstance(value, bool):
                    return ValidationError(
                        field=rule.field,
                        value=value,
                        rule="type",
                        message=rule.error_message or f"Expected bool, got {type(value).__name__}"
                    )

            elif expected_type in ("date", "datetime"):
                if isinstance(value, str):
                    # Try to parse ISO format
                    try:
                        datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        return ValidationError(
                            field=rule.field,
                            value=value,
                            rule="type",
                            message=rule.error_message or f"Invalid {expected_type} format (expected ISO format)"
                        )
                elif not isinstance(value, datetime):
                    return ValidationError(
                        field=rule.field,
                        value=value,
                        rule="type",
                        message=rule.error_message or f"Expected {expected_type}, got {type(value).__name__}"
                    )

        except Exception as e:
            logger.error(f"Type validation failed for {rule.field}: {e}")
            return ValidationError(
                field=rule.field,
                value=value,
                rule="type",
                message=f"Type validation error: {str(e)}"
            )

        return None

    def _validate_range(self, rule: ValidationRule, value: Any) -> ValidationError | None:
        """Validate numeric range."""
        try:
            numeric_value = float(value)

            if rule.min is not None and numeric_value < rule.min:
                return ValidationError(
                    field=rule.field,
                    value=value,
                    rule="min",
                    message=rule.error_message or f"Value {numeric_value} is less than minimum {rule.min}"
                )

            if rule.max is not None and numeric_value > rule.max:
                return ValidationError(
                    field=rule.field,
                    value=value,
                    rule="max",
                    message=rule.error_message or f"Value {numeric_value} exceeds maximum {rule.max}"
                )

        except (ValueError, TypeError) as e:
            return ValidationError(
                field=rule.field,
                value=value,
                rule="range",
                message=f"Cannot validate range for non-numeric value: {str(e)}"
            )

        return None

    def _validate_pattern(self, rule: ValidationRule, value: Any) -> ValidationError | None:
        """Validate string pattern (regex)."""
        if not isinstance(value, str):
            return ValidationError(
                field=rule.field,
                value=value,
                rule="pattern",
                message="Pattern validation requires string value"
            )

        if not rule.pattern:
            return None

        try:
            pattern = re.compile(rule.pattern)
            if not pattern.match(value):
                return ValidationError(
                    field=rule.field,
                    value=value,
                    rule="pattern",
                    message=rule.error_message or f"Value '{value}' doesn't match pattern '{rule.pattern}'"
                )

        except re.error as e:
            logger.error(f"Invalid regex pattern for {rule.field}: {rule.pattern}: {e}")
            return ValidationError(
                field=rule.field,
                value=value,
                rule="pattern",
                message=f"Invalid regex pattern: {str(e)}"
            )

        return None

    def _get_field_value(self, data: dict[str, Any], field_path: str) -> Any:
        """
        Get field value from nested dictionary using dot notation.

        Args:
            data: Dictionary to get value from
            field_path: Field path (e.g., "user.name" or "name")

        Returns:
            Field value or None if not found
        """
        parts = field_path.split(".")
        current = data

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None

        return current
