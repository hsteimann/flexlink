"""Webhook connector configuration models."""

from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class WebhookAuthType(str, Enum):
    """Webhook authentication types."""
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    HMAC_SIGNATURE = "hmac_signature"


class WebhookConfig(BaseModel):
    """Webhook connector configuration."""

    webhook_url: HttpUrl = Field(..., description="Target webhook URL")

    auth_type: WebhookAuthType = Field(
        default=WebhookAuthType.NONE,
        description="Authentication method"
    )

    auth_credentials: dict[str, str] = Field(
        default_factory=dict,
        description="Auth credentials (token, api_key, secret, etc.)"
    )

    signature_enabled: bool = Field(
        default=False,
        description="Enable HMAC-SHA256 signature generation"
    )

    signature_secret: str | None = Field(
        default=None,
        description="Secret key for HMAC signature"
    )

    signature_header: str = Field(
        default="X-Webhook-Signature",
        description="Header name for signature"
    )

    timestamp_header: str = Field(
        default="X-Webhook-Timestamp",
        description="Header name for timestamp"
    )

    custom_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional headers to include"
    )

    max_retry_attempts: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed deliveries"
    )

    retry_backoff_factor: float = Field(
        default=2.0,
        ge=1.0,
        le=5.0,
        description="Exponential backoff multiplier"
    )

    timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=120,
        description="Request timeout in seconds"
    )


class WebhookDeliveryResult(BaseModel):
    """Result of webhook delivery attempt."""

    success: bool = Field(..., description="Whether delivery succeeded")
    status_code: int | None = Field(default=None, description="HTTP status code")
    attempts: int = Field(default=1, description="Number of delivery attempts")
    duration_ms: float = Field(default=0.0, description="Total duration in milliseconds")
    error: str | None = Field(default=None, description="Error message if failed")
    response_body: dict | str | None = Field(default=None, description="Response from webhook")
