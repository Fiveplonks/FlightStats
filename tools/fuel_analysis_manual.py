from parser.easa_pdf import parse_logbook
from parser.fuel import FuelDatabase
from parser.fuel_analysis import (
    calculate_all_fuel,
    summarize_fuel,
)


def format_hours(minutes):
    """Convert minutes into H:MM format."""

    hours = minutes // 60
    remaining_minutes = minutes % 60

    return f"{hours}:{remaining_minutes:02d}"


def display_fuel_unit(unit):
    """Convert a fuel-burn unit into a fuel quantity unit."""

    return unit.replace("/h", "")


def main():
    print("=" * 70)
    print("FLIGHTSTATS FUEL ANALYSIS")
    print("=" * 70)

    print("\nLoading fuel database...")

    fuel_database = FuelDatabase()

    print(
        f"Fuel profiles loaded: "
        f"{len(fuel_database.aircraft)}"
    )

    print("\nParsing logbook...")

    flights = parse_logbook(
        "logbook.pdf"
    )

    print(
        f"\nFlights found: "
        f"{len(flights)}"
    )

    print(
        "\nCalculating estimated fuel..."
    )

    fuel_results = calculate_all_fuel(
        flights,
        fuel_database,
    )

    summary = summarize_fuel(
        fuel_results
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"\nTotal flights: "
        f"{len(flights)}"
    )

    print("\nTotal estimated fuel:")

    for unit, total in sorted(
        summary["totals"].items()
    ):
        quantity_unit = display_fuel_unit(
            unit
        )

        print(
            f"  {total:,.1f} "
            f"{quantity_unit}"
        )

    print("\nBy aircraft:")
    print("-" * 70)

    for aircraft, data in sorted(
        summary["by_aircraft"].items()
    ):
        quantity_unit = display_fuel_unit(
            data["unit"]
        )

        print(
            f"{aircraft:<15} "
            f"{data['flights']:>5} flights  "
            f"{format_hours(data['flight_minutes']):>8}  "
            f"{data['fuel']:>12,.1f} "
            f"{quantity_unit}"
        )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()