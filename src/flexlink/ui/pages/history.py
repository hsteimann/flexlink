"""Historical pipeline runs browser page."""

import logging
from datetime import datetime, timedelta
from typing import Any

from nicegui import ui

from ..api_client import FlexLinkAPIClient
from ..components.navigation import create_navigation
from ..components.status_badge import create_status_badge as _create_status_badge
from ..config import ui_settings

logger = logging.getLogger(__name__)


def create_status_badge(status: str) -> ui.badge:
    """
    Create a status badge for the given status.

    Args:
        status: Run status

    Returns:
        Status badge UI element
    """
    return _create_status_badge(status)


def get_status_icon(status: str) -> str:
    """
    Get Material icon for status.

    Args:
        status: Run status

    Returns:
        Icon name
    """
    icon_map = {
        "success": "check_circle",
        "partial": "warning",
        "failed": "error"
    }
    return icon_map.get(status.lower(), "help")


@ui.page('/history')
async def history_page() -> None:
    """
    Historical pipeline runs browser page.

    Features:
    - Pipeline selector dropdown
    - Paginated table of runs
    - Date filtering
    """
    # Header with navigation
    create_navigation()

    # Main content with consistent layout
    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-4"):
        # Header
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Pipeline History").classes("text-3xl font-bold")

            ui.button(
                "Refresh",
                icon="refresh",
                on_click=lambda: refresh_history()
            ).props("flat color=primary")

        # Filters card
        with ui.card().classes("w-full"):
            with ui.column().classes("w-full gap-4"):
                ui.label("Filters").classes("text-xl font-semibold")

                with ui.row().classes("w-full gap-4 items-end flex-wrap"):
                    # Pipeline selector
                    pipeline_select = ui.select(
                        label="Pipeline",
                        options=[],
                        value=None,
                        on_change=lambda: apply_filters()
                    ).classes("flex-grow min-w-64")
                    pipeline_select.props("clearable")

                    # Date range filters
                    date_from = ui.date(
                        value=None,
                        on_change=lambda: apply_filters()
                    ).classes("w-48")

                    date_to = ui.date(
                        value=None,
                        on_change=lambda: apply_filters()
                    ).classes("w-48")

                    # Quick filters
                    with ui.row().classes("gap-2"):
                        ui.button(
                            "Today",
                            on_click=lambda: set_date_filter("today")
                        ).props("outline size=sm")

                        ui.button(
                            "Last 7 days",
                            on_click=lambda: set_date_filter("week")
                        ).props("outline size=sm")

                        ui.button(
                            "Last 30 days",
                            on_click=lambda: set_date_filter("month")
                        ).props("outline size=sm")

                        ui.button(
                            "Clear",
                            on_click=lambda: clear_filters()
                        ).props("outline size=sm")

        # Loading indicator
        loading = ui.spinner(size="lg")
        loading.visible = False

        # Error display
        error_label = ui.label("").classes("text-red-500")
        error_label.visible = False

        # Results card
        with ui.card().classes("w-full"):
            with ui.column().classes("w-full gap-4"):
                # Results header
                with ui.row().classes("items-center justify-between w-full"):
                    ui.label("Results").classes("text-xl font-semibold")
                    count_label = ui.label("").classes("text-sm text-gray-500")

                # Table container
                table_container = ui.column().classes("w-full")

                # Pagination controls
                with ui.row().classes("items-center justify-between w-full mt-4"):
                    pagination_info = ui.label("").classes("text-sm text-gray-500")

                    with ui.row().classes("gap-2"):
                        prev_button = ui.button(
                            icon="chevron_left",
                            on_click=lambda: go_to_page(state["current_page"] - 1)
                        ).props("flat round")
                        prev_button.enabled = False

                        page_label = ui.label("Page 1").classes("text-sm")

                        next_button = ui.button(
                            icon="chevron_right",
                            on_click=lambda: go_to_page(state["current_page"] + 1)
                        ).props("flat round")
                        next_button.enabled = False

        # State variables
        state: dict[str, Any] = {
            "pipelines": [],
            "runs": [],
            "current_page": 1,
            "page_size": 20,
            "total_runs": 0,
            "selected_pipeline": None,
            "date_from": None,
            "date_to": None
        }

        async def load_pipelines() -> None:
            """Load available pipelines for selector."""
            try:
                async with FlexLinkAPIClient(ui_settings.api_base_url) as client:
                    response = await client.list_pipelines()
                    pipelines = response.get("pipelines", [])

                    # Extract pipeline names
                    pipeline_names = [p.get("name") for p in pipelines if p.get("name")]
                    state["pipelines"] = pipeline_names

                    # Update select options
                    pipeline_select.options = pipeline_names

            except Exception as e:
                logger.error(f"Failed to load pipelines: {e}")
                ui.notify(
                    f"Error loading pipelines: {str(e)}",
                    type="negative"
                )

        async def load_history() -> None:
            """Load pipeline run history."""
            if not state["selected_pipeline"]:
                table_container.clear()
                with table_container:
                    ui.label("Please select a pipeline to view history").classes(
                        "text-gray-500 text-center p-8"
                    )
                count_label.text = ""
                pagination_info.text = ""
                prev_button.enabled = False
                next_button.enabled = False
                return

            loading.visible = True
            error_label.visible = False

            try:
                async with FlexLinkAPIClient(ui_settings.api_base_url) as client:
                    current_page: int = state["current_page"]
                    page_size: int = state["page_size"]
                    offset = (current_page - 1) * page_size
                    pipeline_name: str = state["selected_pipeline"]
                    runs = await client.get_pipeline_runs(
                        pipeline_name,
                        limit=page_size,
                        offset=offset
                    )

                    # Apply date filters (client-side for now)
                    filtered_runs = runs
                    if state["date_from"] or state["date_to"]:
                        filtered_runs = filter_runs_by_date(runs)

                    state["runs"] = filtered_runs
                    state["total_runs"] = len(filtered_runs)

                    # Update count
                    count_label.text = f"{len(filtered_runs)} run(s)"

                    # Render table
                    await render_history_table()

                    # Update pagination
                    update_pagination()

            except Exception as e:
                logger.error(f"Failed to load history: {e}")
                error_label.text = f"Error loading history: {str(e)}"
                error_label.visible = True
            finally:
                loading.visible = False

        def filter_runs_by_date(runs: list[Any]) -> list[Any]:
            """
            Filter runs by date range.

            Args:
                runs: List of run records

            Returns:
                Filtered runs
            """
            filtered = []
            for run in runs:
                run_date = run.started_at

                if state["date_from"]:
                    from_date = datetime.strptime(
                        str(state["date_from"]), "%Y-%m-%d"
                    )
                    if run_date < from_date:
                        continue

                if state["date_to"]:
                    to_date = datetime.strptime(
                        str(state["date_to"]), "%Y-%m-%d"
                    ) + timedelta(days=1)
                    if run_date >= to_date:
                        continue

                filtered.append(run)

            return filtered

        async def render_history_table() -> None:
            """Render the history table."""
            table_container.clear()

            if not state["runs"]:
                with table_container:
                    ui.label("No runs found").classes("text-gray-500 text-center p-8")
                return

            # Create table
            with table_container:
                with ui.card().classes("w-full overflow-x-auto"):
                    with ui.element("table").classes("w-full"):
                        # Header
                        with ui.element("thead").classes(
                            "bg-gray-100 dark:bg-gray-800"
                        ):
                            with ui.element("tr"):
                                th_class = "p-3 text-left text-sm font-semibold"
                                with ui.element("th").classes(th_class):
                                    ui.label("Run ID")
                                with ui.element("th").classes(th_class):
                                    ui.label("Status")
                                with ui.element("th").classes(th_class):
                                    ui.label("Started")
                                with ui.element("th").classes(th_class):
                                    ui.label("Duration")
                                with ui.element("th").classes(th_class):
                                    ui.label("Records")
                                with ui.element("th").classes(th_class):
                                    ui.label("Triggered By")
                                with ui.element("th").classes(th_class):
                                    ui.label("Actions")

                        # Body
                        with ui.element("tbody"):
                            runs_list: list[Any] = state["runs"]
                            for run in runs_list:
                                await render_history_row(run)

        async def render_history_row(run: Any) -> None:
            """
            Render a single history table row.

            Args:
                run: Pipeline run history record
            """
            tr_class = (
                "border-b border-gray-200 dark:border-gray-700 "
                "hover:bg-gray-50 dark:hover:bg-gray-800"
            )
            with ui.element("tr").classes(tr_class):
                # Run ID
                with ui.element("td").classes("p-3"):
                    ui.label(run.run_id[:8] + "...").classes("font-mono text-xs")

                # Status
                with ui.element("td").classes("p-3"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon(get_status_icon(run.status)).classes(
                            f"text-sm text-{get_status_color(run.status)}-500"
                        )
                        create_status_badge(run.status)

                # Started
                with ui.element("td").classes("p-3"):
                    ui.label(format_datetime(run.started_at)).classes("text-sm")

                # Duration
                with ui.element("td").classes("p-3"):
                    ui.label(format_duration(run.duration_seconds)).classes("text-sm")

                # Records
                with ui.element("td").classes("p-3"):
                    with ui.column().classes("gap-0"):
                        rec_class = "text-xs text-gray-600 dark:text-gray-400"
                        ui.label(f"E: {run.records_extracted}").classes(rec_class)
                        ui.label(f"T: {run.records_transformed}").classes(rec_class)
                        ui.label(f"L: {run.records_loaded}").classes(rec_class)
                        if run.validation_errors > 0:
                            err_text = f"Errors: {run.validation_errors}"
                            ui.label(err_text).classes("text-xs text-red-500")

                # Triggered by
                with ui.element("td").classes("p-3"):
                    triggered_icon = "person" if run.triggered_by == "manual" else "schedule"
                    with ui.row().classes("items-center gap-1"):
                        ui.icon(triggered_icon).classes("text-sm")
                        ui.label(run.triggered_by).classes("text-sm")

                # Actions
                # Create closures to avoid NiceGUI click event override
                run_id_str = run.run_id
                run_data = run

                def make_view_handler(rid: str) -> Any:
                    """Create view handler with captured run_id."""
                    def handler() -> None:
                        view_run(rid)
                    return handler

                def make_error_handler(r: Any) -> Any:
                    """Create error handler with captured run data."""
                    def handler() -> None:
                        show_error(r)
                    return handler

                with ui.element("td").classes("p-3"):
                    with ui.row().classes("gap-1"):
                        ui.button(
                            icon="visibility",
                            on_click=make_view_handler(run_id_str)
                        ).props("flat round size=sm")

                        if run.error_message:
                            ui.button(
                                icon="error",
                                on_click=make_error_handler(run_data)
                            ).props("flat round size=sm color=red")

        def get_status_color(status: str) -> str:
            """
            Get color for status.

            Args:
                status: Run status

            Returns:
                Color name
            """
            color_map = {
                "success": "green",
                "partial": "yellow",
                "failed": "red"
            }
            return color_map.get(status.lower(), "grey")

        def view_run(run_id: str) -> None:
            """
            Navigate to monitoring page for a run.

            Args:
                run_id: Run ID to view
            """
            ui.navigate.to(f"/monitoring/{run_id}")

        def show_error(run: Any) -> None:
            """
            Show error message in dialog.

            Args:
                run: Run record with error
            """
            with ui.dialog() as dialog, ui.card():
                ui.label("Error Details").classes("text-xl font-semibold")

                with ui.column().classes("gap-2 mt-4"):
                    ui.label(f"Run ID: {run.run_id}").classes("font-mono text-sm")
                    ui.label(f"Pipeline: {run.pipeline_name}").classes("text-sm")

                    with ui.card().classes("bg-red-50 dark:bg-red-900/20 mt-4"):
                        err_class = "text-sm text-red-700 dark:text-red-300"
                        ui.label(run.error_message or "No error message").classes(
                            err_class
                        )

                with ui.row().classes("justify-end mt-4"):
                    ui.button("Close", on_click=dialog.close).props("flat")

            dialog.open()

        def update_pagination() -> None:
            """Update pagination controls."""
            total_runs: int = state["total_runs"]
            page_size: int = state["page_size"]
            current_page: int = state["current_page"]
            total_pages = max(1, (total_runs + page_size - 1) // page_size)

            # Update page label
            page_label.text = f"Page {current_page} of {total_pages}"

            # Update info
            start = (current_page - 1) * page_size + 1
            end = min(current_page * page_size, total_runs)
            pagination_info.text = f"Showing {start}-{end} of {total_runs}"

            # Update buttons
            prev_button.enabled = current_page > 1
            next_button.enabled = current_page < total_pages

        async def go_to_page(page: int) -> None:
            """
            Navigate to a specific page.

            Args:
                page: Page number
            """
            state["current_page"] = page
            await load_history()

        async def apply_filters() -> None:
            """Apply selected filters."""
            state["selected_pipeline"] = pipeline_select.value
            state["current_page"] = 1  # Reset to first page
            await load_history()

        async def set_date_filter(filter_type: str) -> None:
            """
            Set date filter to predefined range.

            Args:
                filter_type: Type of filter ("today", "week", "month")
            """
            today = datetime.now()

            if filter_type == "today":
                date_from.value = today.strftime("%Y-%m-%d")
                date_to.value = today.strftime("%Y-%m-%d")
            elif filter_type == "week":
                week_ago = today - timedelta(days=7)
                date_from.value = week_ago.strftime("%Y-%m-%d")
                date_to.value = today.strftime("%Y-%m-%d")
            elif filter_type == "month":
                month_ago = today - timedelta(days=30)
                date_from.value = month_ago.strftime("%Y-%m-%d")
                date_to.value = today.strftime("%Y-%m-%d")

            state["date_from"] = date_from.value
            state["date_to"] = date_to.value
            await apply_filters()

        async def clear_filters() -> None:
            """Clear all filters."""
            pipeline_select.value = None
            date_from.value = None
            date_to.value = None
            state["selected_pipeline"] = None
            state["date_from"] = None
            state["date_to"] = None
            state["current_page"] = 1
            await apply_filters()

        async def refresh_history() -> None:
            """Refresh the history view."""
            await load_pipelines()
            await load_history()

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
        await load_pipelines()
