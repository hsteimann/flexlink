"""Integration request and response models."""

from typing import Any

from pydantic import BaseModel, Field


class IntegrationRequest(BaseModel):
    """Standardized integration request."""

    route: str = Field(..., description="Target route/path")
    method: str = Field(..., description="HTTP method (GET, POST, PUT, DELETE, etc.)")
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Request headers"
    )
    body: dict[str, Any] | None = Field(
        default=None,
        description="Request body data"
    )
    query_params: dict[str, str] = Field(
        default_factory=dict,
        description="Query parameters"
    )


class IntegrationResponse(BaseModel):
    """Standardized integration response."""

    status_code: int = Field(..., description="HTTP status code")
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Response headers"
    )
    body: dict[str, Any] | list[Any] | None = Field(
        default=None,
        description="Response body data (dict or list)"
    )
    error: str | None = Field(
        default=None,
        description="Error message if request failed"
    )
