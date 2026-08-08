from collections import Counter

from parser.easa_pdf import parse_logbook


def format_minutes(total_minutes):
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours}:{minutes:02d}"


def main():
    flights = parse_logbook("logbook.pdf")

    print("\n" + "=" * 60)
    print("FLIGHTSTATS PARSER VALIDATION")
    print("=" * 60)

    # ---------------------------------------------------------
    # Basic flight count
    # ---------------------------------------------------------

    print(f"\nTotal flights: {len(flights)}")

    # ---------------------------------------------------------
    # Flights with / without calculated duration
    # ---------------------------------------------------------

    flights_with_duration = [
        flight
        for flight in flights
        if flight.flight_minutes is not None
    ]

    flights_without_duration = [
        flight
        for flight in flights
        if flight.flight_minutes is None
    ]

    print(
        f"Flights with calculated duration: "
        f"{len(flights_with_duration)}"
    )

    print(
        f"Flights missing departure/arrival time: "
        f"{len(flights_without_duration)}"
    )

    # ---------------------------------------------------------
    # Total calculated flight time
    # ---------------------------------------------------------

    total_minutes = sum(
        flight.flight_minutes
        for flight in flights_with_duration
    )

    print(
        f"Calculated flight time: "
        f"{format_minutes(total_minutes)}"
    )

    # ---------------------------------------------------------
    # Flights missing a time
    # ---------------------------------------------------------

    if flights_without_duration:
        print(
            "\nFlights missing departure or arrival time:"
        )
        print("-" * 60)

        for flight in flights_without_duration:
            print(
                f"{flight.date}  "
                f"{flight.departure} "
                f"{flight.departure_time} → "
                f"{flight.arrival} "
                f"{flight.arrival_time}  "
                f"{flight.aircraft} "
                f"{flight.registration}"
            )

    # ---------------------------------------------------------
    # First and last flight
    # ---------------------------------------------------------

    if flights:
        print("\nFirst flight:")
        print(flights[0])

        print("\nLast flight:")
        print(flights[-1])

    # ---------------------------------------------------------
    # Flights by year
    # ---------------------------------------------------------

    yearly_counts = Counter(
        flight.date.year
        for flight in flights
    )

    print("\nFlights by year:")
    print("-" * 30)

    for year in sorted(yearly_counts):
        print(
            f"{year}: "
            f"{yearly_counts[year]}"
        )

    # ---------------------------------------------------------
    # Flight-time distribution
    # ---------------------------------------------------------

    print("\nFlight-time distribution:")
    print("-" * 30)

    under_30 = sum(
        flight.flight_minutes is not None
        and flight.flight_minutes < 30
        for flight in flights
    )

    between_30_60 = sum(
        flight.flight_minutes is not None
        and 30 <= flight.flight_minutes < 60
        for flight in flights
    )

    between_60_120 = sum(
        flight.flight_minutes is not None
        and 60 <= flight.flight_minutes < 120
        for flight in flights
    )

    between_120_300 = sum(
        flight.flight_minutes is not None
        and 120 <= flight.flight_minutes < 300
        for flight in flights
    )

    over_300 = sum(
        flight.flight_minutes is not None
        and flight.flight_minutes >= 300
        for flight in flights
    )

    print(f"< 30 min:       {under_30}")
    print(f"30–59 min:      {between_30_60}")
    print(f"60–119 min:     {between_60_120}")
    print(f"120–299 min:    {between_120_300}")
    print(f"300+ min:       {over_300}")

    # ---------------------------------------------------------
    # Longest flights
    # ---------------------------------------------------------

    print("\n10 longest calculated flights:")
    print("-" * 60)

    longest_flights = sorted(
        flights_with_duration,
        key=lambda flight: flight.flight_minutes,
        reverse=True,
    )

    for flight in longest_flights[:10]:
        print(
            f"{format_minutes(flight.flight_minutes):>6}  "
            f"{flight.date}  "
            f"{flight.departure} → {flight.arrival}  "
            f"{flight.aircraft}  "
            f"{flight.registration}"
        )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()