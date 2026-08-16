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
    progress_callback=None,
):
    """
    Calculate distances for all flights.

    progress_callback, when supplied, is called as:

        progress_callback(percent, message)
    """

    results = []

    total_flights = len(flights)

    if total_flights == 0:
        return results

    for number, flight in enumerate(
        flights,
        start=1,
    ):

        try:
            distance = calculate_flight_distance(
                flight,
                airport_database,
            )
        except ValueError:
            # An unresolved airport must not abort the entire
            # logbook distance calculation. Preserve the flight
            # with an unresolved distance so callers can count
            # and report it.
            distance = None

        results.append(
            {
                "flight": flight,
                "distance_km": distance,
            }
        )

        if progress_callback is not None:

            percent = int(
                number
                / total_flights
                * 100
            )

            progress_callback(
                percent,
                (
                    "Calculating flight distances "
                    f"({number:,}/{total_flights:,})..."
                ),
            )

    return results


def total_distance_km(
    flight_distances,
):
    """
    Calculate total distance from a list
    returned by calculate_all_distances().
    """

    return sum(
        result["distance_km"]
        for result in flight_distances
        if result["distance_km"] is not None
    )