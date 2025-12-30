"""Main NiceGUI application for FlexLink monitoring dashboard."""

import logging
from collections.abc import Callable

from nicegui import app, ui

from .api_client import FlexLinkAPIClient
from .config import ui_settings
from .theme import apply_material_theme, initialize_theme_from_storage

logger = logging.getLogger(__name__)


def create_ui_app(api_base_url: str = "http://localhost:8000") -> None:
    """
    Initialize and configure the FlexLink NiceGUI application.

    This function:
    1. Applies Material Design 3 theme
    2. Initializes the API client
    3. Sets up page routing
    4. Creates global layout with header and navigation
    5. Configures dark theme by default

    Args:
        api_base_url: Base URL for FlexLink API (default: http://localhost:8000)

    Example:
        >>> create_ui_app("http://localhost:8000")
        >>> # App is now configured and ready to run with ui.run() or mounted to FastAPI
    """
    # Apply Material Design 3 theme
    apply_material_theme()

    # Store API base URL in app storage for access across pages
    app.storage.user["api_base_url"] = api_base_url

    # Initialize theme from localStorage on page load
    @ui.page("/")
    async def index_page() -> None:
        """Home/dashboard page."""
        initialize_theme_from_storage()

        # Try to import and render index page
        try:
            from .pages import index

            await index.render(api_base_url)
        except ImportError:
            logger.warning("Index page not yet implemented, showing placeholder")
            _render_placeholder_page("Dashboard", "dashboard")

    # Pipelines page is registered via @ui.page decorator in pages/pipelines.py
    # No duplicate registration needed here

    @ui.page("/pipelines/{name}")
    async def pipeline_detail_page(name: str) -> None:
        """Pipeline detail page."""
        initialize_theme_from_storage()

        try:
            from .pages import pipeline_detail  # type: ignore[attr-defined]

            await pipeline_detail.render(name, api_base_url)
        except ImportError:
            logger.warning("Pipeline detail page not yet implemented, showing placeholder")
            _render_placeholder_page(f"Pipeline: {name}", "analytics")

    # Connectors page is registered via @ui.page decorator in pages/connectors.py
    # No separate route registration needed here

    @ui.page("/schedules")
    async def schedules_page() -> None:
        """Schedules management page."""
        initialize_theme_from_storage()

        try:
            from .pages import schedules  # type: ignore[attr-defined]

            await schedules.render(api_base_url)
        except ImportError:
            logger.warning("Schedules page not yet implemented, showing placeholder")
            _render_placeholder_page("Schedules", "schedule")

    # History page is registered via @ui.page decorator in pages/history.py
    # No duplicate registration needed here

    @ui.page("/settings")
    async def settings_page() -> None:
        """Application settings page."""
        initialize_theme_from_storage()

        try:
            from .pages import settings  # type: ignore[attr-defined]

            await settings.render()
        except ImportError:
            logger.warning("Settings page not yet implemented, showing placeholder")
            _render_placeholder_page("Settings", "settings")

    # Import page modules to register their @ui.page decorators
    # This must happen after placeholder routes are defined to avoid conflicts
    try:
        from .pages import connectors, history, monitoring, pipelines  # noqa: F401
        logger.info("Loaded UI page modules: pipelines, history, monitoring, connectors")
    except ImportError as e:
        logger.warning(f"Some UI page modules could not be loaded: {e}")

    # Configure app metadata
    ui.page_title("FlexLink - Pipeline Monitoring")

    logger.info(f"FlexLink UI initialized with API base URL: {api_base_url}")


def _render_placeholder_page(title: str, icon: str) -> None:
    """
    Render a placeholder page when actual page implementation is not available.

    Args:
        title: Page title
        icon: Material Symbol icon name
    """
    with ui.column().classes("w-full h-screen items-center justify-center"):
        ui.icon(icon, size="4rem").classes("text-primary mb-4")
        ui.label(title).classes("text-h4 mb-2")
        ui.label("This page is under construction").classes("text-subtitle1 text-medium-emphasis")
        ui.button("Go to Pipelines", on_click=lambda: ui.navigate.to("pipelines")).classes(
            "mt-8"
        ).props("flat color=primary")


def create_header(on_theme_toggle: Callable[[], None] | None = None) -> None:
    """
    Create the application header with navigation.

    This is a reusable component that can be imported by pages to create
    consistent navigation across the application.

    Args:
        on_theme_toggle: Optional callback for theme toggle button
    """
    with ui.header().classes("bg-primary text-on-primary shadow-md"):
        with ui.row().classes("w-full items-center justify-between px-4"):
            # Logo and title
            with ui.row().classes("items-center gap-2"):
                ui.icon("account_tree", size="2rem")
                ui.label("FlexLink").classes("text-h5 font-medium")

            # Navigation menu
            with ui.row().classes("items-center gap-2"):
                ui.button("Dashboard", on_click=lambda: ui.navigate.to("/")).props(
                    "flat dense color=on-primary"
                )
                ui.button("Pipelines", on_click=lambda: ui.navigate.to("pipelines")).props(
                    "flat dense color=on-primary"
                )
                ui.button("Connectors", on_click=lambda: ui.navigate.to("connectors")).props(
                    "flat dense color=on-primary"
                )
                ui.button("Schedules", on_click=lambda: ui.navigate.to("schedules")).props(
                    "flat dense color=on-primary"
                )
                ui.button("History", on_click=lambda: ui.navigate.to("history")).props(
                    "flat dense color=on-primary"
                )

                # Settings and theme toggle
                ui.separator().props("vertical")

                if on_theme_toggle:
                    ui.button(icon="dark_mode", on_click=on_theme_toggle).props(
                        "flat round dense color=on-primary"
                    ).tooltip("Toggle theme")

                ui.button(
                    icon="settings", on_click=lambda: ui.navigate.to("settings")
                ).props("flat round dense color=on-primary").tooltip("Settings")


def create_drawer_navigation() -> None:
    """
    Create a navigation drawer for mobile/smaller screens.

    This provides an alternative navigation method when the header menu
    would be too crowded.
    """
    with ui.left_drawer().classes("bg-surface"):
        with ui.column().classes("w-full p-4 gap-2"):
            ui.label("Navigation").classes("text-h6 mb-2")

            ui.button("Dashboard", icon="dashboard", on_click=lambda: ui.navigate.to("/")).props(
                "flat align=left color=primary"
            ).classes("w-full")

            ui.button(
                "Pipelines", icon="view_list", on_click=lambda: ui.navigate.to("pipelines")
            ).props("flat align=left color=primary").classes("w-full")

            ui.button(
                "Connectors", icon="link", on_click=lambda: ui.navigate.to("connectors")
            ).props("flat align=left color=primary").classes("w-full")

            ui.button(
                "Schedules", icon="schedule", on_click=lambda: ui.navigate.to("schedules")
            ).props("flat align=left color=primary").classes("w-full")

            ui.button("History", icon="history", on_click=lambda: ui.navigate.to("history")).props(
                "flat align=left color=primary"
            ).classes("w-full")

            ui.separator()

            ui.button(
                "Settings", icon="settings", on_click=lambda: ui.navigate.to("settings")
            ).props("flat align=left color=primary").classes("w-full")


def get_api_client() -> FlexLinkAPIClient:
    """
    Get the API client for the current session.

    Returns:
        FlexLinkAPIClient instance configured with the current API base URL

    Example:
        >>> async with get_api_client() as client:
        ...     pipelines = await client.list_pipelines()
    """
    api_base_url = app.storage.user.get("api_base_url", ui_settings.api_base_url)
    return FlexLinkAPIClient(base_url=api_base_url)
