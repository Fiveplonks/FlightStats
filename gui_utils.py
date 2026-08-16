"""Shared FlightStats GUI utilities."""

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

