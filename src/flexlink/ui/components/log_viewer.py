"""Log viewer component with Material Design 3 styling."""

from nicegui import ui

from flexlink.models.logs import LogEntry


def create_log_viewer(
    logs: list[LogEntry],
    max_height: str = "400px",
    show_timestamps: bool = True,
) -> ui.element:
    """
    Create a scrollable log viewer with Material Design 3 styling.

    Features:
    - Color-coded log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - Monospace font for readability
    - Auto-scroll to bottom
    - Material Design 3 list design

    Args:
        logs: List of LogEntry objects
        max_height: Maximum height of log viewer (default: 400px)
        show_timestamps: Whether to show timestamps (default: True)

    Returns:
        ui.element: Container with log viewer
    """
    # Log level color mapping using M3 colors
    level_colors = {
        "DEBUG": "var(--md-sys-color-outline)",
        "INFO": "var(--md-sys-color-primary)",
        "WARNING": "var(--md-sys-color-warning)",
        "ERROR": "var(--md-sys-color-error)",
        "CRITICAL": "var(--md-sys-color-error)",
    }

    # Log level icon mapping
    level_icons = {
        "DEBUG": "bug_report",
        "INFO": "info",
        "WARNING": "warning",
        "ERROR": "error",
        "CRITICAL": "emergency",
    }

    container = ui.column().classes("w-full").style(
        f"max-height: {max_height}; "
        "overflow-y: auto; "
        "background-color: var(--md-sys-color-surface); "
        "border: 1px solid var(--md-sys-color-outline-variant); "
        "border-radius: var(--md-sys-shape-corner-medium); "
        "padding: 8px;"
    )

    with container:
        if not logs:
            # Empty state
            with ui.row().classes("items-center justify-center").style(
                "padding: 40px; color: var(--md-sys-color-on-surface-variant);"
            ):
                ui.icon("description").style("font-size: 48px; opacity: 0.5;")
                ui.label("No logs available").classes("md3-body-medium")
        else:
            # Render logs
            for log in logs:
                level_upper = log.level.upper()
                color = level_colors.get(level_upper, "var(--md-sys-color-on-surface)")
                icon = level_icons.get(level_upper, "article")

                with ui.row().classes("items-start gap-2 w-full").style(
                    "padding: 8px; "
                    "border-bottom: 1px solid var(--md-sys-color-outline-variant);"
                ):
                    # Icon
                    ui.icon(icon).style(f"font-size: 18px; color: {color}; margin-top: 2px;")

                    # Log content
                    with ui.column().classes("flex-grow gap-0"):
                        # Timestamp and level
                        if show_timestamps:
                            with ui.row().classes("items-center gap-2"):
                                ui.label(log.timestamp).classes("md3-label-small").style(
                                    "color: var(--md-sys-color-on-surface-variant); "
                                    "font-family: 'Roboto Mono', monospace;"
                                )
                                ui.label(f"[{log.level}]").classes("md3-label-small").style(
                                    f"color: {color}; font-weight: 600; "
                                    "font-family: 'Roboto Mono', monospace;"
                                )
                                if log.logger:
                                    ui.label(log.logger).classes("md3-label-small").style(
                                        "color: var(--md-sys-color-on-surface-variant); "
                                        "font-family: 'Roboto Mono', monospace;"
                                    )

                        # Message
                        ui.label(log.message).classes("md3-body-medium").style(
                            "color: var(--md-sys-color-on-surface); "
                            "font-family: 'Roboto Mono', monospace; "
                            "white-space: pre-wrap; "
                            "word-break: break-word;"
                        )

    # Auto-scroll to bottom
    ui.run_javascript(
        """
        const container = document.querySelector('.overflow-y-auto');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
        """
    )

    return container


def create_log_viewer_card(
    title: str,
    logs: list[LogEntry],
    max_height: str = "400px",
    show_timestamps: bool = True,
) -> ui.card:
    """
    Create a log viewer wrapped in a Material Design 3 card.

    Args:
        title: Card title
        logs: List of LogEntry objects
        max_height: Maximum height of log viewer (default: 400px)
        show_timestamps: Whether to show timestamps (default: True)

    Returns:
        ui.card: Card containing the log viewer
    """
    card = ui.card().classes("md3-card").style(
        "padding: 16px; "
        "border-radius: var(--md-sys-shape-corner-medium); "
        "box-shadow: var(--md-sys-elevation-level1); "
        "background-color: var(--md-sys-color-surface);"
    )

    with card:
        # Header
        with ui.row().classes("items-center justify-between w-full").style(
            "margin-bottom: 16px;"
        ):
            ui.label(title).classes("md3-headline-medium").style(
                "font-weight: 500; color: var(--md-sys-color-on-surface);"
            )
            ui.badge(str(len(logs))).classes("md3-badge md3-badge-secondary")

        # Log viewer
        create_log_viewer(logs, max_height=max_height, show_timestamps=show_timestamps)

    return card
