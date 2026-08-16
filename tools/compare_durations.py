import re
from datetime import datetime

import pdfplumber


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


OFFICIAL_TIME_PATTERN = re.compile(
    r"(?:^|\s)(?:(\d{1,2})\s+)?(\d{2})(?:\s|$)"
)


def format_minutes(minutes):
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}:{mins:02d}"


def parse_time(value):
    if not value:
        return None

    return datetime.strptime(
        value,
        "%H:%M",
    ).time()


def calculate_duration(
    departure_time,
    arrival_time,
):
    departure_minutes = (
        departure_time.hour * 60
        + departure_time.minute
    )

    arrival_minutes = (
        arrival_time.hour * 60
        + arrival_time.minute
    )

    if arrival_minutes < departure_minutes:
        arrival_minutes += 24 * 60

    return arrival_minutes - departure_minutes


def extract_official_duration(rest):
    match = OFFICIAL_TIME_PATTERN.search(rest)

    if not match:
        return None

    hours_text, minutes_text = match.groups()

    hours = (
        int(hours_text)
        if hours_text is not None
        else 0
    )

    minutes = int(minutes_text)

    if minutes >= 60:
        return None

    return hours * 60 + minutes


def main():
    print("=" * 80)
    print("FLIGHTSTATS DEPARTURE/ARRIVAL DURATION DIAGNOSTIC")
    print("=" * 80)

    print("\nOpening logbook...")

    mismatches = []
    missing_official = []

    total_calculated = 0
    total_official = 0
    total_flights = 0

    with pdfplumber.open("logbook.pdf") as pdf:
        total_pages = len(pdf.pages)

        print(f"Pages found: {total_pages}\n")

        for page_number, page in enumerate(
            pdf.pages,
            start=1,
        ):
            text = page.extract_text()

            page_flights = 0

            if text:
                for line in text.splitlines():
                    line = line.strip()

                    match = FLIGHT_ROW_PATTERN.match(line)

                    if not match:
                        continue

                    data = match.groupdict()

                    departure_time = parse_time(
                        data["departure_time"]
                    )

                    arrival_time = parse_time(
                        data["arrival_time"]
                    )

                    calculated = calculate_duration(
                        departure_time,
                        arrival_time,
                    )

                    official = extract_official_duration(
                        data["rest"]
                    )

                    total_flights += 1
                    page_flights += 1

                    total_calculated += calculated

                    if official is None:
                        missing_official.append(
                            {
                                "page": page_number,
                                "line": line,
                                "calculated": calculated,
                                "rest": data["rest"],
                            }
                        )
                        continue

                    total_official += official

                    if calculated != official:
                        mismatches.append(
                            {
                                "page": page_number,
                                "line": line,
                                "calculated": calculated,
                                "official": official,
                            }
                        )

            print(
                f"Processing page "
                f"{page_number}/{total_pages}... "
                f"{page_flights} flights"
            )

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nTotal flights: {total_flights}")

    print(
        f"Calculated from departure/arrival: "
        f"{format_minutes(total_calculated)}"
    )

    print(
        f"Official durations successfully extracted: "
        f"{format_minutes(total_official)}"
    )

    difference = total_calculated - total_official

    print(
        f"Difference: "
        f"{format_minutes(abs(difference))}"
    )

    print(
        f"\nFlights with official duration NOT extracted: "
        f"{len(missing_official)}"
    )

    if missing_official:
        print("\n" + "-" * 80)
        print("OFFICIAL DURATION EXTRACTION FAILURES")
        print("-" * 80)

        for item in missing_official:
            print(
                f"\nPDF page {item['page']}"
            )

            print(
                f"Calculated duration: "
                f"{format_minutes(item['calculated'])}"
            )

            print(
                f"Extracted remainder: "
                f"{item['rest']}"
            )

            print(
                f"Full row:\n"
                f"{item['line']}"
            )

    print(
        f"\nFlights where calculated duration "
        f"differs from extracted official duration: "
        f"{len(mismatches)}"
    )

    if mismatches:
        print("\n" + "-" * 80)
        print("DURATION MISMATCHES")
        print("-" * 80)

        for item in mismatches:
            difference = (
                item["calculated"]
                - item["official"]
            )

            print(
                f"\nPDF page {item['page']}"
            )

            print(
                f"Calculated: "
                f"{format_minutes(item['calculated'])}"
            )

            print(
                f"Official:   "
                f"{format_minutes(item['official'])}"
            )

            print(
                f"Difference: "
                f"{format_minutes(abs(difference))}"
            )

            print(item["line"])

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()