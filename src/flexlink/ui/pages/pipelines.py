"""Pipeline list and detail view page."""

import logging
from typing import Any

from nicegui import ui

from ..api_client import FlexLinkAPIClient, get_api_base_url
from ..components.navigation import create_navigation
from ..components.status_badge import create_status_badge as _create_status_badge

logger = logging.getLogger(__name__)


def create_status_badge(status: str, enabled: bool = True) -> ui.badge:
    """
    Create a status badge element.

    Args:
        status: Status string
        enabled: Whether pipeline is enabled

    Returns:
        Status badge UI element
    """
    badge_status = "active" if enabled else "disabled"
    return _create_status_badge(badge_status)


@ui.page('/pipelines')
async def pipelines_page() -> None:
    """
    Pipeline list and detail view page.

    Features:
    - Data table showing all pipelines
    - Click to expand configuration
    - Run pipeline button
    - Auto-refresh every 5 seconds
    """
    # Header with navigation
    create_navigation()

    # Main content with consistent layout
    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-4"):
        # Header
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Pipelines").classes("text-3xl font-bold")
            ui.button(
                "Refresh",
                icon="refresh",
                on_click=lambda: refresh_pipelines()
            ).props("flat color=primary")

        # Loading indicator
        loading = ui.spinner(size="lg")
        loading.visible = False

        # Error display
        error_label = ui.label("").classes("text-red-500")
        error_label.visible = False

        # Pipeline cards container
        pipelines_container = ui.column().classes("w-full gap-4")

        # Track which pipelines are expanded (to preserve state during refresh)
        expanded_pipelines: set[str] = set()

        async def load_pipelines() -> None:
            """Load and display pipelines."""
            loading.visible = True
            error_label.visible = False
            pipelines_container.clear()

            try:
                async with FlexLinkAPIClient(get_api_base_url()) as client:
                    response = await client.list_pipelines()
                    pipelines_list = response.get("pipelines", [])

                    if not pipelines_list:
                        with pipelines_container:
                            ui.label("No pipelines found").classes("text-gray-500 text-center p-8")
                        return

                    # Create pipeline cards
                    for pipeline_data in pipelines_list:
                        await create_pipeline_row(pipeline_data, pipelines_container)

            except Exception as e:
                logger.error(f"Failed to load pipelines: {e}")
                error_label.text = f"Error loading pipelines: {str(e)}"
                error_label.visible = True
            finally:
                loading.visible = False

        async def create_pipeline_row(pipeline_data: dict[str, Any], container: ui.column) -> None:
            """
            Create a pipeline row with expandable details.

            Args:
                pipeline_data: Pipeline data
                container: Container to add row to
            """
            with container:
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full items-center justify-between p-2"):
                        # Left side: Name and status
                        with ui.column().classes("gap-1"):
                            with ui.row().classes("items-center gap-2"):
                                ui.label(pipeline_data.get("name", "Unknown")).classes(
                                    "text-xl font-semibold"
                                )
                                create_status_badge(
                                    "active", pipeline_data.get("enabled", True)
                                )

                            if pipeline_data.get("description"):
                                ui.label(pipeline_data["description"]).classes(
                                    "text-sm text-gray-500"
                                )

                            # Tags
                            if pipeline_data.get("tags"):
                                with ui.row().classes("gap-1 mt-1"):
                                    for tag in pipeline_data["tags"]:
                                        ui.badge(tag, color="blue").props("outline")

                            # Schedule info
                            schedule = pipeline_data.get("schedule")
                            if schedule and schedule.get("enabled"):
                                schedule_text = schedule.get("expression", "Scheduled")
                                with ui.row().classes("items-center gap-1 mt-1"):
                                    ui.icon("schedule").classes("text-sm")
                                    ui.label(schedule_text).classes("text-sm text-gray-600")

                        # Right side: Actions
                        # Capture pipeline_name in closure to avoid NiceGUI click event override
                        pipeline_name_str = pipeline_data.get("name", "")

                        def make_toggle_handler(data: dict[str, Any]) -> Any:
                            """Create toggle handler with captured data."""
                            async def handler() -> None:
                                await toggle_details(data)
                            return handler

                        def make_run_handler(name: str) -> Any:
                            """Create run handler with captured pipeline name."""
                            async def handler() -> None:
                                await run_pipeline(name)
                            return handler

                        with ui.row().classes("gap-2"):
                            # Expand button (not used, but kept for future)
                            ui.button(
                                icon="expand_more",
                                on_click=make_toggle_handler(pipeline_data)
                            ).props("flat round")

                            # Run button
                            ui.button(
                                "Run",
                                icon="play_arrow",
                                on_click=make_run_handler(pipeline_name_str)
                            ).props("color=primary")

                    # Expandable details section
                    # Restore expansion state if it was previously expanded
                    pipeline_name = pipeline_data.get("name", "")
                    with ui.expansion().classes("w-full") as expansion:
                        # Restore previous expansion state
                        expansion.value = pipeline_name in expanded_pipelines

                        with ui.column().classes("w-full p-4 gap-4"):
                            ui.label("Configuration").classes("text-lg font-semibold")

                            # Load detailed configuration
                            config_container = ui.column().classes("w-full")

                            async def load_config() -> None:
                                """Load detailed pipeline configuration."""
                                try:
                                    api_url = get_api_base_url()
                                    async with FlexLinkAPIClient(api_url) as client:
                                        config = await client.get_pipeline(pipeline_name)

                                        with config_container:
                                            config_container.clear()

                                            # Display configuration as formatted JSON
                                            card_class = (
                                                "w-full bg-gray-100 dark:bg-gray-800"
                                            )
                                            with ui.card().classes(card_class):
                                                ui.json_editor({
                                                    "content": {"json": config}
                                                }).classes("w-full")

                                except Exception as e:
                                    logger.error(f"Failed to load config: {e}")
                                    with config_container:
                                        err_msg = (
                                            f"Error loading configuration: "
                                            f"{str(e)}"
                                        )
                                        ui.label(err_msg).classes("text-red-500")

                            # Track expansion state and load config when expanded
                            async def on_expand(e: Any) -> None:
                                if e.value:
                                    # Add to expanded set and load config
                                    expanded_pipelines.add(pipeline_name)
                                    await load_config()
                                else:
                                    # Remove from expanded set
                                    expanded_pipelines.discard(pipeline_name)

                            expansion.on_value_change(on_expand)

                            # Load config immediately if already expanded
                            if expansion.value:
                                await load_config()

        async def refresh_pipelines() -> None:
            """Refresh the pipelines list."""
            await load_pipelines()

        async def toggle_details(_pipeline_data: dict[str, Any]) -> None:
            """
            Toggle pipeline details visibility.

            Note: Currently not used as expansion is handled by NiceGUI component.
            Kept for future enhancement.
            """
            # This is handled by the expansion component
            pass

        async def run_pipeline(pipeline_name: str) -> None:
            """
            Execute a pipeline.

            Args:
                pipeline_name: Name of pipeline to run
            """
            try:
                async with FlexLinkAPIClient(get_api_base_url()) as client:
                    result = await client.execute_pipeline(
                        pipeline_name, background=True
                    )
                    run_id = result.get("run_id")

                    if run_id:
                        ui.notify(
                            f"Pipeline '{pipeline_name}' started (Run ID: {run_id})",
                            type="positive",
                            close_button=True,
                            timeout=5000
                        )

                        # Navigate to monitoring page
                        ui.navigate.to(f"monitoring/{run_id}")
                    else:
                        ui.notify(
                            f"Pipeline '{pipeline_name}' started but no run ID returned",
                            type="warning"
                        )

            except Exception as e:
                logger.error(f"Failed to run pipeline {pipeline_name}: {e}")
                ui.notify(
                    f"Error running pipeline: {str(e)}",
                    type="negative",
                    close_button=True
                )

        # Initial load
        await load_pipelines()

        # Auto-refresh timer (every 5 seconds)
        # Create async wrapper for timer callback
        async def refresh_callback() -> None:
            await load_pipelines()

        ui.timer(5.0, refresh_callback)
