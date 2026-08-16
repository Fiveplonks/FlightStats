"""Centralized, platform-independent filesystem paths for FlightStats."""

import os
import shutil
import sys
from pathlib import Path

APP_NAME = "FlightStats"
PROJECT_DIR = Path(__file__).resolve().parent


def _bundle_root():
    """Return the directory containing bundled application resources."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    return PROJECT_DIR


def _user_data_root():
    """
    Return the platform-specific user data directory.

    macOS:
        ~/Library/Application Support/FlightStats

    Windows:
        %APPDATA%/FlightStats

    Linux / other Unix:
        $XDG_DATA_HOME/FlightStats
        or ~/.local/share/FlightStats
    """

    if sys.platform == "darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / APP_NAME
        )

    if sys.platform == "win32":
        appdata = Path(
            os.environ.get(
                "APPDATA",
                Path.home() / "AppData" / "Roaming",
            )
        )

        return appdata / APP_NAME

    xdg_data_home = Path(
        os.environ.get(
            "XDG_DATA_HOME",
            Path.home() / ".local" / "share",
        )
    )

    return xdg_data_home / APP_NAME


BUNDLE_ROOT = _bundle_root()

RESOURCE_DATA_DIR = (
    BUNDLE_ROOT / "data"
)

BUNDLED_AIRPORT_DATABASE = (
    RESOURCE_DATA_DIR / "airports.csv"
)

BUNDLED_FUEL_DATABASE = (
    RESOURCE_DATA_DIR / "aircraft_fuel_burn.csv"
)

BUNDLED_LOGBOOK = (
    BUNDLE_ROOT / "logbook.pdf"
)

APPLICATION_SUPPORT_DIR = _user_data_root()

CACHE_DIR = (
    APPLICATION_SUPPORT_DIR / "cache"
)

SETTINGS_FILE = (
    APPLICATION_SUPPORT_DIR / "settings.json"
)

USER_CUSTOM_AIRPORT_DATABASE = (
    APPLICATION_SUPPORT_DIR / "custom_airports.csv"
)

USER_AIRPORT_DATABASE = (
    APPLICATION_SUPPORT_DIR / "airports.csv"
)

USER_AIRPORT_METADATA = (
    APPLICATION_SUPPORT_DIR / "airport_database.json"
)

USER_FUEL_DATABASE = (
    APPLICATION_SUPPORT_DIR / "aircraft_fuel_burn.csv"
)


DEVELOPMENT_LOGBOOK = (
    PROJECT_DIR / "logbook.pdf"
)

DOCUMENTS_DIR = (
    Path.home() / "Documents" / APP_NAME
)

DOCUMENTS_LOGBOOK = (
    DOCUMENTS_DIR / "logbook.pdf"
)


def ensure_app_directories():
    """Create FlightStats' writable application directories."""
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
    Return the user's FlightStats logbook.

    Development:
        Uses the project-level logbook.pdf.

    Packaged application:
        Uses ~/Documents/FlightStats/logbook.pdf.

        On first packaged launch, a bundled logbook is copied there
        if one is present.
    """

    if not getattr(sys, "frozen", False):
        return DEVELOPMENT_LOGBOOK

    ensure_app_directories()

    if DOCUMENTS_LOGBOOK.exists():
        return DOCUMENTS_LOGBOOK

    if BUNDLED_LOGBOOK.exists():
        DOCUMENTS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            BUNDLED_LOGBOOK,
            DOCUMENTS_LOGBOOK,
        )

        return DOCUMENTS_LOGBOOK

    return DOCUMENTS_LOGBOOK


def migrate_file_if_needed(
    source,
    destination,
):
    """Copy a legacy file only when the new location does not exist."""

    source = Path(source)
    destination = Path(destination)

    if (
        destination.exists()
        or not source.exists()
    ):
        return False

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        source,
        destination,
    )

    return True
