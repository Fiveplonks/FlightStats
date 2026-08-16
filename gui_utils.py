"""Shared FlightStats GUI utilities."""

import json

from app_paths import SETTINGS_FILE

def load_home_bases():
    """Load saved home bases from the local settings file."""

    try:
        if not SETTINGS_FILE.exists():
            return []

        with SETTINGS_FILE.open(
            "r",
            encoding="utf-8",
        ) as handle:
            settings = json.load(handle)

        home_bases = settings.get(
            "home_bases",
            [],
        )

        if not isinstance(home_bases, list):
            return []

        return sorted(
            {
                str(code).strip().upper()
                for code in home_bases
                if str(code).strip()
            }
        )

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):
        return []


def save_home_bases(home_bases):
    """Persist the user's home bases."""

    SETTINGS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings = {}

    try:
        if SETTINGS_FILE.exists():
            with SETTINGS_FILE.open(
                "r",
                encoding="utf-8",
            ) as handle:
                settings = json.load(handle)

            if not isinstance(settings, dict):
                settings = {}

    except (
        OSError,
        json.JSONDecodeError,
    ):
        settings = {}

    settings["home_bases"] = sorted(
        {
            str(code).strip().upper()
            for code in home_bases
            if str(code).strip()
        }
    )

    with SETTINGS_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            settings,
            handle,
            indent=2,
        )


def format_hours(minutes):
    """Convert minutes into H:MM format, preserving negative values."""

    if minutes is None:
        return "—"

    sign = "-" if minutes < 0 else ""
    minutes = abs(int(minutes))

    hours, remaining_minutes = divmod(
        minutes,
        60,
    )

    return f"{sign}{hours}:{remaining_minutes:02d}"

def display_fuel_unit(unit):
    """Convert kg/h or L/h into kg or L."""

    return unit.replace("/h", "")
