from parser.fuel import FuelDatabase


def main():
    print("=" * 60)
    print("FLIGHTSTATS FUEL DATABASE TEST")
    print("=" * 60)

    database = FuelDatabase()

    print(
        f"\nFuel profiles loaded: "
        f"{len(database.aircraft)}"
    )

    # Test a known profile.
    profile = database.find(
        "B737-800"
    )

    if profile:
        print(
            "\nB737-800 profile:"
        )
        print(
            f"  Average burn: "
            f"{profile['average_burn']}"
        )
        print(
            f"  Unit: "
            f"{profile['unit']}"
        )
    else:
        print(
            "\nB737-800 has no profile yet."
        )

    print(
        "\n" + "=" * 60
    )


if __name__ == "__main__":
    main()