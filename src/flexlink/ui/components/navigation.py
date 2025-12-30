"""Navigation bar component with Material Design 3 styling."""

from nicegui import ui


def create_navigation() -> None:
    """
    Create top navigation bar with Material Design 3 Top App Bar pattern.

    Features:
    - FlexLink logo and title
    - Navigation links (Pipelines, History, Connectors)
    - Theme toggle button
    - Material Symbols icons
    - M3 elevation and colors
    """
    with ui.header().classes("md3-top-app-bar").style(
        "padding: 0 16px; display: flex; align-items: center; justify-content: space-between;"
    ):
        # Left section: Logo and title
        with ui.row().classes("items-center gap-4"):
            # Logo/Icon
            ui.icon("memory", size="32px").classes("text-primary")
            # Title
            ui.label("FlexLink").classes("md3-title-large").style(
                "font-weight: 500; color: var(--md-sys-color-on-surface);"
            )

        # Center section: Navigation links
        with ui.row().classes("items-center gap-2"):
            ui.button("Dashboard", icon="dashboard", on_click=lambda: ui.navigate.to("/")).props(
                "flat"
            ).classes("md3-button-text")

            ui.button(
                "Pipelines", icon="view_list", on_click=lambda: ui.navigate.to("pipelines")
            ).props("flat").classes("md3-button-text")

            ui.button("History", icon="history", on_click=lambda: ui.navigate.to("history")).props(
                "flat"
            ).classes("md3-button-text")

            ui.button(
                "Connectors", icon="cable", on_click=lambda: ui.navigate.to("connectors")
            ).props("flat").classes("md3-button-text")
