from parser.distance import calculate_distance_km


def calculate_flight_distance(
    flight,
    airport_database,
):
    """
    Calculate the great-circle distance for one flight.

    Returns the distance in kilometres.

    Raises ValueError if either airport cannot be resolved.
    """

    departure = airport_database.resolve(
        flight.departure
    )

    arrival = airport_database.resolve(
        flight.arrival
    )

    if departure is None:
        raise ValueError(
            f"Unable to resolve departure airport: "
            f"{flight.departure}"
        )

    if arrival is None:
        raise ValueError(
            f"Unable to resolve arrival airport: "
            f"{flight.arrival}"
        )

    return calculate_distance_km(
        departure["latitude"],
        departure["longitude"],
        arrival["latitude"],
        arrival["longitude"],
    )


def calculate_all_distances(
    flights,
    airport_database,
):
    """
    Calculate distances for all flights.

    Unresolved airports do not stop processing.

    Returns a list of dictionaries containing:

        flight
        distance_km

    Flights whose airports cannot be resolved have
    distance_km set to None.
    """

    results = []

    total_flights = len(flights)

    unresolved = []

    print(
        "\nCalculating flight distances..."
    )

    for number, flight in enumerate(
        flights,
        start=1,
    ):

        try:
            distance = calculate_flight_distance(
                flight,
                airport_database,
            )

            results.append(
                {
                    "flight": flight,
                    "distance_km": distance,
                }
            )

            print(
                f"Processing flight "
                f"{number}/{total_flights}... "
                f"{flight.departure} → "
                f"{flight.arrival} "
                f"{distance:.1f} km"
            )

        except ValueError as error:

            results.append(
                {
                    "flight": flight,
                    "distance_km": None,
                }
            )

            unresolved.append(
                {
                    "flight": flight,
                    "error": str(error),
                }
            )

            print(
                f"Processing flight "
                f"{number}/{total_flights}... "
                f"{flight.departure} → "
                f"{flight.arrival} "
                f"UNRESOLVED"
            )

    print(
        f"\nDistance processing complete."
    )

    print(
        f"Flights processed: "
        f"{total_flights}"
    )

    print(
        f"Flights with distance: "
        f"{total_flights - len(unresolved)}"
    )

    print(
        f"Flights unresolved: "
        f"{len(unresolved)}"
    )

    if unresolved:
        print(
            "\nUnresolved flights:"
        )

        for item in unresolved:
            flight = item["flight"]

            print(
                f"  {flight.date} "
                f"{flight.departure} → "
                f"{flight.arrival}"
            )

            print(
                f"    {item['error']}"
            )

    return results


def total_distance_km(
    flight_distances,
):
    """
    Calculate total distance from a list
    returned by calculate_all_distances().

    Flights with no calculated distance are
    ignored.
    """

    return sum(
        result["distance_km"]
        for result in flight_distances
        if result["distance_km"] is not None
    )