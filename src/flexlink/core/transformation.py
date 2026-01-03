"""Data transformation engine for field mapping and value transformations."""

import logging
from datetime import datetime
from typing import Any

from flexlink.models.transformation import TransformationRule

# JSONata support (optional dependency)
try:
    import jsonata  # type: ignore[import-not-found]

    JSONATA_AVAILABLE = True
except ImportError:
    JSONATA_AVAILABLE = False
    jsonata = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Expression cache (avoid recompiling same expressions)
_expression_cache: dict[str, Any] = {}  # Maps expression string to compiled Jsonata object


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
            Transformed and filtered data dictionary
        """
        result = data.copy()

        # Apply transformation rules sequentially
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

        # Apply field filtering
        # Collect all include/exclude from rules
        all_includes = []
        all_excludes = []
        has_include_filter = False
        has_exclude_filter = False

        for rule in self.rules:
            if rule.include_fields is not None:
                all_includes.extend(rule.include_fields)
                has_include_filter = True
            if rule.exclude_fields is not None:
                all_excludes.extend(rule.exclude_fields)
                has_exclude_filter = True

        # Apply filtering if any rules specified filters
        if has_include_filter or has_exclude_filter:
            # Remove duplicates while preserving order
            unique_includes = list(dict.fromkeys(all_includes)) if has_include_filter else None
            unique_excludes = list(dict.fromkeys(all_excludes)) if has_exclude_filter else None

            try:
                result = self._filter_fields(result, unique_includes, unique_excludes)
                logger.debug(
                    f"Applied field filtering: include={unique_includes}, exclude={unique_excludes}"
                )
            except Exception as e:
                logger.error(f"Field filtering failed: {e}")
                raise ValueError(f"Field filtering failed: {e}") from e

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
        # Check if expression is specified
        if rule.expression:
            # Expression takes precedence over transformation
            if rule.transformation:
                logger.warning(
                    f"Both 'expression' and 'transformation' specified for "
                    f"{rule.source_field} -> {rule.target_field}. "
                    f"Using expression, ignoring transformation '{rule.transformation}'."
                )

            # Evaluate expression against full data context
            try:
                target_value = self._evaluate_expression(rule.expression, data)
            except Exception as e:
                logger.error(f"Failed to evaluate expression for {rule.target_field}: {e}")
                raise ValueError(f"Expression evaluation failed for {rule.target_field}: {e}") from e

            # Set result
            if target_value is not None:
                self._set_nested_value(data, rule.target_field, target_value)

            return data

        # Original field mapping logic
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

    def _compile_expression(self, expression: str) -> Any:
        """
        Compile JSONata expression with caching.

        Args:
            expression: JSONata expression string

        Returns:
            Compiled Jsonata object

        Raises:
            ImportError: If jsonata-python not installed
            ValueError: If expression syntax is invalid
        """
        if not JSONATA_AVAILABLE or jsonata is None:
            raise ImportError(
                "jsonata-python library not installed. "
                "Install with: pip install jsonata-python"
            )

        # Check cache first
        if expression in _expression_cache:
            logger.debug(f"Using cached JSONata expression: {expression[:50]}...")
            return _expression_cache[expression]

        # Compile and cache
        try:
            compiled = jsonata.Jsonata(expression)  # type: ignore[union-attr]
            _expression_cache[expression] = compiled
            logger.debug(f"Compiled JSONata expression: {expression[:50]}...")
            return compiled
        except Exception as e:
            raise ValueError(
                f"Invalid JSONata expression: {expression[:100]}... Error: {e}"
            ) from e

    def _evaluate_expression(self, expression: str, data: dict[str, Any]) -> Any:
        """
        Evaluate JSONata expression against data.

        Args:
            expression: JSONata expression string
            data: Full data context (not just source field value)

        Returns:
            Expression evaluation result

        Raises:
            ValueError: If expression evaluation fails
        """
        try:
            compiled = self._compile_expression(expression)
            result = compiled.evaluate(data)
            logger.debug(f"Evaluated expression: {expression[:50]}... -> {str(result)[:50]}...")
            return result
        except ValueError:
            # Re-raise compilation errors
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to evaluate JSONata expression: {expression[:100]}... "
                f"against data. Error: {e}"
            ) from e

    def _filter_fields(
        self,
        data: dict[str, Any],
        include_fields: list[str] | None,
        exclude_fields: list[str] | None
    ) -> dict[str, Any]:
        """
        Filter fields from data based on include/exclude lists.

        Rules:
        - If include_fields specified: Only keep listed fields (whitelist)
        - If exclude_fields specified: Remove listed fields (blacklist)
        - If both specified: Exclude takes precedence
        - Supports dot notation for nested fields (e.g., "user.email")

        Args:
            data: Dictionary to filter
            include_fields: Fields to keep (None = keep all)
            exclude_fields: Fields to remove (None = remove none)

        Returns:
            Filtered dictionary
        """
        # Handle empty include list (return empty dict)
        if include_fields is not None and len(include_fields) == 0:
            return {}

        # No filtering if both are None
        if include_fields is None and exclude_fields is None:
            return data

        result = {}

        # Build include set (all fields if not specified)
        if include_fields:
            include_set = set(include_fields)
        else:
            include_set = set(self._get_all_field_paths(data))

        # Build exclude set
        exclude_set = set(exclude_fields) if exclude_fields else set()

        # Apply filtering - only include fields not in exclude set
        for field_path in sorted(include_set):  # Sort to process parent paths first
            if field_path not in exclude_set:
                value = self._get_nested_value(data, field_path)
                if value is not None:
                    self._set_nested_value(result, field_path, value)

        return result

    def _get_all_field_paths(self, data: dict[str, Any], prefix: str = "") -> list[str]:
        """
        Get all field paths in a nested dictionary.

        Only returns leaf paths (non-dict values) to avoid copying entire nested structures.

        Args:
            data: Dictionary to traverse
            prefix: Current path prefix (for recursion)

        Returns:
            List of all leaf field paths (dot notation)
        """
        paths = []

        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key

            # Only add leaf values (non-dicts) to paths
            if isinstance(value, dict):
                # Recurse into nested dicts
                paths.extend(self._get_all_field_paths(value, current_path))
            else:
                # Add leaf value
                paths.append(current_path)

        return paths
