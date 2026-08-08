from parser.easa_pdf import parse_logbook


def main():
    flights = parse_logbook("logbook.pdf")

    print(f"Flights found: {len(flights)}")

    print("\nFirst 10 flights:")
    print("-" * 60)

    for flight in flights[:10]:
        print(
            flight.date,
            flight.departure,
            flight.departure_time,
            "→",
            flight.arrival,
            flight.arrival_time,
            flight.aircraft,
            flight.registration,
            f"{flight.flight_minutes} min",
        )


if __name__ == "__main__":
    main()