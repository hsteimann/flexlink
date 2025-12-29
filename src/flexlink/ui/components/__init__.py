"""UI components for FlexLink monitoring dashboard.

This package contains reusable Material Design 3 components built with NiceGUI:
- navigation: Top navigation bar with theme toggle
- status_badge: Status indicators with M3 colors
- pipeline_card: Pipeline detail cards
- log_viewer: Scrollable log viewer with color-coded levels
- metrics_panel: Execution metrics display
"""

from .log_viewer import create_log_viewer
from .metrics_panel import create_metrics_panel
from .navigation import create_navigation
from .pipeline_card import create_pipeline_card
from .status_badge import create_status_badge

__all__ = [
    "create_navigation",
    "create_status_badge",
    "create_pipeline_card",
    "create_log_viewer",
    "create_metrics_panel",
]
