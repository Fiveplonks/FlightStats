from collections import defaultdict

from parser.fuel import FuelDatabase


def calculate_sector_speed(
    distance_km,
    flight_minutes,
):
    """
    Calculate average sector speed for one flight.

    This is based on great-circle airport-to-airport
    distance divided by recorded flight time.

    Returns speed in km/h.

    Returns None if distance or flight time is unavailable.
    """

    if (
        distance_km is None
        or flight_minutes is None
        or flight_minutes <= 0
    ):
        return None

    flight_hours = flight_minutes / 60

    return distance_km / flight_hours


def calculate_all_sector_speeds(
    flights,
    flight_distances,
):
    """
    Calculate average sector speed for every flight.

    flight_distances must be the list returned by
    calculate_all_distances().

    Returns a list of dictionaries containing:

        flight
        distance_km
        flight_minutes
        sector_speed_kmh
    """

    results = []

    distance_by_flight = {
        id(result["flight"]): result[
            "distance_km"
        ]
        for result in flight_distances
    }

    total_flights = len(flights)

    print(
        "\nCalculating average sector speeds..."
    )

    for number, flight in enumerate(
        flights,
        start=1,
    ):
        distance_km = distance_by_flight.get(
            id(flight)
        )

        sector_speed = calculate_sector_speed(
            distance_km,
            flight.flight_minutes,
        )

        results.append(
            {
                "flight": flight,
                "distance_km": distance_km,
                "flight_minutes": (
                    flight.flight_minutes
                ),
                "sector_speed_kmh": (
                    sector_speed
                ),
            }
        )

        if sector_speed is None:
            speed_text = "N/A"
        else:
            speed_text = (
                f"{sector_speed:.1f} km/h"
            )

        print(
            f"Processing speed "
            f"{number}/{total_flights}... "
            f"{flight.departure} → "
            f"{flight.arrival} "
            f"{speed_text}"
        )

    return results


def summarize_sector_speed(
    speed_results,
):
    """
    Calculate weighted average sector speed
    by normalized aircraft type.

    Aircraft types are normalized using the same
    FuelDatabase normalization used by the fuel system.

    The weighted average is:

        total distance / total flight time

    rather than the arithmetic mean of individual
    flight speeds.
    """

    aircraft_data = defaultdict(
        lambda: {
            "flights": 0,
            "distance_km": 0.0,
            "flight_minutes": 0,
        }
    )

    for result in speed_results:

        flight = result["flight"]
        distance_km = result[
            "distance_km"
        ]

        if (
            distance_km is None
            or flight.flight_minutes <= 0
        ):
            continue

        aircraft = FuelDatabase.normalize_type(
            flight.aircraft
        )

        data = aircraft_data[
            aircraft
        ]

        data["flights"] += 1

        data["distance_km"] += (
            distance_km
        )

        data["flight_minutes"] += (
            flight.flight_minutes
        )

    summaries = {}

    for aircraft, data in (
        aircraft_data.items()
    ):

        flight_hours = (
            data["flight_minutes"]
            / 60
        )

        if flight_hours <= 0:
            average_speed = None
        else:
            average_speed = (
                data["distance_km"]
                / flight_hours
            )

        summaries[aircraft] = {
            "flights": data["flights"],
            "distance_km": data[
                "distance_km"
            ],
            "flight_minutes": data[
                "flight_minutes"
            ],
            "average_sector_speed_kmh": (
                average_speed
            ),
        }

    return summaries


# ---------------------------------------------------------
# Backwards-compatible aliases
# ---------------------------------------------------------
#
# These allow existing code to continue working if it still
# calls the previous function names.
# ---------------------------------------------------------

calculate_ground_speed = calculate_sector_speed

calculate_all_ground_speeds = (
    calculate_all_sector_speeds
)

summarize_ground_speed = (
    summarize_sector_speed
)