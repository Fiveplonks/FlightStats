import re
from datetime import date, datetime, timedelta

import pdfplumber

from parser.models import Flight


FLIGHT_ROW_PATTERN = re.compile(
    r"""
    ^
    (?P<date>\d{2}-\d{2}-\d{4})
    \s+
    (?P<departure>[A-Z0-9]{3,4})
    \s+
    (?P<departure_time>\d{2}:\d{2})
    \s+
    (?P<arrival>[A-Z0-9]{3,4})
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


# The TOTAL TIME OF FLIGHT value appears after the registration.
# Examples:
#
#   1 26 1 26 SELF
#   2 35 2 35 SELF
#   0 48 48 SELF 1
#
# We use the final plausible HH MM pair as the logged total flight time.
LOGGED_TIME_PAIR_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2})\s+([0-5]\d)(?!\d)"
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
    Calculate flight duration from the departure and arrival clock times.

    FlightStats deliberately keeps this as the authoritative calculated
    duration. The logbook's recorded duration is validation data only.
    """

    reference_date = date.today()

    departure = datetime.combine(
        reference_date,
        departure_time,
    )

    arrival = datetime.combine(
        reference_date,
        arrival_time,
    )

    if arrival < departure:
        arrival += timedelta(days=1)

    duration = arrival - departure

    return int(
        duration.total_seconds() / 60
    )


def parse_logged_flight_minutes(rest):
    """
    Extract the logbook's recorded TOTAL TIME OF FLIGHT.

    This value is used only for discrepancy checking.
    """

    matches = list(
        LOGGED_TIME_PAIR_PATTERN.finditer(
            rest
        )
    )

    if not matches:
        return None

    hours, minutes = matches[-1].groups()

    return (
        int(hours) * 60
        + int(minutes)
    )


def parse_flight_row(line):
    """
    Parse one flight row.

    Returns:
        (Flight, discrepancy)

    or:

        (None, None)
    """

    match = FLIGHT_ROW_PATTERN.match(
        line.strip()
    )

    if not match:
        return None, None

    data = match.groupdict()

    flight_date = datetime.strptime(
        data["date"],
        "%d-%m-%Y",
    ).date()

    # Future entries in the PDF are planned/draft flights.
    # They are not completed logbook entries.
    if flight_date > date.today():
        return None, None

    departure_time = parse_time(
        data["departure_time"]
    )

    arrival_time = parse_time(
        data["arrival_time"]
    )

    # IMPORTANT:
    # Timestamp calculation remains authoritative.
    flight_minutes = calculate_flight_minutes(
        departure_time,
        arrival_time,
    )

    flight = Flight(
        date=flight_date,
        departure=data["departure"],
        departure_time=departure_time,
        arrival=data["arrival"],
        arrival_time=arrival_time,
        aircraft=data["aircraft"],
        registration=data["registration"],
        flight_minutes=flight_minutes,
    )

    logged_minutes = parse_logged_flight_minutes(
        data["rest"]
    )

    discrepancy = None

    if logged_minutes is not None:
        difference = (
            flight_minutes
            - logged_minutes
        )

        if difference != 0:
            discrepancy = {
                "type": "flight_time_discrepancy",
                "date": flight_date,
                "departure": data["departure"],
                "arrival": data["arrival"],
                "departure_time": departure_time,
                "arrival_time": arrival_time,
                "calculated_minutes": flight_minutes,
                "logged_minutes": logged_minutes,
                "difference_minutes": difference,
            }

    return flight, discrepancy


def parse_logbook(
    pdf_path,
    progress_callback=None,
    discrepancy_callback=None,
):
    """
    Parse all completed/current flight rows from a logbook PDF.

    The calculated timestamp duration remains authoritative.

    discrepancy_callback is called for every flight where the calculated
    duration differs from the duration recorded in the logbook.
    """

    flights = []

    with pdfplumber.open(pdf_path) as pdf:

        total_pages = len(
            pdf.pages
        )

        if total_pages == 0:

            if progress_callback is not None:
                progress_callback(
                    100,
                    "Logbook contains no pages",
                )

            return flights

        if progress_callback is not None:
            progress_callback(
                0,
                (
                    f"Parsing logbook "
                    f"(0/{total_pages} pages)..."
                ),
            )

        for page_number, page in enumerate(
            pdf.pages,
            start=1,
        ):

            text = page.extract_text()

            if text:

                for line in text.splitlines():

                    flight, discrepancy = (
                        parse_flight_row(line)
                    )

                    if flight is None:
                        continue

                    flights.append(
                        flight
                    )

                    if (
                        discrepancy is not None
                        and discrepancy_callback is not None
                    ):
                        discrepancy_callback(
                            discrepancy
                        )

            if progress_callback is not None:

                percent = int(
                    page_number
                    / total_pages
                    * 100
                )

                progress_callback(
                    percent,
                    (
                        "Parsing logbook "
                        f"({page_number}/{total_pages} pages) "
                        f"— {len(flights):,} flights found"
                    ),
                )

    if progress_callback is not None:
        progress_callback(
            100,
            (
                "Logbook parsing complete — "
                f"{len(flights):,} flights found"
            ),
        )

    return flights
