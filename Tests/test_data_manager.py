from data_manager import FlightStatsData


def main():
    print("=" * 70)
    print("FLIGHTSTATS DATA MANAGER TEST")
    print("=" * 70)

    data = FlightStatsData(
        "logbook.pdf"
    )

    print("\nRESULT")
    print("-" * 70)

    print(
        f"Flights: "
        f"{data.total_flights}"
    )

    print(
        f"Flight time: "
        f"{data.total_flight_minutes // 60}:"
        f"{data.total_flight_minutes % 60:02d}"
    )

    print(
        f"Distance: "
        f"{data.total_distance_km:,.1f} km"
    )

    print(
        f"Airports: "
        f"{len(data.airports)}"
    )

    print(
        f"Distance calculated: "
        f"{data.calculated_distance_flights}"
    )

    print(
        f"Distance unresolved: "
        f"{data.unresolved_distance_flights}"
    )

    print(
        f"Fuel totals: "
        f"{data.fuel_totals}"
    )

    print(
        f"Aircraft types: "
        f"{len(data.aircraft_summary)}"
    )

    print(
        f"Sector-speed types: "
        f"{len(data.aircraft_speed_summary)}"
    )

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()