"""
CSV flight-logbook parser for FlightStats.

This is Milestone 2: CSV input is parsed into the same Flight objects
used by the existing PDF parser. It does not modify the PDF parser or
the data manager.

Expected columns:
    date
    departure
    departure_time
    flight_number
    arrival
    arrival_time
    aircraft
    registration

flight_number is accepted but is not currently stored on Flight because
the existing Flight model does not contain that field.
"""

from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path

from parser.models import Flight


REQUIRED_COLUMNS = {
    "date",
    "departure",
    "departure_time",
    "arrival",
    "arrival_time",
    "aircraft",
    "registration",
}

HEADER_ALIASES = {
    "flight": "flight_number",
    "flight_no": "flight_number",
    "flight_number": "flight_number",
    "dep": "departure",
    "departure_airport": "departure",
    "arr": "arrival",
    "arrival_airport": "arrival",
    "dep_time": "departure_time",
    "departure_time": "departure_time",
    "arr_time": "arrival_time",
    "arrival_time": "arrival_time",
    "aircraft_type": "aircraft",
    "aircraft": "aircraft",
    "registration": "registration",
    "reg": "registration",
}


def _normalise_header(value):
    """Normalize a CSV column heading."""
    value = (
        str(value)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )

    return HEADER_ALIASES.get(
        value,
        value,
    )


def _parse_date(value):
    """Parse the supported FlightStats CSV date formats."""
    value = str(value).strip()

    for fmt in (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ):
        try:
            return datetime.strptime(
                value,
                fmt,
            ).date()
        except ValueError:
            pass

    raise ValueError(
        f"Unsupported date format: {value!r}"
    )


def _parse_time(value):
    """Parse HH:MM or HHMM."""
    value = str(value).strip()

    for fmt in (
        "%H:%M",
        "%H%M",
    ):
        try:
            return datetime.strptime(
                value,
                fmt,
            ).time()
        except ValueError:
            pass

    raise ValueError(
        f"Unsupported time format: {value!r}"
    )


def _calculate_flight_minutes(
    departure_time,
    arrival_time,
):
    """
    Calculate flight duration.

    If arrival time is earlier than departure time, the flight is
    assumed to have arrived after midnight, matching the PDF parser.
    """
    today = datetime.today().date()

    departure = datetime.combine(
        today,
        departure_time,
    )

    arrival = datetime.combine(
        today,
        arrival_time,
    )

    if arrival < departure:
        arrival += timedelta(days=1)

    return int(
        (arrival - departure).total_seconds()
        / 60
    )


def parse_csv(csv_path):
    """
    Parse a FlightStats CSV logbook.

    Returns:
        list[Flight]

    Raises:
        FileNotFoundError: input file does not exist.
        ValueError: CSV structure or a row is invalid.
    """
    path = Path(csv_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"CSV logbook not found: {path}"
        )

    flights = []

    print("Opening CSV logbook...")

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if reader.fieldnames is None:
            raise ValueError(
                "CSV logbook has no header row."
            )

        reader.fieldnames = [
            _normalise_header(header)
            for header in reader.fieldnames
        ]

        missing = REQUIRED_COLUMNS - set(
            reader.fieldnames
        )

        if missing:
            raise ValueError(
                "CSV logbook is missing required columns: "
                + ", ".join(sorted(missing))
            )

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            # Ignore completely blank lines.
            if not any(
                str(value or "").strip()
                for value in row.values()
            ):
                continue

            try:
                flight_date = _parse_date(
                    row["date"]
                )

                departure_time = _parse_time(
                    row["departure_time"]
                )

                arrival_time = _parse_time(
                    row["arrival_time"]
                )

                departure = (
                    str(row["departure"])
                    .strip()
                    .upper()
                )

                arrival = (
                    str(row["arrival"])
                    .strip()
                    .upper()
                )

                aircraft = (
                    str(row["aircraft"])
                    .strip()
                )

                registration = (
                    str(row["registration"])
                    .strip()
                )

                if not departure:
                    raise ValueError(
                        "departure is empty"
                    )

                if not arrival:
                    raise ValueError(
                        "arrival is empty"
                    )

                if not aircraft:
                    raise ValueError(
                        "aircraft is empty"
                    )

                if not registration:
                    raise ValueError(
                        "registration is empty"
                    )

                flights.append(
                    Flight(
                        date=flight_date,
                        departure=departure,
                        departure_time=departure_time,
                        arrival=arrival,
                        arrival_time=arrival_time,
                        aircraft=aircraft,
                        registration=registration,
                        flight_minutes=(
                            _calculate_flight_minutes(
                                departure_time,
                                arrival_time,
                            )
                        ),
                    )
                )

            except (KeyError, ValueError) as error:
                raise ValueError(
                    f"Invalid CSV row {row_number}: "
                    f"{error}"
                ) from error

    print(
        f"CSV parsing complete. "
        f"Flights found: {len(flights)}"
    )

    return flights
