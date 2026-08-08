import re

import pdfplumber


FLIGHT_START = re.compile(
    r"^\d{2}-\d{2}-\d{4}\s+"
)

PAGE_TOTAL = re.compile(
    r"TOTAL THIS PAGE\s+(\d+):(\d{2})"
)


def format_minutes(total_minutes):
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}:{minutes:02d}"


def parse_time_to_minutes(hours, minutes):
    return int(hours) * 60 + int(minutes)


def main():
    print("=" * 80)
    print("FLIGHTSTATS PAGE-BY-PAGE TIME DIAGNOSTIC")
    print("=" * 80)

    print("\nOpening logbook...")

    with pdfplumber.open("logbook.pdf") as pdf:
        total_pages = len(pdf.pages)

        print(f"Pages found: {total_pages}")
        print()

        total_parsed_minutes = 0
        total_official_minutes = 0

        mismatches = []

        for page_number, page in enumerate(
            pdf.pages,
            start=1,
        ):
            text = page.extract_text()

            page_parsed_minutes = 0
            flight_rows = []

            if text:
                lines = text.splitlines()

                for line in lines:
                    line = line.strip()

                    if not FLIGHT_START.match(line):
                        continue

                    parts = line.split()

                    if len(parts) < 8:
                        continue

                    # The first seven fields are:
                    #
                    # date
                    # departure
                    # departure time
                    # arrival
                    # arrival time
                    # aircraft
                    # registration
                    #
                    # Everything after that contains the
                    # flight-time columns and other data.

                    rest = parts[7:]

                    # Find the first hour/minute pair after
                    # the registration.
                    time_match = re.search(
                        r"(?:^|\s)(?:(\d{1,2})\s+)?(\d{2})(?:\s|$)",
                        " ".join(rest),
                    )

                    if not time_match:
                        continue

                    hours_text, minutes_text = (
                        time_match.groups()
                    )

                    if hours_text is None:
                        hours = 0
                    else:
                        hours = int(hours_text)

                    minutes = int(minutes_text)

                    flight_minutes = (
                        hours * 60 + minutes
                    )

                    page_parsed_minutes += (
                        flight_minutes
                    )

                    flight_rows.append(
                        (
                            line,
                            flight_minutes,
                        )
                    )

                # Look for the official PDF page total.
                official_match = PAGE_TOTAL.search(text)

                if official_match:
                    official_hours = int(
                        official_match.group(1)
                    )

                    official_minutes = int(
                        official_match.group(2)
                    )

                    page_official_minutes = (
                        official_hours * 60
                        + official_minutes
                    )

                    total_official_minutes += (
                        page_official_minutes
                    )

                    total_parsed_minutes += (
                        page_parsed_minutes
                    )

                    difference = (
                        page_parsed_minutes
                        - page_official_minutes
                    )

                    if difference == 0:
                        status = "✓"
                    else:
                        status = "✗"

                        mismatches.append(
                            (
                                page_number,
                                page_parsed_minutes,
                                page_official_minutes,
                                difference,
                                flight_rows,
                            )
                        )

                    print(
                        f"Page "
                        f"{page_number:3d}/{total_pages}  "
                        f"{status}  "
                        f"parsed "
                        f"{format_minutes(page_parsed_minutes):>7}  |  "
                        f"PDF total "
                        f"{format_minutes(page_official_minutes):>7}"
                    )

                else:
                    print(
                        f"Page "
                        f"{page_number:3d}/{total_pages}  "
                        f"?  No 'TOTAL THIS PAGE' found"
                    )

            else:
                print(
                    f"Page "
                    f"{page_number:3d}/{total_pages}  "
                    f"?  No text extracted"
                )

        # -----------------------------------------------------
        # Final summary
        # -----------------------------------------------------

        print("\n" + "=" * 80)
        print("DIAGNOSTIC SUMMARY")
        print("=" * 80)

        print(
            f"\nPages processed: "
            f"{total_pages}"
        )

        print(
            f"Parsed flight time: "
            f"{format_minutes(total_parsed_minutes)}"
        )

        print(
            f"Official page totals: "
            f"{format_minutes(total_official_minutes)}"
        )

        total_difference = (
            total_parsed_minutes
            - total_official_minutes
        )

        print(
            f"Overall difference: "
            f"{format_minutes(abs(total_difference))}"
        )

        if total_difference == 0:
            print(
                "\n✓ PERFECT MATCH"
            )
        elif total_difference < 0:
            print(
                "\n✗ Parser is SHORT by "
                f"{format_minutes(abs(total_difference))}"
            )
        else:
            print(
                "\n✗ Parser is OVER by "
                f"{format_minutes(total_difference)}"
            )

        # -----------------------------------------------------
        # Detailed mismatches
        # -----------------------------------------------------

        print(
            f"\nPages with mismatches: "
            f"{len(mismatches)}"
        )

        if mismatches:
            print("\n" + "-" * 80)
            print("MISMATCH DETAILS")
            print("-" * 80)

            for (
                page_number,
                parsed,
                official,
                difference,
                flight_rows,
            ) in mismatches:

                print(
                    f"\nPAGE {page_number}"
                )

                print(
                    f"Parsed:   "
                    f"{format_minutes(parsed)}"
                )

                print(
                    f"Official: "
                    f"{format_minutes(official)}"
                )

                if difference < 0:
                    print(
                        f"Missing:  "
                        f"{format_minutes(abs(difference))}"
                    )
                else:
                    print(
                        f"Excess:   "
                        f"{format_minutes(difference)}"
                    )

                print(
                    f"Flight rows found: "
                    f"{len(flight_rows)}"
                )

                print("\nRows parsed from this page:")

                for line, minutes in flight_rows:
                    print(
                        f"  "
                        f"{format_minutes(minutes):>6}  "
                        f"{line}"
                    )

        print("\n" + "=" * 80)


if __name__ == "__main__":
    main()