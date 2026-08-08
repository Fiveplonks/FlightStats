from parser.easa_pdf import parse_logbook
from parser.airports import AirportDatabase
from parser.flight_analysis import (
    calculate_all_distances,
    total_distance_km,
)
from parser.fuel import FuelDatabase
from parser.fuel_analysis import (
    calculate_all_fuel,
    summarize_fuel,
)
from parser.performance_analysis import (
    calculate_all_sector_speeds,
    summarize_sector_speed,
)


LOGBOOK = "logbook.pdf"


def format_hours(minutes):
    """Convert minutes into H:MM format."""

    hours = minutes // 60
    remaining_minutes = minutes % 60

    return f"{hours}:{remaining_minutes:02d}"


def display_fuel_unit(unit):
    """Convert kg/h or L/h into kg or L."""

    return unit.replace("/h", "")


def main():
    print("=" * 70)
    print("FLIGHTSTATS")
    print("=" * 70)

    # =====================================================
    # PARSE LOGBOOK
    # =====================================================

    print("\nLoading logbook...")

    flights = parse_logbook(
        LOGBOOK
    )

    total_flights = len(flights)

    total_flight_minutes = sum(
        flight.flight_minutes
        for flight in flights
    )

    print("\n" + "=" * 70)
    print("LOGBOOK SUMMARY")
    print("=" * 70)

    print(
        f"\nTotal flights: "
        f"{total_flights}"
    )

    print(
        f"Total flight time: "
        f"{format_hours(total_flight_minutes)}"
    )

    # =====================================================
    # AIRPORT DATABASE
    # =====================================================

    print("\n" + "=" * 70)
    print("AIRPORT DATABASE")
    print("=" * 70)

    airport_database = AirportDatabase()

    print(
        "\nAirport database loaded."
    )

    # =====================================================
    # DISTANCE CALCULATION
    # =====================================================

    print("\n" + "=" * 70)
    print("DISTANCE CALCULATION")
    print("=" * 70)

    flight_distances = calculate_all_distances(
        flights,
        airport_database,
    )

    total_distance = total_distance_km(
        flight_distances
    )

    calculated_distance_flights = sum(
        1
        for result in flight_distances
        if result["distance_km"] is not None
    )

    unresolved_distance_flights = (
        total_flights
        - calculated_distance_flights
    )

    print(
        "\nDistance calculation complete."
    )

    print(
        f"Flights with distance: "
        f"{calculated_distance_flights}"
    )

    print(
        f"Flights unresolved: "
        f"{unresolved_distance_flights}"
    )

    print(
        f"Total distance: "
        f"{total_distance:,.1f} km"
    )

    # =====================================================
    # SECTOR SPEED ANALYSIS
    # =====================================================

    print("\n" + "=" * 70)
    print("SECTOR SPEED ANALYSIS")
    print("=" * 70)

    speed_results = (
        calculate_all_sector_speeds(
            flights,
            flight_distances,
        )
    )

    speed_summary = (
        summarize_sector_speed(
            speed_results
        )
    )

    print(
        "\nAverage sector speed by aircraft:"
    )

    print("-" * 70)

    for (
        aircraft,
        data,
    ) in sorted(
        speed_summary.items()
    ):
        average_speed = data[
            "average_sector_speed_kmh"
        ]

        if average_speed is None:
            speed_text = "N/A"
        else:
            speed_text = (
                f"{average_speed:,.1f} km/h"
            )

        print(
            f"{aircraft:<15} "
            f"{data['flights']:>5} flights  "
            f"{format_hours(data['flight_minutes']):>8}  "
            f"{data['distance_km']:>12,.1f} km  "
            f"{speed_text:>12}"
        )

    # =====================================================
    # FUEL DATABASE
    # =====================================================

    print("\n" + "=" * 70)
    print("FUEL DATABASE")
    print("=" * 70)

    fuel_database = FuelDatabase()

    print(
        f"\nFuel profiles loaded: "
        f"{len(fuel_database.aircraft)}"
    )

    # =====================================================
    # FUEL CALCULATION
    # =====================================================

    print("\n" + "=" * 70)
    print("FUEL CALCULATION")
    print("=" * 70)

    fuel_results = calculate_all_fuel(
        flights,
        fuel_database,
    )

    fuel_summary = summarize_fuel(
        fuel_results
    )

    # =====================================================
    # FUEL SUMMARY
    # =====================================================

    print("\n" + "=" * 70)
    print("FUEL SUMMARY")
    print("=" * 70)

    print("\nTotal estimated fuel:")

    for unit, total in sorted(
        fuel_summary["totals"].items()
    ):
        quantity_unit = display_fuel_unit(
            unit
        )

        print(
            f"  {total:,.1f} "
            f"{quantity_unit}"
        )

    # =====================================================
    # AIRCRAFT FUEL BREAKDOWN
    # =====================================================

    print("\nBy aircraft:")
    print("-" * 70)

    for (
        aircraft,
        data,
    ) in sorted(
        fuel_summary[
            "by_aircraft"
        ].items()
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

    # =====================================================
    # FINAL SUMMARY
    # =====================================================

    print("\n" + "=" * 70)
    print("FLIGHTSTATS SUMMARY")
    print("=" * 70)

    print(
        f"\nFlights: "
        f"{total_flights}"
    )

    print(
        f"Flight time: "
        f"{format_hours(total_flight_minutes)}"
    )

    print(
        f"Distance: "
        f"{total_distance:,.1f} km"
    )

    print(
        f"Flights with distance: "
        f"{calculated_distance_flights}"
    )

    print(
        f"Flights unresolved: "
        f"{unresolved_distance_flights}"
    )

    print("\nAverage sector speed:")

    for (
        aircraft,
        data,
    ) in sorted(
        speed_summary.items()
    ):
        average_speed = data[
            "average_sector_speed_kmh"
        ]

        if average_speed is None:
            continue

        print(
            f"  {aircraft:<15} "
            f"{average_speed:,.1f} km/h"
        )

    for unit, total in sorted(
        fuel_summary["totals"].items()
    ):
        quantity_unit = display_fuel_unit(
            unit
        )

        print(
            f"Estimated fuel: "
            f"{total:,.1f} "
            f"{quantity_unit}"
        )

    print("\n" + "=" * 70)
    print("FLIGHTSTATS COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()