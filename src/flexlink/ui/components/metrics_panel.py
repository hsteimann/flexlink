"""Metrics panel component with Material Design 3 styling."""

from nicegui import ui

from flexlink.models.pipeline import ExecutionMetadata, StepResult


def create_metrics_panel(
    metadata: ExecutionMetadata,
    duration_seconds: float | None = None,
    step_results: list[StepResult] | None = None,
) -> ui.card:
    """
    Create execution metrics display panel with Material Design 3 styling.

    Displays:
    - Records extracted, transformed, loaded
    - Validation errors
    - Execution duration
    - Step-by-step breakdown (if step_results provided)

    Args:
        metadata: Execution metadata with record counts
        duration_seconds: Total execution duration
        step_results: List of step execution results (optional)

    Returns:
        ui.card: Card containing metrics display
    """
    card = ui.card().classes("md3-card").style(
        "padding: 16px; "
        "border-radius: var(--md-sys-shape-corner-medium); "
        "box-shadow: var(--md-sys-elevation-level1); "
        "background-color: var(--md-sys-color-surface);"
    )

    with card:
        # Header
        ui.label("Execution Metrics").classes("md3-headline-medium").style(
            "font-weight: 500; color: var(--md-sys-color-on-surface); margin-bottom: 16px;"
        )

        # Overview metrics in grid
        with ui.grid(columns=2).classes("w-full gap-4"):
            # Records Extracted
            _create_metric_item(
                icon="download",
                label="Extracted",
                value=str(metadata.records_extracted),
                color="var(--md-sys-color-primary)",
            )

            # Records Transformed
            _create_metric_item(
                icon="transform",
                label="Transformed",
                value=str(metadata.records_transformed),
                color="var(--md-sys-color-secondary)",
            )

            # Records Loaded
            _create_metric_item(
                icon="upload",
                label="Loaded",
                value=str(metadata.records_loaded),
                color="var(--md-sys-color-tertiary)",
            )

            # Validation Errors
            error_color = (
                "var(--md-sys-color-error)"
                if metadata.validation_errors > 0
                else "var(--md-sys-color-success)"
            )
            _create_metric_item(
                icon="error" if metadata.validation_errors > 0 else "check_circle",
                label="Validation Errors",
                value=str(metadata.validation_errors),
                color=error_color,
            )

        # Duration (if provided)
        if duration_seconds is not None:
            ui.separator().style("margin: 16px 0;")
            with ui.row().classes("items-center gap-2"):
                ui.icon("schedule").style("font-size: 24px; color: var(--md-sys-color-primary);")
                ui.label("Duration:").classes("md3-body-medium").style(
                    "color: var(--md-sys-color-on-surface-variant);"
                )
                ui.label(_format_duration(duration_seconds)).classes("md3-title-medium").style(
                    "color: var(--md-sys-color-on-surface); font-weight: 500;"
                )

        # Step breakdown (if provided)
        if step_results:
            ui.separator().style("margin: 16px 0;")
            ui.label("Step Details").classes("md3-title-medium").style(
                "font-weight: 500; color: var(--md-sys-color-on-surface); margin-bottom: 12px;"
            )

            for step in step_results:
                _create_step_item(step)

    return card


def _create_metric_item(icon: str, label: str, value: str, color: str) -> None:
    """
    Create a single metric item with icon, label, and value.

    Args:
        icon: Material Symbol icon name
        label: Metric label
        value: Metric value (as string)
        color: Color for icon and value
    """
    with ui.column().classes("items-start gap-1").style(
        "padding: 12px; "
        "background-color: var(--md-sys-color-surface-variant); "
        "border-radius: var(--md-sys-shape-corner-small);"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon).style(f"font-size: 24px; color: {color};")
            ui.label(label).classes("md3-body-medium").style(
                "color: var(--md-sys-color-on-surface-variant);"
            )
        ui.label(value).classes("md3-headline-medium").style(
            f"color: {color}; font-weight: 600;"
        )


def _create_step_item(step: StepResult) -> None:
    """
    Create a step result item showing status, duration, and records.

    Args:
        step: Step execution result
    """
    # Determine status color
    status_colors = {
        "success": "var(--md-sys-color-success)",
        "error": "var(--md-sys-color-error)",
        "skipped": "var(--md-sys-color-outline)",
    }
    status_icons = {
        "success": "check_circle",
        "error": "error",
        "skipped": "remove_circle",
    }

    status_lower = step.status.lower()
    color = status_colors.get(status_lower, "var(--md-sys-color-outline)")
    icon = status_icons.get(status_lower, "help")

    with ui.row().classes("items-center justify-between w-full").style(
        "padding: 8px; "
        "border-left: 3px solid; "
        f"border-color: {color}; "
        "background-color: var(--md-sys-color-surface-variant); "
        "border-radius: var(--md-sys-shape-corner-small); "
        "margin-bottom: 8px;"
    ):
        # Left: Step name and status
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon).style(f"font-size: 20px; color: {color};")
            ui.label(step.step_name).classes("md3-body-medium").style(
                "color: var(--md-sys-color-on-surface); font-weight: 500;"
            )

        # Right: Duration and records
        with ui.row().classes("items-center gap-4"):
            # Records processed
            if step.records_processed > 0:
                with ui.row().classes("items-center gap-1"):
                    ui.icon("database").style(
                        "font-size: 16px; color: var(--md-sys-color-on-surface-variant);"
                    )
                    ui.label(str(step.records_processed)).classes("md3-label-small").style(
                        "color: var(--md-sys-color-on-surface-variant);"
                    )

            # Duration
            duration_style = (
                "color: var(--md-sys-color-on-surface-variant); "
                "font-family: 'Roboto Mono', monospace;"
            )
            ui.label(_format_duration(step.duration_seconds)).classes(
                "md3-label-small"
            ).style(duration_style)

        # Error message (if present)
        if step.error_message:
            with ui.row().classes("w-full").style("margin-top: 8px;"):
                ui.label(step.error_message).classes("md3-body-small").style(
                    "color: var(--md-sys-color-error); "
                    "padding: 8px; "
                    "background-color: var(--md-sys-color-error-container); "
                    "border-radius: var(--md-sys-shape-corner-extra-small);"
                )


def _format_duration(seconds: float) -> str:
    """
    Format duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "2m 30s", "45.2s", "1h 15m")
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
