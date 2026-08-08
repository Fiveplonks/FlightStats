from parser.airports import AirportDatabase
from parser.easa_pdf import parse_logbook
from parser.flight_analysis import (
    calculate_all_distances,
    total_distance_km,
)


def main():
    print("=" * 70)
    print("FLIGHTSTATS CAREER DISTANCE TEST")
    print("=" * 70)

    print("\nLoading airport database...")

    airport_database = AirportDatabase()

    print("\nParsing logbook...")

    flights = parse_logbook(
        "logbook.pdf"
    )

    print(
        f"\nFlights found: {len(flights)}"
    )

    print("\nCalculating distances...")

    flight_distances = (
        calculate_all_distances(
            flights,
            airport_database,
        )
    )

    total_distance = total_distance_km(
        flight_distances
    )

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)

    print(
        f"\nTotal flights: "
        f"{len(flights)}"
    )

    print(
        f"Total distance: "
        f"{total_distance:,.1f} km"
    )

    print(
        f"Total distance: "
        f"{total_distance / 1_000_000:.3f} million km"
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()