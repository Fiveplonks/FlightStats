"""Presentation-level unit preferences and conversions for FlightStats."""

import json

from app_paths import SETTINGS_FILE


DISTANCE_UNITS = ("km", "NM", "mi")
FUEL_UNITS = ("kg/h", "L/h", "USG/h")

# Standard reference densities used only for presentation conversion.
# Stored fuel data remains in its original/canonical unit.
JET_FUEL_DENSITY_KG_L = 0.804
AVGAS_DENSITY_KG_L = 0.721


def _load_settings():
    try:
        if not SETTINGS_FILE.exists():
            return {}
        with SETTINGS_FILE.open("r", encoding="utf-8") as handle:
            settings = json.load(handle)
        return settings if isinstance(settings, dict) else {}
    except (OSError, json.JSONDecodeError, TypeError):
        return {}


def _save_settings(settings):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SETTINGS_FILE.open("w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)


def load_unit_preferences():
    """Return persisted presentation units."""
    settings = _load_settings()
    distance = settings.get("distance_unit", "km")
    fuel = settings.get("fuel_unit", "kg/h")

    if distance not in DISTANCE_UNITS:
        distance = "km"
    if fuel not in FUEL_UNITS:
        fuel = "kg/h"

    return {
        "distance_unit": distance,
        "fuel_unit": fuel,
    }


def save_unit_preferences(distance_unit, fuel_unit):
    """Persist presentation units without touching flight data."""
    if distance_unit not in DISTANCE_UNITS:
        raise ValueError(f"Unsupported distance unit: {distance_unit}")
    if fuel_unit not in FUEL_UNITS:
        raise ValueError(f"Unsupported fuel unit: {fuel_unit}")

    settings = _load_settings()
    settings["distance_unit"] = distance_unit
    settings["fuel_unit"] = fuel_unit
    _save_settings(settings)


def convert_distance_km(value_km, target_unit):
    """Convert a stored kilometre value to the selected display unit."""
    if value_km is None:
        return None
    factors = {"km": 1.0, "NM": 1.0 / 1.852, "mi": 1.0 / 1.609344}
    if target_unit not in factors:
        raise ValueError(f"Unsupported distance unit: {target_unit}")
    return float(value_km) * factors[target_unit]


def convert_fuel_flow(value, source_unit, target_unit):
    """Convert a fuel-flow value for presentation.

    ``kg/h`` is treated as Jet A/Jet A-1 and ``L/h`` as avgas because
    those are the two source units currently used by FlightStats.
    """
    if value is None:
        return None
    if source_unit not in {"kg/h", "L/h"}:
        raise ValueError(f"Unsupported source fuel unit: {source_unit}")
    if target_unit not in FUEL_UNITS:
        raise ValueError(f"Unsupported target fuel unit: {target_unit}")

    value = float(value)

    if source_unit == target_unit:
        return value

    if source_unit == "kg/h":
        litres = value / JET_FUEL_DENSITY_KG_L
        if target_unit == "L/h":
            return litres
        if target_unit == "USG/h":
            return litres / 3.785411784
        return value

    # Source is L/h of avgas.
    if target_unit == "kg/h":
        return value * AVGAS_DENSITY_KG_L
    if target_unit == "USG/h":
        return value / 3.785411784
    return value


def format_distance(value_km, target_unit, decimals=1):
    value = convert_distance_km(value_km, target_unit)
    if value is None:
        return "—"
    return f"{value:,.{decimals}f} {target_unit}"


def format_fuel_flow(value, source_unit, target_unit, decimals=1):
    value = convert_fuel_flow(value, source_unit, target_unit)
    if value is None:
        return "—"
    return f"{value:,.{decimals}f} {target_unit}"


def format_fuel_quantity(value, source_unit, target_unit, decimals=1):
    """Format a fuel quantity using the same density assumptions as flow."""
    if value is None:
        return "—"
    return format_fuel_flow(value, source_unit, target_unit, decimals)


class UnitSettings:
    """Small state holder shared by GUI pages."""

    def __init__(self):
        self.load()

    def load(self):
        preferences = load_unit_preferences()
        self.distance_unit = preferences["distance_unit"]
        self.fuel_unit = preferences["fuel_unit"]

    def save(self, distance_unit, fuel_unit):
        save_unit_preferences(distance_unit, fuel_unit)
        self.distance_unit = distance_unit
        self.fuel_unit = fuel_unit
