"""FlexLink Web UI module.

This module provides a web-based user interface for monitoring and configuring
FlexLink pipelines using NiceGUI framework with Material Design 3 styling.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flexlink.ui.app import create_ui_app

__all__ = ["create_ui_app"]


def __getattr__(name: str) -> object:
    """Lazy load UI app to avoid circular imports."""
    if name == "create_ui_app":
        from flexlink.ui.app import create_ui_app
        return create_ui_app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
