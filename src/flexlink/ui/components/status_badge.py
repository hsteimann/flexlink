"""Status badge component with Material Design 3 colors."""

from nicegui import ui


def create_status_badge(status: str) -> ui.badge:
    """
    Create a status badge with Material Design 3 styling.

    Args:
        status: Status value (running, success, failed, partial, pending, completed, queued)

    Returns:
        ui.badge: NiceGUI badge component with appropriate styling

    Status mapping:
    - running: Primary color (blue/purple)
    - success/completed: Success color (green)
    - failed: Error color (red)
    - partial: Warning color (yellow/orange)
    - pending/queued: Secondary color (gray)
    """
    # Normalize status to lowercase
    status_lower = status.lower()

    # Map status to M3 badge class and icon
    status_config = {
        "running": {
            "class": "md3-badge-primary",
            "icon": "play_circle",
            "label": "Running",
        },
        "success": {
            "class": "md3-badge-success",
            "icon": "check_circle",
            "label": "Success",
        },
        "completed": {
            "class": "md3-badge-success",
            "icon": "check_circle",
            "label": "Completed",
        },
        "failed": {
            "class": "md3-badge-error",
            "icon": "error",
            "label": "Failed",
        },
        "partial": {
            "class": "md3-badge-warning",
            "icon": "warning",
            "label": "Partial",
        },
        "pending": {
            "class": "md3-badge-secondary",
            "icon": "schedule",
            "label": "Pending",
        },
        "queued": {
            "class": "md3-badge-secondary",
            "icon": "schedule",
            "label": "Queued",
        },
    }

    # Get config or default to secondary
    config = status_config.get(
        status_lower,
        {
            "class": "md3-badge-secondary",
            "icon": "help",
            "label": status.capitalize(),
        },
    )

    # Create badge with icon and label
    badge = ui.badge(config["label"]).classes(f"md3-badge {config['class']}").style(
        "display: inline-flex; align-items: center; gap: 4px; "
        "padding: 4px 12px; border-radius: var(--md-sys-shape-corner-full); "
        "font-size: var(--md-sys-typescale-label-small-size); "
        "font-weight: var(--md-sys-typescale-label-small-weight);"
    )

    # Add icon inside badge using raw HTML
    with badge:
        icon_html = (
            f'<span class="material-symbols-outlined" '
            f'style="font-size: 16px;">{config["icon"]}</span>'
        )
        ui.html(icon_html, sanitize=False)

    return badge
