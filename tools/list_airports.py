from parser.easa_pdf import parse_logbook


def main():
    flights = parse_logbook("logbook.pdf")

    airports = set()

    for flight in flights:
        airports.add(flight.departure)
        airports.add(flight.arrival)

    airports = sorted(airports)

    print("\n" + "=" * 60)
    print("FLIGHTSTATS AIRPORT ANALYSIS")
    print("=" * 60)

    print(f"\nFlights: {len(flights)}")
    print(f"Unique airports: {len(airports)}")

    print("\nICAO codes:")
    print("-" * 30)

    for airport in airports:
        print(airport)

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()