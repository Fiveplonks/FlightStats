import re
from datetime import datetime

import pdfplumber

from parser.models import Flight


FLIGHT_ROW_PATTERN = re.compile(
    r"""
    ^
    (?P<date>\d{2}-\d{2}-\d{4})
    \s+

    (?P<departure>[A-Z0-9]{4})
    \s+

    (?:
        (?P<departure_time>\d{2}:\d{2})
        \s+
    )?

    (?P<arrival>[A-Z0-9]{4})
    \s+

    (?:
        (?P<arrival_time>\d{2}:\d{2})
        \s+
    )?

    (?P<aircraft>\S+)
    \s+

    (?P<registration>\S+)
    \s+

    (?P<rest>.*)
    $
    """,
    re.VERBOSE,
)


def parse_optional_time(value):
    """Convert HH:MM text into a time object.

    Returns None when no time was recorded.
    """

    if not value:
        return None

    return datetime.strptime(
        value,
        "%H:%M",
    ).time()


def calculate_flight_minutes(
    departure_time,
    arrival_time,
):
    """Calculate elapsed flight time.

    Both times are assumed to be UTC.

    If the arrival time is earlier than the departure time,
    the flight is assumed to have crossed midnight.
    """

    if departure_time is None or arrival_time is None:
        return None

    departure_minutes = (
        departure_time.hour * 60
        + departure_time.minute
    )

    arrival_minutes = (
        arrival_time.hour * 60
        + arrival_time.minute
    )

    # Overnight flight.
    if arrival_minutes < departure_minutes:
        arrival_minutes += 24 * 60

    return arrival_minutes - departure_minutes


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

    departure_time = parse_optional_time(
        data["departure_time"]
    )

    arrival_time = parse_optional_time(
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

    flights_without_duration = sum(
        flight.flight_minutes is None
        for flight in flights
    )

    print(
        f"\nParsing complete. "
        f"Flights found: {len(flights)}"
    )

    print(
        f"Flights with calculated duration: "
        f"{len(flights) - flights_without_duration}"
    )

    print(
        f"Flights missing departure/arrival time: "
        f"{flights_without_duration}"
    )

    return flights