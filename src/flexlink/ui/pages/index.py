"""Dashboard/Home page with navigation cards to all sections."""

import logging

from nicegui import ui

from flexlink.ui.components.navigation import create_navigation

logger = logging.getLogger(__name__)


async def render(api_base_url: str) -> None:
    """
    Render the dashboard/home page with navigation cards.

    Args:
        api_base_url: Base URL for FlexLink API
    """
    # Header with navigation
    create_navigation()

    # Main content
    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-8"):
        # Welcome section
        with ui.row().classes("w-full items-center justify-between mb-4"):
            with ui.column().classes("gap-2"):
                ui.label("FlexLink Dashboard").classes("text-4xl font-bold").style(
                    "color: var(--md-sys-color-primary);"
                )
                ui.label(
                    "Data integration and pipeline orchestration platform"
                ).classes("text-lg").style(
                    "color: var(--md-sys-color-on-surface-variant);"
                )

        # Navigation cards grid
        with ui.grid(columns=3).classes("w-full gap-4"):
            # Pipelines card
            _create_navigation_card(
                title="Pipelines",
                description="View, configure, and execute data pipelines",
                icon="view_list",
                route="/pipelines",
                color="primary",
            )

            # History card
            _create_navigation_card(
                title="Run History",
                description="Browse past pipeline executions and logs",
                icon="history",
                route="/history",
                color="secondary",
            )

            # Connectors card
            _create_navigation_card(
                title="Connectors",
                description="Manage data source and destination connectors",
                icon="cable",
                route="/connectors",
                color="tertiary",
            )

            # Schedules card
            _create_navigation_card(
                title="Schedules",
                description="View and manage pipeline schedules",
                icon="schedule",
                route="/schedules",
                color="primary",
            )

            # API Documentation card
            _create_navigation_card(
                title="API Docs",
                description="Interactive API documentation (Swagger UI)",
                icon="api",
                route="/docs",
                color="secondary",
            )

            # Settings card
            _create_navigation_card(
                title="Settings",
                description="Configure application settings",
                icon="settings",
                route="/settings",
                color="tertiary",
            )

        # Quick stats section
        ui.separator().classes("my-8")

        with ui.row().classes("w-full gap-4"):
            ui.label("Quick Stats").classes("text-2xl font-semibold mb-4").style(
                "color: var(--md-sys-color-on-surface);"
            )

        with ui.grid(columns=4).classes("w-full gap-4"):
            # These would be populated with real data from API
            _create_stat_card("Total Pipelines", "3", "view_list")
            _create_stat_card("Active Runs", "0", "play_circle")
            _create_stat_card("Scheduled", "0", "schedule")
            _create_stat_card("Connectors", "4", "cable")


def _create_navigation_card(
    title: str,
    description: str,
    icon: str,
    route: str,
    color: str = "primary",
) -> None:
    """
    Create a navigation card for the dashboard.

    Args:
        title: Card title
        description: Card description
        icon: Material icon name
        route: Route to navigate to
        color: M3 color role (primary, secondary, tertiary)
    """
    with ui.card().classes(
        "cursor-pointer hover:shadow-lg transition-shadow"
    ).style(
        "background: var(--md-sys-color-surface-container-low); "
        "border: 1px solid var(--md-sys-color-outline-variant); "
        "min-height: 180px; "
        "display: flex; "
        "flex-direction: column; "
        "justify-content: space-between;"
    ).on(
        "click", lambda: ui.navigate.to(route)
    ):
        with ui.column().classes("gap-3 p-2"):
            # Icon
            ui.icon(icon, size="48px").style(
                f"color: var(--md-sys-color-{color});"
            )

            # Title
            ui.label(title).classes("text-xl font-semibold").style(
                "color: var(--md-sys-color-on-surface);"
            )

            # Description
            ui.label(description).classes("text-sm").style(
                "color: var(--md-sys-color-on-surface-variant); "
                "line-height: 1.4;"
            )


def _create_stat_card(label: str, value: str, icon: str) -> None:
    """
    Create a statistics card.

    Args:
        label: Stat label
        value: Stat value
        icon: Material icon name
    """
    with ui.card().classes("p-4").style(
        "background: var(--md-sys-color-surface-container); "
        "border: 1px solid var(--md-sys-color-outline-variant);"
    ):
        with ui.row().classes("items-center gap-3 w-full"):
            ui.icon(icon, size="32px").style(
                "color: var(--md-sys-color-primary);"
            )
            with ui.column().classes("gap-1"):
                ui.label(value).classes("text-2xl font-bold").style(
                    "color: var(--md-sys-color-on-surface);"
                )
                ui.label(label).classes("text-sm").style(
                    "color: var(--md-sys-color-on-surface-variant);"
                )
