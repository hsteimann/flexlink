"""Tests for JSONata expression support in transformation engine."""

import pytest

from flexlink.core.transformation import TransformationEngine
from flexlink.models.transformation import TransformationRule


@pytest.mark.asyncio
async def test_jsonata_simple_expression():
    """Test simple JSONata expression."""
    rules = [
        TransformationRule(
            source_field="name",  # Ignored
            target_field="upperName",
            expression="$uppercase(name)",
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "john"}
    result = await engine.apply(data)

    assert result["upperName"] == "JOHN"
    assert result["name"] == "john"  # Original preserved


@pytest.mark.asyncio
async def test_jsonata_string_concatenation():
    """Test string concatenation in JSONata."""
    rules = [
        TransformationRule(
            source_field="firstName",  # Ignored
            target_field="fullName",
            expression='$uppercase(firstName & " " & lastName)',
        )
    ]

    engine = TransformationEngine(rules)
    data = {"firstName": "john", "lastName": "doe"}
    result = await engine.apply(data)

    assert result["fullName"] == "JOHN DOE"


@pytest.mark.asyncio
async def test_jsonata_array_sum():
    """Test array aggregation with JSONata."""
    rules = [
        TransformationRule(
            source_field="items",  # Ignored
            target_field="total",
            expression="$sum(items.price)",
        )
    ]

    engine = TransformationEngine(rules)
    data = {"items": [{"price": 10}, {"price": 20}, {"price": 30}]}
    result = await engine.apply(data)

    assert result["total"] == 60


@pytest.mark.asyncio
async def test_jsonata_array_filter():
    """Test array filtering with JSONata."""
    rules = [
        TransformationRule(
            source_field="items",  # Ignored
            target_field="expensive",
            expression="$filter(items, function($v) { $v.price > 20 })",
        )
    ]

    engine = TransformationEngine(rules)
    data = {"items": [{"price": 10}, {"price": 25}, {"price": 30}]}
    result = await engine.apply(data)

    assert len(result["expensive"]) == 2
    assert result["expensive"][0]["price"] == 25
    assert result["expensive"][1]["price"] == 30


@pytest.mark.asyncio
async def test_jsonata_conditional():
    """Test conditional logic with JSONata."""
    rules = [
        TransformationRule(
            source_field="status",  # Ignored
            target_field="message",
            expression='active ? "Account is active" : "Account is inactive"',
        )
    ]

    engine = TransformationEngine(rules)

    # Test true condition
    data = {"active": True}
    result = await engine.apply(data)
    assert result["message"] == "Account is active"

    # Test false condition
    data = {"active": False}
    result = await engine.apply(data)
    assert result["message"] == "Account is inactive"


@pytest.mark.asyncio
async def test_jsonata_nested_object_creation():
    """Test creating nested objects with JSONata."""
    rules = [
        TransformationRule(
            source_field="user",  # Ignored
            target_field="profile",
            expression='{"fullName": $uppercase(firstName & " " & lastName), "isAdult": age >= 18}',
        )
    ]

    engine = TransformationEngine(rules)
    data = {"firstName": "john", "lastName": "doe", "age": 25}
    result = await engine.apply(data)

    assert result["profile"]["fullName"] == "JOHN DOE"
    assert result["profile"]["isAdult"] is True


@pytest.mark.asyncio
async def test_jsonata_array_map():
    """Test array mapping with JSONata."""
    rules = [
        TransformationRule(
            source_field="items",  # Ignored
            target_field="prices",
            expression="items.price",
        )
    ]

    engine = TransformationEngine(rules)
    data = {"items": [{"name": "A", "price": 10}, {"name": "B", "price": 20}]}
    result = await engine.apply(data)

    assert result["prices"] == [10, 20]


@pytest.mark.asyncio
async def test_jsonata_takes_precedence_over_transformation():
    """Test that expression takes precedence when both specified."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="output",
            transformation="lower",  # Should be ignored
            expression="$uppercase(name)",  # This should win
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "john"}
    result = await engine.apply(data)

    # Expression result, not transformation
    assert result["output"] == "JOHN"


@pytest.mark.asyncio
async def test_jsonata_invalid_expression_raises_error():
    """Test that invalid JSONata expression raises ValueError."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="output",
            expression="invalid {{ syntax",  # Invalid
        )
    ]

    engine = TransformationEngine(rules)
    data = {"name": "john"}

    with pytest.raises(ValueError, match="Invalid JSONata expression"):
        await engine.apply(data)


@pytest.mark.asyncio
async def test_jsonata_evaluation_error_graceful():
    """Test that evaluation errors with missing fields are handled gracefully."""
    rules = [
        TransformationRule(
            source_field="value",
            target_field="result",
            expression="$sum(nonexistent.field)",  # Field doesn't exist
        )
    ]

    engine = TransformationEngine(rules)
    data = {"value": 123}

    # Should handle gracefully (JSONata returns null/undefined)
    result = await engine.apply(data)
    # Result may not have the target field if expression returned None
    assert "value" in result


@pytest.mark.asyncio
async def test_jsonata_expression_caching():
    """Test that expressions are cached for performance."""
    from flexlink.core.transformation import _expression_cache

    # Clear cache
    _expression_cache.clear()

    rules = [
        TransformationRule(
            source_field="name", target_field="upper1", expression="$uppercase(name)"
        )
    ]

    engine = TransformationEngine(rules)

    # First evaluation - should compile and cache
    data = {"name": "john"}
    await engine.apply(data)

    assert len(_expression_cache) == 1
    assert "$uppercase(name)" in _expression_cache

    # Second evaluation - should use cache
    data = {"name": "jane"}
    await engine.apply(data)

    # Still only one cached expression
    assert len(_expression_cache) == 1


@pytest.mark.asyncio
async def test_jsonata_with_default_value():
    """Test that expression works when field exists."""
    rules = [
        TransformationRule(
            source_field="name",
            target_field="greeting",
            expression='$uppercase("Hello " & name)',
            default_value="Guest",  # Should be ignored when expression present
        )
    ]

    engine = TransformationEngine(rules)

    # When field exists, expression uses it
    data = {"name": "john"}
    result = await engine.apply(data)
    assert result["greeting"] == "HELLO JOHN"


@pytest.mark.asyncio
async def test_jsonata_multiple_expressions():
    """Test multiple JSONata expressions in same transformation."""
    rules = [
        TransformationRule(
            source_field="items", target_field="total", expression="$sum(items.price)"
        ),
        TransformationRule(
            source_field="items", target_field="count", expression="$count(items)"
        ),
        TransformationRule(
            source_field="items",
            target_field="avgPrice",
            expression="$sum(items.price) / $count(items)",
        ),
    ]

    engine = TransformationEngine(rules)
    data = {"items": [{"price": 10}, {"price": 20}, {"price": 30}]}
    result = await engine.apply(data)

    assert result["total"] == 60
    assert result["count"] == 3
    assert result["avgPrice"] == 20


@pytest.mark.asyncio
async def test_jsonata_with_filtering():
    """Test JSONata expressions combined with field filtering."""
    rules = [
        TransformationRule(
            source_field="user",
            target_field="displayName",
            expression='$uppercase(firstName & " " & lastName)',
            exclude_fields=["firstName", "lastName"],  # Remove originals
        )
    ]

    engine = TransformationEngine(rules)
    data = {"firstName": "john", "lastName": "doe", "email": "john@example.com"}
    result = await engine.apply(data)

    assert result["displayName"] == "JOHN DOE"
    assert "firstName" not in result
    assert "lastName" not in result
    assert result["email"] == "john@example.com"
