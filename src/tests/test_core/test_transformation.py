"""Tests for transformation engine."""

from datetime import datetime

import pytest

from flexlink.core.transformation import TransformationEngine
from flexlink.models.transformation import TransformationRule


@pytest.mark.asyncio
async def test_simple_field_mapping():
    """Test simple field mapping without transformation."""
    data = {"name": "John", "age": 30}
    rules = [
        TransformationRule(source_field="name", target_field="full_name"),
        TransformationRule(source_field="age", target_field="user_age"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["full_name"] == "John"
    assert result["user_age"] == 30


@pytest.mark.asyncio
async def test_nested_field_mapping():
    """Test field mapping with dot notation."""
    data = {"user": {"name": "Alice", "email": "alice@test.com"}, "status": "active"}
    rules = [
        TransformationRule(source_field="user.name", target_field="userName"),
        TransformationRule(source_field="user.email", target_field="userEmail"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["userName"] == "Alice"
    assert result["userEmail"] == "alice@test.com"


@pytest.mark.asyncio
async def test_nested_target_field():
    """Test creating nested structure in target field."""
    data = {"name": "Bob", "email": "bob@test.com"}
    rules = [
        TransformationRule(source_field="name", target_field="user.name"),
        TransformationRule(source_field="email", target_field="user.email"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["user"]["name"] == "Bob"
    assert result["user"]["email"] == "bob@test.com"


@pytest.mark.asyncio
async def test_uppercase_transformation():
    """Test uppercase transformation."""
    data = {"name": "alice"}
    rules = [TransformationRule(source_field="name", target_field="name", transformation="upper")]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["name"] == "ALICE"


@pytest.mark.asyncio
async def test_lowercase_transformation():
    """Test lowercase transformation."""
    data = {"name": "ALICE"}
    rules = [TransformationRule(source_field="name", target_field="name", transformation="lower")]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["name"] == "alice"


@pytest.mark.asyncio
async def test_strip_transformation():
    """Test strip transformation."""
    data = {"name": "  Alice  "}
    rules = [TransformationRule(source_field="name", target_field="name", transformation="strip")]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["name"] == "Alice"


@pytest.mark.asyncio
async def test_int_transformation():
    """Test integer transformation."""
    data = {"age": "30", "count": "42"}
    rules = [
        TransformationRule(source_field="age", target_field="age", transformation="int"),
        TransformationRule(source_field="count", target_field="count", transformation="int"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["age"] == 30
    assert result["count"] == 42
    assert isinstance(result["age"], int)


@pytest.mark.asyncio
async def test_float_transformation():
    """Test float transformation."""
    data = {"price": "19.99"}
    rules = [TransformationRule(source_field="price", target_field="price", transformation="float")]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["price"] == 19.99
    assert isinstance(result["price"], float)


@pytest.mark.asyncio
async def test_bool_transformation():
    """Test boolean transformation."""
    data = {
        "active1": "true",
        "active2": "false",
        "active3": "1",
        "active4": "0",
        "active5": True,
    }
    rules = [
        TransformationRule(
            source_field="active1", target_field="is_active1", transformation="bool"
        ),
        TransformationRule(
            source_field="active2", target_field="is_active2", transformation="bool"
        ),
        TransformationRule(
            source_field="active3", target_field="is_active3", transformation="bool"
        ),
        TransformationRule(
            source_field="active4", target_field="is_active4", transformation="bool"
        ),
        TransformationRule(
            source_field="active5", target_field="is_active5", transformation="bool"
        ),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["is_active1"] is True
    assert result["is_active2"] is False
    assert result["is_active3"] is True
    assert result["is_active4"] is False
    assert result["is_active5"] is True


@pytest.mark.asyncio
async def test_str_transformation():
    """Test string transformation."""
    data = {"age": 30, "count": 42}
    rules = [
        TransformationRule(source_field="age", target_field="age_str", transformation="str"),
        TransformationRule(source_field="count", target_field="count_str", transformation="str"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["age_str"] == "30"
    assert result["count_str"] == "42"
    assert isinstance(result["age_str"], str)


@pytest.mark.asyncio
async def test_date_format_transformation():
    """Test date formatting transformation."""
    dt = datetime(2024, 1, 15, 10, 30, 0)
    data = {"created_at": dt}
    rules = [
        TransformationRule(
            source_field="created_at", target_field="created_at", transformation="date_format"
        )
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["created_at"] == "2024-01-15T10:30:00"


@pytest.mark.asyncio
async def test_default_value():
    """Test using default value when source field is missing."""
    data = {"name": "Alice"}
    rules = [
        TransformationRule(
            source_field="email", target_field="user_email", default_value="unknown@example.com"
        )
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["user_email"] == "unknown@example.com"


@pytest.mark.asyncio
async def test_default_value_with_transformation():
    """Test default value with transformation applied."""
    data = {"name": "Alice"}
    rules = [
        TransformationRule(
            source_field="status",
            target_field="status",
            default_value="active",
            transformation="upper",
        )
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_multiple_rules_in_sequence():
    """Test applying multiple transformation rules in sequence."""
    data = {"firstName": "alice", "lastName": "smith", "age": "30"}
    rules = [
        TransformationRule(
            source_field="firstName", target_field="user.first_name", transformation="upper"
        ),
        TransformationRule(
            source_field="lastName", target_field="user.last_name", transformation="upper"
        ),
        TransformationRule(source_field="age", target_field="user.age", transformation="int"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["user"]["first_name"] == "ALICE"
    assert result["user"]["last_name"] == "SMITH"
    assert result["user"]["age"] == 30


@pytest.mark.asyncio
async def test_complex_nested_transformation():
    """Test complex nested field transformations."""
    data = {"user": {"profile": {"name": "  john doe  ", "age": "25"}}, "status": "pending"}
    rules = [
        TransformationRule(
            source_field="user.profile.name",
            target_field="person.fullName",
            transformation="strip",
        ),
        TransformationRule(
            source_field="user.profile.age", target_field="person.age", transformation="int"
        ),
        TransformationRule(
            source_field="status", target_field="person.status", transformation="upper"
        ),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    assert result["person"]["fullName"] == "john doe"
    assert result["person"]["age"] == 25
    assert result["person"]["status"] == "PENDING"


@pytest.mark.asyncio
async def test_unknown_transformation():
    """Test error handling for unknown transformation."""
    data = {"name": "Alice"}
    rules = [
        TransformationRule(
            source_field="name", target_field="name", transformation="unknown_transform"
        )
    ]

    engine = TransformationEngine(rules)

    with pytest.raises(ValueError, match="Unknown transformation"):
        await engine.apply(data)


@pytest.mark.asyncio
async def test_failed_int_transformation():
    """Test error handling for failed int transformation."""
    data = {"age": "not_a_number"}
    rules = [TransformationRule(source_field="age", target_field="age", transformation="int")]

    engine = TransformationEngine(rules)

    with pytest.raises(ValueError, match="Transformation failed"):
        await engine.apply(data)


@pytest.mark.asyncio
async def test_missing_source_field_without_default():
    """Test that missing source field without default doesn't create target field."""
    data = {"name": "Alice"}
    rules = [TransformationRule(source_field="email", target_field="user_email")]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Target field should not be created if source is missing and no default
    assert "user_email" not in result


@pytest.mark.asyncio
async def test_empty_rules_list():
    """Test transformation engine with empty rules list."""
    data = {"name": "Alice", "age": 30}
    rules: list[TransformationRule] = []

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Data should be unchanged
    assert result == data


@pytest.mark.asyncio
async def test_preserve_original_data():
    """Test that original data is preserved alongside transformed data."""
    data = {"old_name": "Alice", "old_age": 30}
    rules = [
        TransformationRule(source_field="old_name", target_field="new_name"),
        TransformationRule(source_field="old_age", target_field="new_age"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Both old and new fields should exist
    assert result["old_name"] == "Alice"
    assert result["new_name"] == "Alice"
    assert result["old_age"] == 30
    assert result["new_age"] == 30
