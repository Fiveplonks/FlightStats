from parser.airports import AirportDatabase
from parser.easa_pdf import parse_logbook


def main():
    print("=" * 70)
    print("FLIGHTSTATS AIRPORT RESOLUTION TEST")
    print("=" * 70)

    database = AirportDatabase()

    print("\nParsing logbook...")

    flights = parse_logbook("logbook.pdf")

    codes = set()

    for flight in flights:
        codes.add(flight.departure.upper())
        codes.add(flight.arrival.upper())

    codes = sorted(codes)

    print(
        f"\nUnique airport codes in logbook: "
        f"{len(codes)}"
    )

    resolved = []
    newly_added = []

    print("\nResolving airports...")
    print("-" * 70)

    for code in codes:
        airport = database.find(code)

        if airport:
            resolved.append(code)

            print(
                f"✓ {code:<6} "
                f"{airport['name']} "
                f"({airport['latitude']:.4f}, "
                f"{airport['longitude']:.4f})"
            )

        else:
            print(
                f"\n✗ {code:<6} NOT FOUND"
            )

            airport = database.resolve(code)

            if airport:
                newly_added.append(code)

                print(
                    f"✓ {code:<6} "
                    f"{airport['name']} "
                    f"({airport['latitude']:.4f}, "
                    f"{airport['longitude']:.4f})"
                )

    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)

    print(
        f"\nAutomatically resolved: "
        f"{len(resolved)}"
    )

    print(
        f"Custom airports added: "
        f"{len(newly_added)}"
    )

    if newly_added:
        print("\nCustom airports:")

        for code in newly_added:
            print(f"  {code}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()