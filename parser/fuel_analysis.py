def calculate_fuel_for_flight(
    flight,
    fuel_database,
):
    """
    Calculate estimated fuel for one flight.

    Returns a dictionary containing:
        flight
        fuel
        unit
        fuel_rate
        normalized_aircraft
    """

    profile = fuel_database.resolve(
        flight.aircraft
    )

    if profile is None:
        return {
            "flight": flight,
            "fuel": None,
            "unit": None,
            "fuel_rate": None,
            "normalized_aircraft": None,
            "source": None,
            "method": None,
        }

    fuel_rate = profile["average_burn"]
    unit = profile["unit"]

    fuel = (
        flight.flight_minutes
        / 60
        * fuel_rate
    )

    return {
        "flight": flight,
        "fuel": fuel,
        "unit": unit,
        "fuel_rate": fuel_rate,
        "normalized_aircraft": profile.get(
            "normalized_type"
        ),
        "source": profile.get("source"),
        "method": profile.get("method"),
    }


def calculate_all_fuel(
    flights,
    fuel_database,
    progress_callback=None,
):
    """
    Calculate estimated fuel for all flights.

    progress_callback is optional.

    When supplied, it is called as:

        progress_callback(
            percent,
            message,
        )
    """

    results = []

    total_flights = len(
        flights
    )

    if total_flights == 0:
        return results

    for number, flight in enumerate(
        flights,
        start=1,
    ):

        result = calculate_fuel_for_flight(
            flight,
            fuel_database,
        )

        results.append(
            result
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
                    "Calculating estimated fuel "
                    f"({number:,}/{total_flights:,})..."
                ),
            )

    return results


def summarize_fuel(
    fuel_results,
):
    """
    Summarize estimated fuel.

    Aircraft are grouped by the canonical normalized
    aircraft type returned by FuelDatabase.
    """

    totals = {}

    by_aircraft = {}

    for result in fuel_results:

        fuel = result["fuel"]
        unit = result["unit"]
        flight = result["flight"]

        if fuel is None:
            continue

        if unit not in totals:
            totals[unit] = 0.0

        totals[unit] += fuel

        # Group equivalent aircraft representations together.
        aircraft = (
            result.get("normalized_aircraft")
            or flight.aircraft
        )

        if aircraft not in by_aircraft:

            by_aircraft[aircraft] = {
                "flights": 0,
                "flight_minutes": 0,
                "fuel": 0.0,
                "unit": unit,
            }

        by_aircraft[
            aircraft
        ]["flights"] += 1

        by_aircraft[
            aircraft
        ]["flight_minutes"] += (
            flight.flight_minutes
        )

        by_aircraft[
            aircraft
        ]["fuel"] += fuel

    return {
        "totals": totals,
        "by_aircraft": by_aircraft,
    }
