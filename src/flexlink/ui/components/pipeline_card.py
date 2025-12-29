"""Pipeline detail card component with Material Design 3 styling."""

from collections.abc import Callable

from nicegui import ui

from .status_badge import create_status_badge


def create_pipeline_card(
    pipeline_name: str,
    description: str,
    status: str | None = None,
    enabled: bool = True,
    schedule_info: str | None = None,
    tags: list[str] | None = None,
    on_run: Callable[[], None] | None = None,
    on_view: Callable[[], None] | None = None,
) -> ui.card:
    """
    Create a pipeline detail card with Material Design 3 styling.

    Args:
        pipeline_name: Name of the pipeline
        description: Pipeline description
        status: Current status (optional, for runs)
        enabled: Whether pipeline is enabled
        schedule_info: Schedule information text (e.g., "Every 5m", "0 */6 * * *")
        tags: List of tags for categorization
        on_run: Callback function when Run button is clicked
        on_view: Callback function when View Details button is clicked

    Returns:
        ui.card: NiceGUI card component with pipeline information
    """
    if tags is None:
        tags = []

    card = ui.card().classes("md3-card").style(
        "padding: 16px; "
        "border-radius: var(--md-sys-shape-corner-medium); "
        "box-shadow: var(--md-sys-elevation-level1); "
        "background-color: var(--md-sys-color-surface); "
        "color: var(--md-sys-color-on-surface); "
        "transition: box-shadow 0.2s;"
    )

    with card:
        # Header: Title and status
        with ui.row().classes("items-center justify-between w-full"):
            # Left: Title and enabled indicator
            with ui.row().classes("items-center gap-2"):
                ui.label(pipeline_name).classes("md3-title-large").style(
                    "font-weight: 500; color: var(--md-sys-color-on-surface);"
                )
                if not enabled:
                    ui.badge("Disabled").classes("md3-badge md3-badge-secondary")

            # Right: Status badge (if provided)
            if status:
                create_status_badge(status)

        # Description
        if description:
            ui.label(description).classes("md3-body-medium").style(
                "margin-top: 8px; color: var(--md-sys-color-on-surface-variant);"
            )

        # Schedule info and tags
        with ui.row().classes("items-center gap-4").style("margin-top: 12px;"):
            # Schedule icon + text
            if schedule_info:
                with ui.row().classes("items-center gap-1"):
                    ui.icon("schedule").classes("text-sm").style(
                        "font-size: 18px; color: var(--md-sys-color-on-surface-variant);"
                    )
                    ui.label(schedule_info).classes("md3-body-medium").style(
                        "color: var(--md-sys-color-on-surface-variant);"
                    )

            # Tags
            if tags:
                with ui.row().classes("items-center gap-1"):
                    for tag in tags:
                        ui.chip(tag).classes("md3-chip").style(
                            "background-color: var(--md-sys-color-surface-variant); "
                            "color: var(--md-sys-color-on-surface-variant); "
                            "border-radius: var(--md-sys-shape-corner-small); "
                            "font-size: var(--md-sys-typescale-label-small-size);"
                        )

        # Action buttons
        with ui.row().classes("items-center gap-2").style("margin-top: 16px;"):
            if on_view:
                ui.button("View Details", icon="info", on_click=on_view).props(
                    "flat"
                ).classes("md3-button-text")

            if on_run and enabled:
                ui.button("Run", icon="play_arrow", on_click=on_run).props("flat").classes(
                    "md3-button-filled"
                ).style(
                    "background-color: var(--md-sys-color-primary); "
                    "color: var(--md-sys-color-on-primary);"
                )

    # Add hover effect
    card.on(
        "mouseenter",
        lambda: card.style(add="box-shadow: var(--md-sys-elevation-level2);"),
    )
    card.on(
        "mouseleave",
        lambda: card.style(add="box-shadow: var(--md-sys-elevation-level1);"),
    )

    return card
