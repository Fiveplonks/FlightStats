import re
from datetime import datetime, timedelta

import pdfplumber

from parser.models import Flight


FLIGHT_ROW_PATTERN = re.compile(
    r"""
    ^
    (?P<date>\d{2}-\d{2}-\d{4})
    \s+
    (?P<departure>[A-Z0-9]{4})
    \s+
    (?P<departure_time>\d{2}:\d{2})
    \s+
    (?P<arrival>[A-Z0-9]{4})
    \s+
    (?P<arrival_time>\d{2}:\d{2})
    \s+
    (?P<aircraft>\S+)
    \s+
    (?P<registration>\S+)
    \s+
    (?P<rest>.*)
    $
    """,
    re.VERBOSE,
)


def parse_time(value):
    """Convert HH:MM text into a time object."""
    return datetime.strptime(
        value,
        "%H:%M",
    ).time()


def calculate_flight_minutes(
    departure_time,
    arrival_time,
):
    """
    Calculate flight duration from UTC departure
    and arrival times.

    If arrival is earlier than departure, assume
    the flight arrived the following UTC day.
    """

    departure = datetime.combine(
        datetime.today(),
        departure_time,
    )

    arrival = datetime.combine(
        datetime.today(),
        arrival_time,
    )

    if arrival < departure:
        arrival += timedelta(days=1)

    duration = arrival - departure

    return int(duration.total_seconds() / 60)


def parse_flight_row(line):
    """Parse one flight row from the PDF."""

    match = FLIGHT_ROW_PATTERN.match(
        line.strip()
    )

    if not match:
        return None

    data = match.groupdict()

    flight_date = datetime.strptime(
        data["date"],
        "%d-%m-%Y",
    ).date()

    departure_time = parse_time(
        data["departure_time"]
    )

    arrival_time = parse_time(
        data["arrival_time"]
    )

    flight_minutes = calculate_flight_minutes(
        departure_time,
        arrival_time,
    )

    return Flight(
        date=flight_date,
        departure=data["departure"],
        departure_time=departure_time,
        arrival=data["arrival"],
        arrival_time=arrival_time,
        aircraft=data["aircraft"],
        registration=data["registration"],
        flight_minutes=flight_minutes,
    )


def parse_logbook(pdf_path):
    """Parse all flight rows from a logbook PDF."""

    flights = []

    print("Opening logbook...")

    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)

        print(
            f"Pages found: {total_pages}"
        )

        for page_number, page in enumerate(
            pdf.pages,
            start=1,
        ):
            text = page.extract_text()

            page_flights = 0

            if text:
                for line in text.splitlines():
                    flight = parse_flight_row(line)

                    if flight is not None:
                        flights.append(flight)
                        page_flights += 1

            print(
                f"Processing page "
                f"{page_number}/{total_pages}... "
                f"{page_flights} flights"
            )

    print(
        f"\nParsing complete. "
        f"Flights found: {len(flights)}"
    )

    return flights