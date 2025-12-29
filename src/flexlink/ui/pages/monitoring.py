"""Real-time pipeline execution monitoring page."""

import logging
from datetime import datetime
from typing import Any

from nicegui import ui

from flexlink.models.pipeline import TaskStatus

from ..api_client import FlexLinkAPIClient
from ..components.navigation import create_navigation
from ..components.status_badge import create_status_badge as _create_status_badge
from ..config import ui_settings

logger = logging.getLogger(__name__)


def create_status_badge(status: str) -> ui.badge:
    """
    Create a status badge for the given status.

    Args:
        status: Task status

    Returns:
        Status badge UI element
    """
    return _create_status_badge(status)


def get_status_icon(status: str) -> str:
    """
    Get Material icon for status.

    Args:
        status: Task status

    Returns:
        Icon name
    """
    icon_map = {
        "queued": "schedule",
        "running": "autorenew",
        "completed": "check_circle",
        "failed": "error"
    }
    return icon_map.get(status.lower(), "help")


def get_status_color(status: str) -> str:
    """
    Get color for status.

    Args:
        status: Task status

    Returns:
        Color name
    """
    color_map = {
        "queued": "grey",
        "running": "blue",
        "completed": "green",
        "failed": "red"
    }
    return color_map.get(status.lower(), "grey")


@ui.page('/monitoring/{run_id}')
async def monitoring_page(run_id: str) -> None:
    """
    Real-time pipeline execution monitoring page.

    Features:
    - Status badge display
    - Real-time log streaming
    - Progress indicators
    - Poll status every 2 seconds

    Args:
        run_id: Pipeline run ID to monitor
    """
    # Header with navigation
    create_navigation()

    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-4"):
        # Header
        with ui.row().classes("w-full items-center justify-between"):
            with ui.row().classes("items-center gap-2"):
                ui.button(
                    icon="arrow_back",
                    on_click=lambda: ui.navigate.to("/pipelines")
                ).props("flat round")
                ui.label("Pipeline Monitoring").classes("text-3xl font-bold")

            # Refresh button
            ui.button(
                "Refresh",
                icon="refresh",
                on_click=lambda: update_status()
            ).props("flat color=primary")

        # Run ID display
        with ui.card().classes("w-full"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("fingerprint")
                ui.label("Run ID:").classes("font-semibold")
                ui.label(run_id).classes("font-mono text-sm")

        # Status card
        with ui.card().classes("w-full"):
            with ui.column().classes("w-full gap-4"):
                ui.label("Status").classes("text-xl font-semibold")

                # Status row
                status_row = ui.row().classes("items-center gap-4 w-full")

                # Pipeline info
                info_column = ui.column().classes("gap-2")

                # Duration and times
                times_column = ui.column().classes("gap-1 text-sm")

                # Progress indicator (for running status)
                progress_container = ui.row().classes("w-full")

        # Error display (if any)
        error_card = ui.card().classes("w-full bg-red-50 dark:bg-red-900/20")
        error_card.visible = False
        with error_card:
            with ui.row().classes("items-start gap-2"):
                ui.icon("error").classes("text-red-500")
                error_label = ui.label("").classes("text-red-700 dark:text-red-300")

        # Logs card
        with ui.card().classes("w-full"):
            with ui.column().classes("w-full gap-4"):
                with ui.row().classes("items-center justify-between w-full"):
                    ui.label("Execution Logs").classes("text-xl font-semibold")

                    # Log controls
                    with ui.row().classes("gap-2"):
                        auto_scroll_toggle = ui.switch("Auto-scroll", value=True).classes("text-sm")

                # Log viewer container
                with ui.card().classes("w-full bg-gray-100 dark:bg-gray-900 p-4"):
                    log_class = (
                        "w-full gap-1 font-mono text-sm h-96 overflow-y-auto"
                    )
                    log_container = ui.column().classes(log_class)
                    log_container.style("scroll-behavior: smooth;")

        # State variables
        state: dict[str, Any] = {
            "last_log_count": 0,
            "is_completed": False,
            "timer": None,
            "pipeline_name": None
        }

        async def update_status() -> None:
            """Update status information."""
            try:
                async with FlexLinkAPIClient(ui_settings.api_base_url) as client:
                    # Get run status
                    status = await client.get_run_status(run_id)

                    # Store pipeline name for log fetching
                    state["pipeline_name"] = str(status.pipeline_name)

                    # Update status row
                    status_row.clear()
                    with status_row:
                        with ui.row().classes("items-center gap-2"):
                            ui.icon(get_status_icon(status.status.value)).classes(
                                f"text-{get_status_color(status.status.value)}-500"
                            ).style("font-size: 2rem;")
                            create_status_badge(status.status.value)

                    # Update info column
                    info_column.clear()
                    with info_column:
                        ui.label(f"Pipeline: {status.pipeline_name}").classes("font-semibold")

                    # Update times
                    times_column.clear()
                    with times_column:
                        if status.started_at:
                            time_class = "text-gray-600 dark:text-gray-400"
                            started_time = format_datetime(status.started_at)
                            ui.label(f"Started: {started_time}").classes(time_class)

                        if status.completed_at:
                            time_class = "text-gray-600 dark:text-gray-400"
                            completed_time = format_datetime(status.completed_at)
                            ui.label(f"Completed: {completed_time}").classes(time_class)

                        if status.duration_seconds is not None:
                            time_class = "text-gray-600 dark:text-gray-400"
                            duration = format_duration(status.duration_seconds)
                            ui.label(f"Duration: {duration}").classes(time_class)
                        elif status.started_at and status.status == TaskStatus.RUNNING:
                            # Calculate running duration
                            running_duration = (
                                datetime.now() - status.started_at
                            ).total_seconds()
                            time_class = "text-gray-600 dark:text-gray-400"
                            duration_text = (
                                f"Duration: {format_duration(running_duration)} "
                                "(running)"
                            )
                            ui.label(duration_text).classes(time_class)

                    # Update progress indicator
                    progress_container.clear()
                    if status.status == TaskStatus.RUNNING:
                        with progress_container:
                            ui.linear_progress().props("indeterminate color=primary")

                    # Update error display
                    if status.error_message:
                        error_label.text = status.error_message
                        error_card.visible = True
                    else:
                        error_card.visible = False

                    # Check if completed
                    if status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        state["is_completed"] = True
                        if state["timer"] is not None:
                            state["timer"].active = False

                    # Update logs
                    await update_logs()

            except Exception as e:
                logger.error(f"Failed to update status: {e}")
                ui.notify(
                    f"Error updating status: {str(e)}",
                    type="negative"
                )

        async def update_logs() -> None:
            """Update log display."""
            if not state["pipeline_name"]:
                return

            try:
                async with FlexLinkAPIClient(ui_settings.api_base_url) as client:
                    logs_response = await client.get_run_logs(
                        str(state["pipeline_name"]),
                        run_id,
                        limit=1000
                    )

                    logs = logs_response.logs
                    last_count = int(state["last_log_count"])

                    # Only update if new logs
                    if len(logs) > last_count:
                        # Clear and redraw all logs
                        log_container.clear()

                        with log_container:
                            for log_entry in logs:
                                await render_log_entry(log_entry)

                        state["last_log_count"] = len(logs)

                        # Auto-scroll if enabled
                        if auto_scroll_toggle.value:
                            ui.run_javascript("""
                            const container = document.querySelector('.overflow-y-auto');
                            if (container) {
                                container.scrollTop = container.scrollHeight;
                            }
                            """)

            except Exception as e:
                logger.error(f"Failed to update logs: {e}")
                # Don't show notification for log errors to avoid spam

        async def render_log_entry(log_entry: Any) -> None:
            """
            Render a single log entry.

            Args:
                log_entry: Log entry to render
            """
            level_colors = {
                "DEBUG": "text-gray-500",
                "INFO": "text-blue-500",
                "WARNING": "text-yellow-500",
                "ERROR": "text-red-500",
                "CRITICAL": "text-red-700"
            }

            color_class = level_colors.get(log_entry.level, "text-gray-500")

            with ui.row().classes("items-start gap-2 w-full"):
                ui.label(log_entry.timestamp).classes(
                    "text-gray-500 text-xs whitespace-nowrap"
                )
                level_class = f"{color_class} font-semibold text-xs whitespace-nowrap"
                ui.label(f"[{log_entry.level}]").classes(level_class)
                ui.label(log_entry.message).classes("flex-grow")

        def format_datetime(dt: datetime) -> str:
            """
            Format datetime for display.

            Args:
                dt: Datetime to format

            Returns:
                Formatted string
            """
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        def format_duration(seconds: float) -> str:
            """
            Format duration in seconds to human-readable string.

            Args:
                seconds: Duration in seconds

            Returns:
                Formatted string
            """
            if seconds < 60:
                return f"{seconds:.1f}s"
            elif seconds < 3600:
                minutes = seconds / 60
                return f"{minutes:.1f}m"
            else:
                hours = seconds / 3600
                return f"{hours:.1f}h"

        # Initial load
        await update_status()

        # Poll every 2 seconds if not completed
        if not state["is_completed"]:
            state["timer"] = ui.timer(2.0, lambda: update_status())
