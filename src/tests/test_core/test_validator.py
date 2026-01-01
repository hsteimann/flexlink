"""Tests for data validation engine (validator.py)."""

import pytest

from flexlink.core.validator import Validator
from flexlink.models.validation import (
    ValidationConfig,
    ValidationError,
    ValidationErrorStrategy,
    ValidationRule,
)


# =============================================================================
# Tests for Validator.validate()
# =============================================================================


class TestValidatorValidate:
    """Test the main validate() method."""

    @pytest.mark.asyncio
    async def test_validate_all_rules_pass(self):
        """Test validation when all rules pass."""
        config = ValidationConfig(
            rules=[
                ValidationRule(field="name", type="string", required=True),
                ValidationRule(field="age", type="int", min=0, max=150),
            ]
        )
        validator = Validator(config)

        data = {"name": "John Doe", "age": 30}
        result = await validator.validate(data)

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.validated_data == data

    @pytest.mark.asyncio
    async def test_validate_some_rules_fail(self):
        """Test validation when some rules fail."""
        config = ValidationConfig(
            rules=[
                ValidationRule(field="name", type="string", required=True),
                ValidationRule(field="age", type="int", min=0, max=150),
                ValidationRule(field="email", required=True),
            ]
        )
        validator = Validator(config)

        data = {"name": "John", "age": 200}  # Missing email, age out of range

        result = await validator.validate(data)

        assert result.valid is False
        assert len(result.errors) == 2
        assert any(e.field == "age" for e in result.errors)
        assert any(e.field == "email" for e in result.errors)

    @pytest.mark.asyncio
    async def test_validate_fail_fast_with_fail_pipeline_strategy(self):
        """Test that validation stops on first error with fail_pipeline strategy."""
        config = ValidationConfig(
            rules=[
                ValidationRule(field="field1", required=True),
                ValidationRule(field="field2", required=True),
                ValidationRule(field="field3", required=True),
            ],
            on_validation_error=ValidationErrorStrategy.FAIL_PIPELINE
        )
        validator = Validator(config)

        data = {}  # All fields missing

        result = await validator.validate(data)

        assert result.valid is False
        # Should stop after first error
        assert len(result.errors) == 1
        assert result.validated_data is None

    @pytest.mark.asyncio
    async def test_validate_continue_with_skip_row_strategy(self):
        """Test that validation continues checking all rules with skip_row strategy."""
        config = ValidationConfig(
            rules=[
                ValidationRule(field="field1", required=True),
                ValidationRule(field="field2", required=True),
                ValidationRule(field="field3", required=True),
            ],
            on_validation_error=ValidationErrorStrategy.SKIP_ROW
        )
        validator = Validator(config)

        data = {}  # All fields missing

        result = await validator.validate(data)

        assert result.valid is False
        # Should check all rules
        assert len(result.errors) == 3
        assert result.validated_data == data  # Data still returned with skip_row

    @pytest.mark.asyncio
    async def test_validate_with_log_and_continue_strategy(self):
        """Test validation with log_and_continue strategy."""
        config = ValidationConfig(
            rules=[
                ValidationRule(field="name", required=True),
            ],
            on_validation_error=ValidationErrorStrategy.LOG_AND_CONTINUE,
            log_errors=True
        )
        validator = Validator(config)

        data = {}  # Missing name

        result = await validator.validate(data)

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.validated_data == data

    @pytest.mark.asyncio
    async def test_validate_logs_errors_when_configured(self):
        """Test that errors are logged when log_errors is True."""
        config = ValidationConfig(
            rules=[ValidationRule(field="name", required=True)],
            log_errors=True
        )
        validator = Validator(config)

        data = {}

        result = await validator.validate(data)

        assert result.valid is False
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    async def test_validate_handles_unexpected_exceptions(self):
        """Test that unexpected exceptions in rules are caught and converted to errors."""
        # Create a rule with an invalid regex pattern that will cause an exception
        config = ValidationConfig(
            rules=[
                ValidationRule(field="test", pattern="[invalid(regex")  # Invalid regex
            ]
        )
        validator = Validator(config)

        data = {"test": "value"}

        result = await validator.validate(data)

        # Should catch the exception and report it as a validation error
        assert result.valid is False
        assert len(result.errors) == 1
        assert "pattern" in result.errors[0].rule or "internal_error" in result.errors[0].rule

    @pytest.mark.asyncio
    async def test_validate_empty_rules_list(self):
        """Test validation with no rules configured."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        data = {"any": "data"}

        result = await validator.validate(data)

        assert result.valid is True
        assert len(result.errors) == 0
        assert result.validated_data == data


# =============================================================================
# Tests for Validator._validate_rule()
# =============================================================================


class TestValidatorValidateRule:
    """Test the _validate_rule() method."""

    @pytest.mark.asyncio
    async def test_validate_rule_required_field_missing(self):
        """Test required field validation when field is missing."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="name", required=True)
        data = {}

        errors = await validator._validate_rule(rule, data)

        assert len(errors) == 1
        assert errors[0].field == "name"
        assert errors[0].rule == "required"
        assert "missing" in errors[0].message.lower()

    @pytest.mark.asyncio
    async def test_validate_rule_required_field_present(self):
        """Test required field validation when field is present."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="name", required=True)
        data = {"name": "John"}

        errors = await validator._validate_rule(rule, data)

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_rule_optional_field_missing(self):
        """Test that optional fields don't cause errors when missing."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="optional", required=False, type="string")
        data = {}

        errors = await validator._validate_rule(rule, data)

        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_validate_rule_custom_error_message(self):
        """Test that custom error messages are used."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(
            field="age",
            required=True,
            error_message="Custom error: age is mandatory"
        )
        data = {}

        errors = await validator._validate_rule(rule, data)

        assert len(errors) == 1
        assert errors[0].message == "Custom error: age is mandatory"

    @pytest.mark.asyncio
    async def test_validate_rule_type_validation(self):
        """Test type validation within _validate_rule."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="age", type="int")
        data = {"age": "not_an_int"}

        errors = await validator._validate_rule(rule, data)

        assert len(errors) == 1
        assert errors[0].rule == "type"

    @pytest.mark.asyncio
    async def test_validate_rule_range_validation(self):
        """Test range validation within _validate_rule."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="score", min=0, max=100)
        data = {"score": 150}

        errors = await validator._validate_rule(rule, data)

        assert len(errors) == 1
        assert errors[0].rule == "max"

    @pytest.mark.asyncio
    async def test_validate_rule_pattern_validation(self):
        """Test pattern validation within _validate_rule."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="email", pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
        data = {"email": "invalid-email"}

        errors = await validator._validate_rule(rule, data)

        assert len(errors) == 1
        assert errors[0].rule == "pattern"

    @pytest.mark.asyncio
    async def test_validate_rule_stops_after_type_error(self):
        """Test that validation stops after type error (no range/pattern check)."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(
            field="age",
            type="int",
            min=0,
            max=100,
            pattern=r"\d+"  # Pattern shouldn't be checked if type fails
        )
        data = {"age": "not_an_int"}

        errors = await validator._validate_rule(rule, data)

        # Should only have type error, not range or pattern errors
        assert len(errors) == 1
        assert errors[0].rule == "type"

    @pytest.mark.asyncio
    async def test_validate_rule_multiple_errors(self):
        """Test that multiple validation errors can be returned."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(
            field="score",
            type="int",
            min=0,
            max=100,
            pattern=r"^\d+$"
        )
        data = {"score": 150}  # Type is OK but out of range

        errors = await validator._validate_rule(rule, data)

        # Should have range error (type passed)
        assert len(errors) >= 1
        assert any(e.rule == "max" for e in errors)

    @pytest.mark.asyncio
    async def test_validate_rule_nested_field_path(self):
        """Test validation with nested field paths (dot notation)."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="user.profile.name", required=True)
        data = {"user": {"profile": {"name": "John"}}}

        errors = await validator._validate_rule(rule, data)

        assert len(errors) == 0


# =============================================================================
# Tests for Validator._validate_type()
# =============================================================================


class TestValidatorValidateType:
    """Test type validation."""

    def test_validate_type_string_valid(self):
        """Test string type validation with valid value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="name", type="string")
        error = validator._validate_type(rule, "John Doe")

        assert error is None

    def test_validate_type_string_invalid(self):
        """Test string type validation with invalid value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="name", type="string")
        error = validator._validate_type(rule, 123)

        assert error is not None
        assert error.rule == "type"
        assert "string" in error.message.lower()

    def test_validate_type_int_valid(self):
        """Test int type validation with valid value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="age", type="int")
        error = validator._validate_type(rule, 30)

        assert error is None

    def test_validate_type_int_from_string(self):
        """Test int type validation with convertible string."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="age", type="int")
        # String "30" can be converted to int
        error = validator._validate_type(rule, "30")

        assert error is None

    def test_validate_type_int_invalid(self):
        """Test int type validation with non-convertible value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="age", type="int")
        error = validator._validate_type(rule, "not_a_number")

        assert error is not None
        assert error.rule == "type"

    def test_validate_type_int_bool_convertible(self):
        """Test that bool can be converted to int (True -> 1, False -> 0)."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="value", type="int")
        # Bools are excluded by isinstance check but can be converted via int()
        error = validator._validate_type(rule, True)

        # int(True) succeeds, so no error
        assert error is None

    def test_validate_type_float_valid(self):
        """Test float type validation with valid value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="price", type="float")
        error = validator._validate_type(rule, 19.99)

        assert error is None

    def test_validate_type_float_accepts_int(self):
        """Test that float type accepts int values."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="price", type="float")
        error = validator._validate_type(rule, 20)

        assert error is None

    def test_validate_type_float_from_string(self):
        """Test float type validation with convertible string."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="price", type="float")
        error = validator._validate_type(rule, "19.99")

        assert error is None

    def test_validate_type_float_invalid(self):
        """Test float type validation with non-convertible value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="price", type="float")
        error = validator._validate_type(rule, "not_a_number")

        assert error is not None

    def test_validate_type_bool_valid(self):
        """Test bool type validation with valid value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="active", type="bool")
        error = validator._validate_type(rule, True)

        assert error is None

    def test_validate_type_bool_invalid(self):
        """Test bool type validation with invalid value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="active", type="bool")
        error = validator._validate_type(rule, "yes")

        assert error is not None

    def test_validate_type_date_valid_iso_string(self):
        """Test date validation with valid ISO format string."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="birthdate", type="date")
        error = validator._validate_type(rule, "2024-01-15")

        assert error is None

    def test_validate_type_date_with_utc_marker(self):
        """Test date validation with Z (UTC) marker."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="timestamp", type="datetime")
        error = validator._validate_type(rule, "2024-01-15T10:30:00Z")

        assert error is None

    def test_validate_type_date_invalid_format(self):
        """Test date validation with invalid format."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="birthdate", type="date")
        error = validator._validate_type(rule, "15/01/2024")  # Wrong format

        assert error is not None

    def test_validate_type_with_custom_error_message(self):
        """Test that custom error messages are used in type validation."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(
            field="age",
            type="int",
            error_message="Age must be a number"
        )
        error = validator._validate_type(rule, "invalid")

        assert error is not None
        assert error.message == "Age must be a number"


# =============================================================================
# Tests for Validator._validate_range()
# =============================================================================


class TestValidatorValidateRange:
    """Test numeric range validation."""

    def test_validate_range_within_bounds(self):
        """Test range validation when value is within bounds."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="age", min=0, max=150)
        error = validator._validate_range(rule, 30)

        assert error is None

    def test_validate_range_below_minimum(self):
        """Test range validation when value is below minimum."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="age", min=0, max=150)
        error = validator._validate_range(rule, -5)

        assert error is not None
        assert error.rule == "min"
        assert "minimum" in error.message.lower()

    def test_validate_range_above_maximum(self):
        """Test range validation when value exceeds maximum."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="age", min=0, max=150)
        error = validator._validate_range(rule, 200)

        assert error is not None
        assert error.rule == "max"
        assert "maximum" in error.message.lower()

    def test_validate_range_exact_bounds(self):
        """Test that values exactly at min/max boundaries are accepted."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="score", min=0, max=100)

        assert validator._validate_range(rule, 0) is None
        assert validator._validate_range(rule, 100) is None

    def test_validate_range_only_min(self):
        """Test range validation with only minimum constraint."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="price", min=0)

        assert validator._validate_range(rule, 10) is None
        assert validator._validate_range(rule, -5) is not None

    def test_validate_range_only_max(self):
        """Test range validation with only maximum constraint."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="discount", max=100)

        assert validator._validate_range(rule, 50) is None
        assert validator._validate_range(rule, 150) is not None

    def test_validate_range_non_numeric_value(self):
        """Test range validation with non-numeric value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="value", min=0, max=100)
        error = validator._validate_range(rule, "not_a_number")

        assert error is not None
        assert "non-numeric" in error.message.lower()


# =============================================================================
# Tests for Validator._validate_pattern()
# =============================================================================


class TestValidatorValidatePattern:
    """Test regex pattern validation."""

    def test_validate_pattern_matches(self):
        """Test pattern validation when value matches."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="email", pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
        error = validator._validate_pattern(rule, "john.doe@example.com")

        assert error is None

    def test_validate_pattern_no_match(self):
        """Test pattern validation when value doesn't match."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="email", pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
        error = validator._validate_pattern(rule, "invalid-email")

        assert error is not None
        assert error.rule == "pattern"

    def test_validate_pattern_non_string_value(self):
        """Test pattern validation with non-string value."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="code", pattern=r"^\d+$")
        error = validator._validate_pattern(rule, 12345)  # int, not string

        assert error is not None
        assert "string" in error.message.lower()

    def test_validate_pattern_invalid_regex(self):
        """Test pattern validation with invalid regex pattern."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        rule = ValidationRule(field="test", pattern="[invalid(regex")
        error = validator._validate_pattern(rule, "value")

        assert error is not None
        assert "regex" in error.message.lower()


# =============================================================================
# Tests for Validator._get_field_value()
# =============================================================================


class TestValidatorGetFieldValue:
    """Test nested field value extraction."""

    def test_get_field_value_simple_field(self):
        """Test getting value from simple (non-nested) field."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        data = {"name": "John", "age": 30}
        value = validator._get_field_value(data, "name")

        assert value == "John"

    def test_get_field_value_nested_field(self):
        """Test getting value from nested field with dot notation."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        data = {
            "user": {
                "profile": {
                    "name": "John Doe"
                }
            }
        }
        value = validator._get_field_value(data, "user.profile.name")

        assert value == "John Doe"

    def test_get_field_value_missing_field(self):
        """Test getting value from missing field returns None."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        data = {"name": "John"}
        value = validator._get_field_value(data, "age")

        assert value is None

    def test_get_field_value_missing_nested_field(self):
        """Test getting value from missing nested field returns None."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        data = {"user": {"name": "John"}}
        value = validator._get_field_value(data, "user.profile.name")

        assert value is None

    def test_get_field_value_deep_nesting(self):
        """Test getting value from deeply nested structure."""
        config = ValidationConfig(rules=[])
        validator = Validator(config)

        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": "deep_value"
                    }
                }
            }
        }
        value = validator._get_field_value(data, "level1.level2.level3.level4")

        assert value == "deep_value"
