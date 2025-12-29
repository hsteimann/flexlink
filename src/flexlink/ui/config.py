"""UI configuration management."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class UISettings(BaseSettings):
    """UI-specific settings."""

    api_base_url: str = Field(
        default="http://localhost:8000",
        description="Base URL for FlexLink API"
    )
    refresh_interval_seconds: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Auto-refresh interval for monitoring pages"
    )
    log_page_size: int = Field(
        default=100,
        ge=10,
        le=1000,
        description="Number of log entries to display per page"
    )
    history_page_size: int = Field(
        default=20,
        ge=10,
        le=100,
        description="Number of historical runs to display per page"
    )
    theme: Literal["light", "dark"] = Field(
        default="dark",
        description="UI theme (light or dark)"
    )


# Global UI settings instance
ui_settings = UISettings()
