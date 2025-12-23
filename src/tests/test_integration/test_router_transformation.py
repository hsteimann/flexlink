"""Integration tests for router + transformation engine."""

import pytest

from flexlink.core.transformation import TransformationEngine
from flexlink.models.transformation import TransformationRule


@pytest.mark.asyncio
async def test_transformation_preserves_original_fields():
    """Test that transformations preserve original fields."""
    data = {"old_name": "Alice", "old_age": 30}
    rules = [
        TransformationRule(source_field="old_name", target_field="new_name"),
        TransformationRule(source_field="old_age", target_field="new_age"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Both old and new fields should exist
    assert "old_name" in result
    assert "new_name" in result
    assert result["old_name"] == "Alice"
    assert result["new_name"] == "Alice"


@pytest.mark.asyncio
async def test_chained_transformations_order():
    """Test that transformations are applied in order."""
    data = {"value": "  HELLO  "}
    rules = [
        TransformationRule(
            source_field="value", target_field="value", transformation="strip"
        ),
        TransformationRule(
            source_field="value", target_field="value", transformation="lower"
        ),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Should be stripped then lowercased
    assert result["value"] == "hello"


@pytest.mark.asyncio
async def test_nested_field_transformation_creates_structure():
    """Test that nested field transformations create proper structure."""
    data = {"name": "Alice", "email": "alice@test.com", "age": 30}
    rules = [
        TransformationRule(source_field="name", target_field="user.profile.name"),
        TransformationRule(source_field="email", target_field="user.contact.email"),
        TransformationRule(source_field="age", target_field="user.profile.age"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Verify nested structure created
    assert "user" in result
    assert "profile" in result["user"]
    assert "contact" in result["user"]
    assert result["user"]["profile"]["name"] == "Alice"
    assert result["user"]["contact"]["email"] == "alice@test.com"
    assert result["user"]["profile"]["age"] == 30


@pytest.mark.asyncio
async def test_transformation_with_default_values():
    """Test transformations with default values for missing fields."""
    data = {"name": "Alice"}
    rules = [
        TransformationRule(
            source_field="email",
            target_field="contact_email",
            default_value="no-email@example.com",
        ),
        TransformationRule(
            source_field="phone",
            target_field="contact_phone",
            default_value="555-0000",
        ),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Verify default values used
    assert result["contact_email"] == "no-email@example.com"
    assert result["contact_phone"] == "555-0000"


@pytest.mark.asyncio
async def test_transformation_with_default_and_transform():
    """Test default value with transformation applied."""
    data = {"name": "Alice"}
    rules = [
        TransformationRule(
            source_field="status",
            target_field="user_status",
            default_value="pending",
            transformation="upper",
        )
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Default value should be transformed
    assert result["user_status"] == "PENDING"


@pytest.mark.asyncio
async def test_complex_multi_level_transformation():
    """Test complex transformation with multiple levels."""
    data = {
        "user": {
            "first_name": "alice",
            "last_name": "smith",
            "contact": {"email": "ALICE.SMITH@TEST.COM", "phone": "  555-1234  "},
        },
        "account": {"id": "123", "type": "premium", "active": "true"},
    }

    rules = [
        TransformationRule(
            source_field="user.first_name",
            target_field="profile.name.first",
            transformation="upper",
        ),
        TransformationRule(
            source_field="user.last_name",
            target_field="profile.name.last",
            transformation="upper",
        ),
        TransformationRule(
            source_field="user.contact.email",
            target_field="profile.email",
            transformation="lower",
        ),
        TransformationRule(
            source_field="user.contact.phone",
            target_field="profile.phone",
            transformation="strip",
        ),
        TransformationRule(
            source_field="account.id",
            target_field="account_info.id",
            transformation="int",
        ),
        TransformationRule(
            source_field="account.active",
            target_field="account_info.is_active",
            transformation="bool",
        ),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Verify all transformations
    assert result["profile"]["name"]["first"] == "ALICE"
    assert result["profile"]["name"]["last"] == "SMITH"
    assert result["profile"]["email"] == "alice.smith@test.com"
    assert result["profile"]["phone"] == "555-1234"
    assert result["account_info"]["id"] == 123
    assert result["account_info"]["is_active"] is True


@pytest.mark.asyncio
async def test_transformation_error_propagation():
    """Test that transformation errors are properly propagated."""
    data = {"age": "not_a_number", "count": "also_not_a_number"}
    rules = [
        TransformationRule(source_field="age", target_field="age", transformation="int"),
        TransformationRule(
            source_field="count", target_field="count", transformation="int"
        ),
    ]

    engine = TransformationEngine(rules)

    # Should raise ValueError on first failed transformation
    with pytest.raises(ValueError, match="Transformation failed"):
        await engine.apply(data)


@pytest.mark.asyncio
async def test_empty_transformation_list():
    """Test transformation engine with no rules."""
    data = {"name": "Alice", "age": 30}
    rules = []

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Data should be unchanged
    assert result == data


@pytest.mark.asyncio
async def test_transformation_with_none_values():
    """Test transformation handles None values correctly."""
    data = {"name": "Alice", "email": None, "age": 30}
    rules = [
        TransformationRule(source_field="name", target_field="user_name"),
        TransformationRule(source_field="email", target_field="user_email"),
        TransformationRule(source_field="age", target_field="user_age"),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Non-None values should be copied
    assert result["user_name"] == "Alice"
    assert result["user_age"] == 30
    # None value should not create target field
    assert "user_email" not in result


@pytest.mark.asyncio
async def test_bool_transformation_variants():
    """Test boolean transformation with various input types."""
    data = {
        "bool1": True,
        "bool2": False,
        "bool3": "true",
        "bool4": "false",
        "bool5": "1",
        "bool6": "0",
        "bool7": "yes",
        "bool8": "no",
        "bool9": 1,
        "bool10": 0,
    }
    rules = [
        TransformationRule(
            source_field=f"bool{i}",
            target_field=f"result{i}",
            transformation="bool",
        )
        for i in range(1, 11)
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Verify boolean conversions
    assert result["result1"] is True  # True
    assert result["result2"] is False  # False
    assert result["result3"] is True  # "true"
    assert result["result4"] is False  # "false"
    assert result["result5"] is True  # "1"
    assert result["result6"] is False  # "0"
    assert result["result7"] is True  # "yes"
    assert result["result8"] is False  # "no"
    assert result["result9"] is True  # 1
    assert result["result10"] is False  # 0


@pytest.mark.asyncio
async def test_transformation_field_overwrite():
    """Test that transformations can overwrite existing fields."""
    data = {"name": "alice", "email": "ALICE@TEST.COM"}
    rules = [
        TransformationRule(
            source_field="name", target_field="name", transformation="upper"
        ),
        TransformationRule(
            source_field="email", target_field="email", transformation="lower"
        ),
    ]

    engine = TransformationEngine(rules)
    result = await engine.apply(data)

    # Fields should be overwritten with transformed values
    assert result["name"] == "ALICE"
    assert result["email"] == "alice@test.com"
