"""Mapping configuration models for YAML-based transformations."""

from typing import Any
from pydantic import BaseModel, Field

from flexlink.models.transformation import TransformationRule
from flexlink.models.validation import ValidationConfig


class ConditionalMapping(BaseModel):
    """Conditional mapping rule with if-then-else logic."""

    condition: str = Field(
        ...,
        description="Condition expression (simple for MVP: 'field == value')"
    )
    then_value: Any = Field(..., description="Value to use if condition is true")
    else_value: Any | None = Field(default=None, description="Value to use if condition is false")


class MappingRule(BaseModel):
    """
    Enhanced mapping rule supporting transformations and conditions.

    Extends TransformationRule with conditional logic and multi-field support.
    """

    source_field: str | None = Field(
        default=None,
        description="Source field path (None for computed fields)"
    )
    target_field: str = Field(..., description="Target field path")

    # Transformation
    transformation: str | None = Field(
        default=None,
        description="Transformation function (upper, lower, int, float, etc.)"
    )

    # Default value
    default_value: Any | None = Field(
        default=None,
        description="Default value if source field is missing"
    )

    # Conditional mapping (Week 2 - simple conditions only)
    conditional: ConditionalMapping | None = Field(
        default=None,
        description="Conditional mapping logic (if-then-else)"
    )

    # Multi-field derived fields (Week 2 - simple concatenation)
    concat_fields: list[str] | None = Field(
        default=None,
        description="List of fields to concatenate (e.g., ['firstName', 'lastName'])"
    )
    concat_separator: str = Field(
        default=" ",
        description="Separator for concatenation (default: space)"
    )


class MappingConfig(BaseModel):
    """
    Complete mapping configuration loaded from YAML.

    Combines transformation rules and validation rules.
    """

    name: str = Field(..., description="Mapping configuration name (must match filename)")
    description: str | None = Field(default=None, description="Description of this mapping")

    # Transformation mappings
    mappings: list[MappingRule] = Field(
        default_factory=list,
        description="List of field mapping rules"
    )

    # Validation rules
    validation: ValidationConfig | None = Field(
        default=None,
        description="Validation configuration for transformed data"
    )


# Helper to convert MappingRule to TransformationRule for existing engine
def mapping_rule_to_transformation_rule(mapping: MappingRule) -> TransformationRule | None:
    """
    Convert MappingRule to TransformationRule for compatibility with existing engine.

    Note: This only handles simple field mappings, not conditionals or concatenation.
    """
    if mapping.source_field is None:
        # Computed field - requires special handling
        return None

    return TransformationRule(
        source_field=mapping.source_field,
        target_field=mapping.target_field,
        transformation=mapping.transformation,
        default_value=mapping.default_value
    )
