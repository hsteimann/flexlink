"""Data transformation engine for field mapping and value transformations."""

import logging
from datetime import datetime
from typing import Any

from flexlink.models.transformation import TransformationRule

logger = logging.getLogger(__name__)


class TransformationEngine:
    """
    Applies transformation rules to data.

    Supports:
    - Field mapping with dot notation (e.g., "user.name" -> "userName")
    - Value transformations (upper, lower, strip, int, float, bool, date_format)
    - Default values for missing fields
    - Nested field access and creation
    """

    def __init__(self, rules: list[TransformationRule]):
        """
        Initialize transformation engine with rules.

        Args:
            rules: List of transformation rules to apply
        """
        self.rules = rules

    async def apply(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Apply all transformation rules to input data.

        Args:
            data: Input data dictionary

        Returns:
            Transformed data dictionary
        """
        result = data.copy()

        for rule in self.rules:
            try:
                result = await self._apply_rule(rule, result)
            except Exception as e:
                logger.error(
                    f"Failed to apply transformation rule "
                    f"{rule.source_field} -> {rule.target_field}: {e}"
                )
                raise ValueError(
                    f"Transformation failed for {rule.source_field}: {e}"
                ) from e

        return result

    async def _apply_rule(
        self, rule: TransformationRule, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Apply a single transformation rule.

        Args:
            rule: Transformation rule to apply
            data: Current data dictionary

        Returns:
            Transformed data dictionary
        """
        # Get source value (supports dot notation)
        source_value = self._get_nested_value(data, rule.source_field)

        # Use default value if source field is missing
        if source_value is None and rule.default_value is not None:
            source_value = rule.default_value
            logger.debug(
                f"Using default value for {rule.source_field}: {rule.default_value}"
            )

        # Apply transformation if specified
        if source_value is not None and rule.transformation:
            source_value = self._transform_value(source_value, rule.transformation)

        # Set target value (supports dot notation)
        if source_value is not None:
            self._set_nested_value(data, rule.target_field, source_value)

        return data

    def _get_nested_value(self, data: dict[str, Any], field_path: str) -> Any:
        """
        Get value from nested dictionary using dot notation.

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

    def _set_nested_value(self, data: dict[str, Any], field_path: str, value: Any) -> None:
        """
        Set value in nested dictionary using dot notation.

        Creates intermediate dictionaries if they don't exist.

        Args:
            data: Dictionary to set value in
            field_path: Field path (e.g., "user.name" or "name")
            value: Value to set
        """
        parts = field_path.split(".")
        current = data

        # Navigate/create nested structure
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set final value
        current[parts[-1]] = value

    def _transform_value(self, value: Any, transformation: str) -> Any:
        """
        Apply transformation function to value.

        Supported transformations:
        - upper: Convert to uppercase
        - lower: Convert to lowercase
        - strip: Remove leading/trailing whitespace
        - int: Convert to integer
        - float: Convert to float
        - bool: Convert to boolean
        - date_format: Format datetime to ISO format
        - str: Convert to string

        Args:
            value: Value to transform
            transformation: Transformation function name

        Returns:
            Transformed value

        Raises:
            ValueError: If transformation is unknown or fails
        """
        try:
            match transformation:
                case "upper":
                    return str(value).upper()
                case "lower":
                    return str(value).lower()
                case "strip":
                    return str(value).strip()
                case "int":
                    return int(value)
                case "float":
                    return float(value)
                case "bool":
                    # Convert various representations to bool
                    if isinstance(value, bool):
                        return value
                    if isinstance(value, str):
                        return value.lower() in ("true", "1", "yes", "on")
                    return bool(value)
                case "date_format":
                    # If value is datetime, format to ISO
                    if isinstance(value, datetime):
                        return value.isoformat()
                    # If value is string, try to parse and format
                    if isinstance(value, str):
                        try:
                            dt = datetime.fromisoformat(value)
                            return dt.isoformat()
                        except ValueError:
                            return value
                    return str(value)
                case "str":
                    return str(value)
                case _:
                    raise ValueError(f"Unknown transformation: {transformation}")
        except Exception as e:
            raise ValueError(
                f"Failed to apply transformation '{transformation}' to value '{value}': {e}"
            ) from e
