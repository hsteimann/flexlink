"""Connectors management page."""

import logging
from typing import Any

from nicegui import ui

from ..api_client import FlexLinkAPIClient, get_api_base_url
from ..components.navigation import create_navigation
from ..components.status_badge import create_status_badge as _create_status_badge

logger = logging.getLogger(__name__)


def create_status_badge(enabled: bool) -> ui.badge:
    """
    Create status badge for connector.

    Args:
        enabled: Whether connector is enabled

    Returns:
        Status badge UI element
    """
    badge_status = "active" if enabled else "disabled"
    return _create_status_badge(badge_status)


@ui.page("/connectors")
async def connectors_page() -> None:
    """
    Connectors list and detail view page.

    Features:
    - Card-based layout showing all connectors
    - Type badges and status indicators
    - Expandable configuration (metadata only)
    - Auto-refresh every 5 seconds
    """
    # Header with navigation
    create_navigation()

    # Main content container
    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-4"):
        # Header row
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Connectors").classes("text-3xl font-bold")
            ui.button("Refresh", icon="refresh", on_click=lambda: refresh_connectors()).props(
                "flat color=primary"
            )

        # Loading indicator
        loading = ui.spinner(size="lg")
        loading.visible = False

        # Error display
        error_label = ui.label("").classes("text-red-500")
        error_label.visible = False

        # Connectors container
        connectors_container = ui.column().classes("w-full gap-4")

        # Track expanded connectors (preserve state during refresh)
        expanded_connectors: set[str] = set()

        async def load_connectors() -> None:
            """Load and display connectors."""
            loading.visible = True
            error_label.visible = False
            connectors_container.clear()

            try:
                async with FlexLinkAPIClient(get_api_base_url()) as client:
                    response = await client.list_connectors()
                    connectors_list = response.get("connectors", [])

                if not connectors_list:
                    with connectors_container:
                        ui.label("No connectors found").classes("text-gray-500 text-center p-8")
                    return

                # Create connector cards
                for connector_data in connectors_list:
                    await create_connector_card(connector_data, connectors_container)

            except Exception as e:
                logger.error(f"Failed to load connectors: {e}")
                error_label.text = f"Error loading connectors: {str(e)}"
                error_label.visible = True
            finally:
                loading.visible = False

        async def create_connector_card(
            connector_data: dict[str, Any], container: ui.column
        ) -> None:
            """
            Create a connector card with details.

            Args:
                connector_data: Connector metadata
                container: Container to add card to
            """
            with container:
                with ui.card().classes("w-full"):
                    with ui.row().classes("w-full items-center justify-between p-2"):
                        # Left side: Name, type, description
                        with ui.column().classes("gap-1"):
                            # Name and type badge
                            with ui.row().classes("items-center gap-2"):
                                ui.label(connector_data.get("name", "Unknown")).classes(
                                    "text-xl font-semibold"
                                )
                                # Type badge
                                connector_type = connector_data.get("type", "unknown")
                                type_color = get_type_color(connector_type)
                                ui.badge(connector_type.upper(), color=type_color).props("outline")

                            # Description
                            if connector_data.get("description"):
                                ui.label(connector_data["description"]).classes(
                                    "text-sm text-gray-500"
                                )

                        # Right side: Type icon
                        type_icon = get_type_icon(connector_data.get("type", "unknown"))
                        ui.icon(type_icon, size="32px").classes("text-gray-400")

                    # Expandable metadata section
                    connector_name = connector_data.get("name", "")
                    with ui.expansion(text="Details").classes("w-full") as expansion:
                        # Restore previous expansion state
                        expansion.value = connector_name in expanded_connectors

                        with ui.column().classes("w-full p-4 gap-2"):
                            # Display metadata
                            ui.label("Metadata").classes("text-lg font-semibold mb-2")

                            with ui.grid(columns=2).classes("w-full gap-2"):
                                # Name
                                ui.label("Name:").classes("font-semibold")
                                ui.label(connector_data.get("name", "N/A"))

                                # Type
                                ui.label("Type:").classes("font-semibold")
                                ui.label(connector_data.get("type", "N/A"))

                                # Description
                                ui.label("Description:").classes("font-semibold")
                                ui.label(connector_data.get("description") or "N/A")

                        # Track expansion state
                        def make_expand_handler(name: str) -> Any:
                            """Create expansion handler with captured name."""

                            def handler(e: Any) -> None:
                                if e.value:
                                    expanded_connectors.add(name)
                                else:
                                    expanded_connectors.discard(name)

                            return handler

                        expansion.on_value_change(make_expand_handler(connector_name))

        def get_type_color(connector_type: str) -> str:
            """
            Get badge color for connector type.

            Args:
                connector_type: Connector type string

            Returns:
                Color name for badge
            """
            color_map = {
                "rest": "blue",
                "postgresql": "purple",
                "file": "green",
                "webhook": "orange",
            }
            return color_map.get(connector_type, "grey")

        def get_type_icon(connector_type: str) -> str:
            """
            Get icon for connector type.

            Args:
                connector_type: Connector type string

            Returns:
                Material icon name
            """
            icon_map = {
                "rest": "http",
                "postgresql": "storage",
                "file": "folder",
                "webhook": "webhook",
            }
            return icon_map.get(connector_type, "link")

        async def refresh_connectors() -> None:
            """Refresh the connectors list."""
            await load_connectors()

        # Initial load
        await load_connectors()

        # Auto-refresh timer (every 5 seconds)
        async def refresh_callback() -> None:
            await load_connectors()

        ui.timer(5.0, refresh_callback)
