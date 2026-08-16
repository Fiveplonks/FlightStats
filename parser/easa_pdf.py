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


# Standard EASA AMC1 FCL.050 flight-row format.
#
# The single-pilot SE/ME columns may be empty. Therefore the
# extracted row can contain either two or three HH MM pairs:
#
#   2 26 2 26
#
# or:
#
#   1 10 2 05 3 15
#
# The final pair is TOTAL TIME OF FLIGHT.
STANDARD_EASA_FLIGHT_ROW_PATTERN = re.compile(
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
    (?P<time_pairs>
        \d{1,2}\s+[0-5]\d
        (?:\s+\d{1,2}\s+[0-5]\d){1,2}
    )
    (?P<tail>.*)
    $
    """,
    re.VERBOSE,
)


# Logged total flight time in the Belgian CAA format.
#
# Examples:
#
#   1 26 1 26 SELF
#   2 35 2 35 SELF
#   0 48 48 SELF 1
#
# The final plausible HH MM pair is the recorded total.
LOGGED_TIME_PAIR_PATTERN = re.compile(
    r"(?<!\d)(\d{1,2})\s+([0-5]\d)(?!\d)"
)


# Carried-forward flight time from previous logbook pages.
#
# Example:
#
#   TOTAL FROM 3.839:59
#   PREVIOUS PAGES
#
# This is metadata only. It is read once from the first
# applicable flight-entry page and is never added to the
# calculated flight-time pipeline.
PREVIOUS_EXPERIENCE_PATTERN = re.compile(
    r"TOTAL\s+FROM\s+PREVIOUS\s+PAGES\s+([0-9.]+):([0-5]\d)",
    re.IGNORECASE,
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


def parse_captain_from_tail(tail):
    """
    Extract the PIC name from an EASA/Belgian CAA row tail.

    The Belgian CAA format may still contain the final HH MM
    flight-time pair in the supplied text:

        X 1 20 Kevin Quanten 2
            -> Kevin Quanten

    The standard EASA format has already separated the time pairs
    from the tail, so the supplied text may simply be:

        SCHOLLAERT Michel

    or:

        SCHOLLAERT Michel 1 1

    Trailing numeric landing columns are removed.
    """

    value = str(tail or "").strip()

    if not value:
        return None

    # Belgian CAA rows may still contain the final HH MM pair.
    matches = list(
        LOGGED_TIME_PAIR_PATTERN.finditer(
            value
        )
    )

    if matches:
        value = value[
            matches[-1].end():
        ].strip()

    # Remove trailing numeric landing-count columns.
    parts = value.split()

    while parts and re.fullmatch(
        r"\d+",
        parts[-1],
    ):
        parts.pop()

    captain = " ".join(parts).strip()

    return captain or None



def parse_flight_row(line):
    """
    Parse one flight row.

    Returns:
        (Flight, discrepancy)

    or:

        (None, None)
    """

    stripped_line = line.strip()

    # -----------------------------------------------------
    # TRY STANDARD EASA FCL.050 FORMAT FIRST
    # -----------------------------------------------------
    #
    # In the standard EASA layout the Total Time of Flight
    # is an explicit column. PDF extraction represents the
    # time columns as HH MM pairs.
    #
    # The final pair in time_pairs is therefore the logged
    # Total Time of Flight.
    #
    # Example:
    #
    #   18-01-2017 EHAM 19:57 LIRF 22:23
    #   737-700 PH-BGT 2 26 2 26 1
    #
    #                           ^^^^^
    #                           total
    #
    standard_match = (
        STANDARD_EASA_FLIGHT_ROW_PATTERN.match(
            stripped_line
        )
    )

    if standard_match:
        data = standard_match.groupdict()
        source_format = "standard_easa"

    else:
        # -------------------------------------------------
        # FALL BACK TO BELGIAN CAA FORMAT
        # -------------------------------------------------

        match = FLIGHT_ROW_PATTERN.match(
            stripped_line
        )

        if not match:
            return None, None

        data = match.groupdict()
        source_format = "belgian_caa"

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

    if source_format == "standard_easa":
        captain = parse_captain_from_tail(
            data["tail"]
        )

        time_pairs = list(
            re.finditer(
                r"(?<!\d)(\d{1,2})\s+([0-5]\d)(?!\d)",
                data["time_pairs"],
            )
        )

        if time_pairs:
            hours, minutes = time_pairs[-1].groups()

            logged_minutes = (
                int(hours) * 60
                + int(minutes)
            )
        else:
            logged_minutes = None

    else:
        captain = parse_captain_from_tail(
            data["rest"]
        )

        logged_minutes = parse_logged_flight_minutes(
            data["rest"]
        )

    # -----------------------------------------------------
    # VALIDATE SOURCE LOGBOOK TIME
    # -----------------------------------------------------
    #
    # The logbook's Total Time of Flight can legitimately
    # differ substantially from the timestamp-derived
    # duration, particularly on relief flights.
    #
    # Therefore we do not require the two values to match.
    #
    # Extremely small logged values are treated as
    # suspicious. The original source value is preserved.
    #

    if logged_minutes is None:
        logged_time_status = "missing"

    elif (
        flight_minutes > 0
        and logged_minutes / flight_minutes < 0.30
    ):
        logged_time_status = "suspicious"

    else:
        logged_time_status = "valid"

    flight = Flight(
        date=flight_date,
        departure=data["departure"],
        departure_time=departure_time,
        arrival=data["arrival"],
        arrival_time=arrival_time,
        aircraft=data["aircraft"],
        registration=data["registration"],
        flight_minutes=flight_minutes,
        captain=captain,
        logged_flight_minutes=logged_minutes,
        logged_time_status=logged_time_status,
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
                "logged_time_status": logged_time_status,
            }

    return flight, discrepancy


def parse_logbook(
    pdf_path,
    progress_callback=None,
    discrepancy_callback=None,
    previous_experience_callback=None,
    flight_callback=None,
):
    """
    Parse all completed/current flight rows from a logbook PDF.

    The calculated timestamp duration remains authoritative.

    discrepancy_callback is called for every flight where the calculated
    duration differs from the duration recorded in the logbook.

    previous_experience_callback is called once with the carried-forward
    flight time from the first flight-entry page. This value is metadata
    and is not added to the parsed flight records.
    """

    flights = []

    previous_experience_minutes = None

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

                # The right-hand pages contain the flight-entry
                # table. In this logbook format these are odd-numbered
                # PDF pages.
                #
                # Only the FIRST such page may provide the
                # "TOTAL FROM PREVIOUS PAGES" value. Later pages
                # contain cumulative carry-forward totals and must
                # be ignored.

                is_first_flight_entry_page = (
                    page_number % 2 == 1
                    and previous_experience_minutes is None
                )

                if is_first_flight_entry_page:
                    previous_match = (
                        PREVIOUS_EXPERIENCE_PATTERN.search(
                            text
                        )
                    )

                    if previous_match is not None:
                        hours_text = (
                            previous_match.group(1)
                            .replace(
                                ".",
                                "",
                            )
                        )

                        minutes = int(
                            previous_match.group(2)
                        )

                        previous_experience_minutes = (
                            int(hours_text) * 60
                            + minutes
                        )

                        if (
                            previous_experience_callback
                            is not None
                        ):
                            previous_experience_callback(
                                previous_experience_minutes
                            )

                for line in text.splitlines():

                    flight, discrepancy = (
                        parse_flight_row(line)
                    )

                    if flight is None:
                        continue

                    flights.append(
                        flight
                    )

                    if flight_callback is not None:
                        flight_callback(
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
