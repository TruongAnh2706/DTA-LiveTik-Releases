"""Screenshot capture verification utility."""

from pathlib import Path


def get_html_path() -> Path:
    """Return path to renderer index.html."""
    return Path(__file__).resolve().parent.parent / "electron" / "renderer" / "index.html"
