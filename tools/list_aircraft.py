from collections import Counter

from parser.easa_pdf import parse_logbook


def main():
    print("=" * 60)
    print("FLIGHTSTATS AIRCRAFT ANALYSIS")
    print("=" * 60)

    print("\nParsing logbook...")

    flights = parse_logbook(
        "logbook.pdf"
    )

    aircraft = Counter(
        flight.aircraft
        for flight in flights
    )

    print(
        f"\nTotal flights: "
        f"{len(flights)}"
    )

    print(
        f"Unique aircraft types: "
        f"{len(aircraft)}"
    )

    print("\nAircraft types:")
    print("-" * 60)

    for aircraft_type, count in (
        aircraft.most_common()
    ):
        print(
            f"{aircraft_type:<20} "
            f"{count:>5} flights"
        )

    print(
        "\n" + "=" * 60
    )


if __name__ == "__main__":
    main()