"""
Centralized filesystem paths for FlightStats.
"""

from pathlib import Path


APP_NAME = "FlightStats"

PROJECT_DIR = Path(__file__).resolve().parent

DOCUMENTS_DIR = (
    Path.home()
    / "Documents"
    / APP_NAME
)

APPLICATION_SUPPORT_DIR = (
    Path.home()
    / "Library"
    / "Application Support"
    / APP_NAME
)

CACHE_DIR = (
    APPLICATION_SUPPORT_DIR
    / "cache"
)

SETTINGS_FILE = (
    APPLICATION_SUPPORT_DIR
    / "settings.json"
)

# Keep the existing development logbook location for now.
DEVELOPMENT_LOGBOOK = (
    PROJECT_DIR
    / "logbook.pdf"
)


def ensure_app_directories():
    """Create FlightStats application directories when needed."""

    APPLICATION_SUPPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def get_logbook_path():
    """
    Return the current logbook path.

    The development version continues to use the existing
    project-level logbook.pdf. We can switch this to
    Documents/FlightStats when packaging the Mac app.
    """

    return DEVELOPMENT_LOGBOOK
