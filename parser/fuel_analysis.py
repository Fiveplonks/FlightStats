from collections import defaultdict


def calculate_fuel_for_flight(
    flight,
    fuel_database,
):
    """
    Calculate estimated fuel consumption for one flight.

    Returns a dictionary containing:
        - flight
        - aircraft type
        - duration
        - fuel burn rate
        - fuel unit
        - estimated fuel
        - source
        - method
    """

    profile = fuel_database.resolve(
        flight.aircraft
    )

    duration_hours = (
        flight.flight_minutes / 60
    )

    estimated_fuel = (
        duration_hours
        * profile["average_burn"]
    )

    return {
        "flight": flight,
        "aircraft_type": profile[
            "normalized_type"
        ],
        "duration_hours": duration_hours,
        "average_burn": profile[
            "average_burn"
        ],
        "unit": profile["unit"],
        "estimated_fuel": estimated_fuel,
        "method": profile["method"],
        "source": profile["source"],
    }


def calculate_all_fuel(
    flights,
    fuel_database,
):
    """
    Calculate estimated fuel consumption
    for every flight.
    """

    results = []

    total_flights = len(flights)

    for number, flight in enumerate(
        flights,
        start=1,
    ):

        result = calculate_fuel_for_flight(
            flight,
            fuel_database,
        )

        results.append(result)

        print(
            f"Processing flight "
            f"{number}/{total_flights}... "
            f"{flight.date} "
            f"{flight.departure} → "
            f"{flight.arrival} "
            f"{flight.aircraft} "
            f"{result['estimated_fuel']:.1f} "
            f"{result['unit']}"
        )

    return results


def summarize_fuel(
    fuel_results,
):
    """
    Summarize estimated fuel consumption.

    Fuel is kept separated by unit because
    litres of avgas and kilograms of jet fuel
    cannot simply be added together.
    """

    totals = defaultdict(float)

    by_aircraft = defaultdict(
        lambda: {
            "flights": 0,
            "flight_minutes": 0,
            "fuel": 0.0,
            "unit": None,
        }
    )

    for result in fuel_results:

        unit = result["unit"]
        aircraft = result["aircraft_type"]

        totals[unit] += result[
            "estimated_fuel"
        ]

        aircraft_data = by_aircraft[
            aircraft
        ]

        aircraft_data["flights"] += 1

        aircraft_data[
            "flight_minutes"
        ] += result[
            "flight"
        ].flight_minutes

        aircraft_data["fuel"] += (
            result["estimated_fuel"]
        )

        aircraft_data["unit"] = unit

    return {
        "totals": dict(totals),
        "by_aircraft": dict(by_aircraft),
    }