"""Material Design 3 theme configuration for NiceGUI."""

from pathlib import Path

from nicegui import ui


def apply_material_theme() -> None:
    """
    Apply Material Design 3 theme to NiceGUI application.

    This function:
    1. Loads the Material Design 3 CSS file
    2. Adds it to the NiceGUI app head
    3. Loads Material Symbols icon font
    4. Sets up theme toggle functionality
    """
    # Get path to material3.css
    static_dir = Path(__file__).parent / "static"
    css_file = static_dir / "material3.css"

    # Read CSS content
    if css_file.exists():
        with open(css_file) as f:
            css_content = f.read()

        # Add CSS to app
        ui.add_head_html(f"<style>{css_content}</style>")
    else:
        # Fallback: use inline minimal styles if file not found
        ui.add_head_html("""
        <style>
        :root {
            --md-sys-color-primary: #6750A4;
            --md-sys-color-on-primary: #FFFFFF;
            --md-sys-color-background: #FFFBFE;
            --md-sys-color-on-background: #1D1B20;
        }
        body {
            background-color: var(--md-sys-color-background);
            color: var(--md-sys-color-on-background);
        }
        </style>
        """)

    # Add Material Symbols icon font
    ui.add_head_html("""
    <link rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200">
    <link rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap">
    <style>
    .material-symbols-outlined {
      font-family: 'Material Symbols Outlined';
      font-weight: normal;
      font-style: normal;
      font-size: 24px;
      display: inline-block;
      line-height: 1;
      text-transform: none;
      letter-spacing: normal;
      word-wrap: normal;
      white-space: nowrap;
      direction: ltr;
    }
    </style>
    """)


def toggle_theme() -> None:
    """Toggle between light and dark theme."""
    # This would be implemented with JavaScript to toggle data-theme attribute
    ui.run_javascript("""
    const root = document.documentElement;
    const currentTheme = root.getAttribute('data-theme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    root.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    """)


def initialize_theme_from_storage() -> None:
    """Initialize theme from localStorage on page load."""
    ui.run_javascript("""
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    """)
