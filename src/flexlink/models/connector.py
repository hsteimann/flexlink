"""Connector configuration models."""


from pydantic import BaseModel, Field


class AuthConfig(BaseModel):
    """Authentication configuration for connectors."""

    type: str = Field(
        ...,
        description="Auth type: none, basic, bearer, oauth2, api_key"
    )
    credentials: dict[str, str] = Field(
        default_factory=dict,
        description="Authentication credentials (tokens, keys, etc.)"
    )


class ConnectorConfig(BaseModel):
    """Connector configuration loaded from YAML."""

    name: str = Field(..., description="Unique connector identifier")
    type: str = Field(..., description="Connector type: rest, soap, graphql, file, etc.")
    base_url: str = Field(..., description="Base URL for target system")
    auth: AuthConfig = Field(
        default_factory=lambda: AuthConfig(type="none"),
        description="Authentication configuration"
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="Default headers for requests"
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts on failure"
    )
    enabled: bool = Field(
        default=True,
        description="Whether connector is active"
    )
