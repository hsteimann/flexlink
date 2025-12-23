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


class RouteConfig(BaseModel):
    """Route configuration mapping incoming requests to connectors."""

    path: str = Field(..., description="Incoming request path pattern")
    method: str = Field(default="POST", description="HTTP method")
    connector: str = Field(..., description="Target connector name")
    target_path: str = Field(..., description="Target system path")
    transformations: list[TransformationRule] = Field(
        default_factory=list,
        description="Request transformation rules"
    )
