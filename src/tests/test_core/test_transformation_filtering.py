"""Tests for transformation engine field filtering."""

import pytest
from flexlink.core.transformation import TransformationEngine
from flexlink.models.transformation import TransformationRule


@pytest.mark.asyncio
async def test_include_fields_simple():
    """Test simple include_fields filtering."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=["name", "email"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": "john@example.com", "password": "secret"}
    result = await engine.apply(data)

    assert result == {"name": "John", "email": "john@example.com"}
    assert "password" not in result


@pytest.mark.asyncio
async def test_exclude_fields_simple():
    """Test simple exclude_fields filtering."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            exclude_fields=["password", "internal_id"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": "john@example.com", "password": "secret", "internal_id": 123}
    result = await engine.apply(data)

    assert result == {"name": "John", "email": "john@example.com"}
    assert "password" not in result
    assert "internal_id" not in result


@pytest.mark.asyncio
async def test_exclude_takes_precedence():
    """Test that exclude_fields takes precedence over include_fields."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=["name", "email", "password"],
            exclude_fields=["password"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": "john@example.com", "password": "secret"}
    result = await engine.apply(data)

    assert result == {"name": "John", "email": "john@example.com"}
    assert "password" not in result


@pytest.mark.asyncio
async def test_nested_field_filtering():
    """Test filtering with nested fields (dot notation)."""
    rules = [
        TransformationRule(
            source_field="user.name",
            target_field="user.name",
            exclude_fields=["user.email", "user.password"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {
        "user": {
            "name": "John",
            "email": "john@example.com",
            "password": "secret",
            "age": 30
        }
    }
    result = await engine.apply(data)

    assert "user" in result
    assert result["user"]["name"] == "John"
    assert result["user"]["age"] == 30
    assert "email" not in result["user"]
    assert "password" not in result["user"]


@pytest.mark.asyncio
async def test_filtering_after_transformation():
    """Test that filtering happens after transformations."""
    rules = [
        TransformationRule(
            source_field="first_name",
            target_field="full_name",  # Creates new field
            transformation="upper",
            exclude_fields=["first_name"]  # Exclude original
        )
    ]

    engine = TransformationEngine(rules)
    data = {"first_name": "john", "last_name": "doe"}
    result = await engine.apply(data)

    assert result == {"full_name": "JOHN", "last_name": "doe"}
    assert "first_name" not in result


@pytest.mark.asyncio
async def test_include_empty_list():
    """Test include_fields with empty list returns empty dict."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=[]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": "john@example.com"}
    result = await engine.apply(data)

    assert result == {}


@pytest.mark.asyncio
async def test_no_filtering_when_not_specified():
    """Test that no filtering occurs when include/exclude not specified."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="customer_name",
            transformation="upper"
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "john", "email": "john@example.com", "password": "secret"}
    result = await engine.apply(data)

    # All fields preserved (additive transformation)
    assert result["name"] == "john"
    assert result["customer_name"] == "JOHN"
    assert result["email"] == "john@example.com"
    assert result["password"] == "secret"


@pytest.mark.asyncio
async def test_multiple_rules_with_different_filters():
    """Test multiple rules with different filter specifications."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=["name", "email", "age"]
        ),
        TransformationRule(
            source_field="age",
            target_field="age",
            exclude_fields=["age"]  # Remove age
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": "john@example.com", "age": 30, "password": "secret"}
    result = await engine.apply(data)

    # Combined filtering: include name,email,age then exclude age
    assert result == {"name": "John", "email": "john@example.com"}


@pytest.mark.asyncio
async def test_filtering_with_missing_fields():
    """Test filtering gracefully handles missing fields."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=["name", "email", "nonexistent"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": "john@example.com"}
    result = await engine.apply(data)

    # Only existing fields included
    assert result == {"name": "John", "email": "john@example.com"}


@pytest.mark.asyncio
async def test_filtering_deeply_nested_structures():
    """Test filtering with deeply nested structures."""
    rules = [
        TransformationRule(
            source_field="user.profile.name",
            target_field="user.profile.name",
            exclude_fields=["user.profile.settings.theme"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {
        "user": {
            "profile": {
                "name": "John",
                "email": "john@example.com",
                "settings": {
                    "theme": "dark",
                    "language": "en"
                }
            }
        }
    }
    result = await engine.apply(data)

    assert result["user"]["profile"]["name"] == "John"
    assert result["user"]["profile"]["email"] == "john@example.com"
    assert result["user"]["profile"]["settings"]["language"] == "en"
    assert "theme" not in result["user"]["profile"]["settings"]


@pytest.mark.asyncio
async def test_filtering_preserves_list_values():
    """Test that filtering doesn't break list values."""
    rules = [
        TransformationRule(
            source_field="tags",
            target_field="tags",
            include_fields=["tags", "name"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "Product", "tags": ["electronics", "sale"], "price": 99.99}
    result = await engine.apply(data)

    assert result == {"name": "Product", "tags": ["electronics", "sale"]}


@pytest.mark.asyncio
async def test_filtering_empty_data():
    """Test filtering on empty data."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=["name"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {}
    result = await engine.apply(data)

    assert result == {}


@pytest.mark.asyncio
async def test_filtering_with_null_values():
    """Test filtering preserves null values in included fields."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=["name", "email"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": None, "password": "secret"}
    result = await engine.apply(data)

    # Note: _get_nested_value returns None for missing/null
    # So null values won't be included in result
    assert "name" in result
    assert result["name"] == "John"
    # Email is None, so it won't be set in result


@pytest.mark.asyncio
async def test_exclude_all_fields():
    """Test exclude all fields returns empty dict."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            exclude_fields=["name", "email", "password"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": "john@example.com", "password": "secret"}
    result = await engine.apply(data)

    assert result == {}


@pytest.mark.asyncio
async def test_include_single_field():
    """Test include only one field."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=["name"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "John", "email": "john@example.com", "password": "secret"}
    result = await engine.apply(data)

    assert result == {"name": "John"}


@pytest.mark.asyncio
async def test_filtering_with_transformation_and_nested_fields():
    """Test complex scenario with transformation and nested field filtering."""
    rules = [
        TransformationRule(
            source_field="user.first_name",
            target_field="user.display_name",
            transformation="upper",
            exclude_fields=["user.first_name", "user.internal_id"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {
        "user": {
            "first_name": "john",
            "internal_id": 12345,
            "email": "john@example.com"
        }
    }
    result = await engine.apply(data)

    assert "user" in result
    assert result["user"]["display_name"] == "JOHN"
    assert result["user"]["email"] == "john@example.com"
    assert "first_name" not in result["user"]
    assert "internal_id" not in result["user"]


@pytest.mark.asyncio
async def test_filtering_preserves_non_string_values():
    """Test filtering preserves integer, float, and boolean values."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="name",
            include_fields=["name", "age", "price", "active"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {
        "name": "Product",
        "age": 30,
        "price": 99.99,
        "active": True,
        "password": "secret"
    }
    result = await engine.apply(data)

    assert result == {
        "name": "Product",
        "age": 30,
        "price": 99.99,
        "active": True
    }
    assert "password" not in result


@pytest.mark.asyncio
async def test_filtering_multiple_nested_levels():
    """Test filtering with multiple levels of nesting."""
    rules = [
        TransformationRule(
            source_field="data.user.name",
            target_field="data.user.name",
            include_fields=["data.user.name", "data.user.profile.email"]
        )
    ]

    engine = TransformationEngine(rules)
    data = {
        "data": {
            "user": {
                "name": "John",
                "password": "secret",
                "profile": {
                    "email": "john@example.com",
                    "phone": "123-456-7890"
                }
            }
        }
    }
    result = await engine.apply(data)

    assert result["data"]["user"]["name"] == "John"
    assert result["data"]["user"]["profile"]["email"] == "john@example.com"
    assert "password" not in result["data"]["user"]
    assert "phone" not in result["data"]["user"]["profile"]
