"""Data transformation models."""


from pydantic import BaseModel, Field


class TransformationRule(BaseModel):
    """Data transformation rule for field mapping and transformation."""

    source_field: str = Field(..., description="Source field path (supports dot notation)")
    target_field: str = Field(..., description="Target field path (supports dot notation)")
    transformation: str | None = Field(
        default=None,
        description="Transformation function: upper, lower, strip, int, float, date_format, etc."
    )
    default_value: str | None = Field(
        default=None,
        description="Default value if source field is missing"
    )

    # JSONata expression for complex transformations
    expression: str | None = Field(
        default=None,
        description="JSONata expression for complex transformations. Takes precedence over 'transformation' if both specified."
    )

    # Field filtering
    include_fields: list[str] | None = Field(
        default=None,
        description="Only keep these fields in output (supports dot notation). Applied after transformations."
    )
    exclude_fields: list[str] | None = Field(
        default=None,
        description="Remove these fields from output (supports dot notation). Takes precedence over include_fields."
    )


class RouteConfig(BaseModel):
    """Route configuration mapping incoming requests to connectors."""

    path: str = Field(..., description="Incoming request path pattern")
    method: str = Field(default="POST", description="HTTP method")
    connector: str = Field(..., description="Target connector name")
    target_path: str = Field(..., description="Target system path")
    transformations: list[TransformationRule] = Field(
        default_factory=list,
        description="Request transformations applied before sending to connector"
    )
    response_transformations: list[TransformationRule] = Field(
        default_factory=list,
        description="Response transformations applied before returning to client"
    )

    # YAML Mapping Reference (Week 2 - Phase 2)
    mapping_ref: str | None = Field(
        default=None,
        description="Reference to YAML mapping config (config/mappings/{name}.yaml)"
    )
