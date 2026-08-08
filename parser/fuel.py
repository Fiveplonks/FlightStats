import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"

FUEL_DATABASE = DATA_DIR / "aircraft_fuel_burn.csv"


class FuelDatabase:
    """
    Aircraft fuel-burn database.

    Fuel consumption is an estimate based on an
    aircraft-specific representative fuel-burn rate.

    Supported units:
        kg/h
        L/h
    """

    VALID_UNITS = {
        "kg/h",
        "L/h",
    }

    def __init__(self):
        self.aircraft = {}

        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.load()

    # -----------------------------------------------------
    # Aircraft normalization
    # -----------------------------------------------------

    NORMALIZATION = {
        "737-700": "B737-700",
        "B737-700": "B737-700",
        "B737-800": "B737-800",
        "B737-900": "B737-900",
        "B737-COMBI": "B737-COMBI",
        "A319": "A319",
        "A320": "A320",
        "A330-200": "A330-200",
        "A330-200F": "A330-200F",
        "A330-900": "A330-900",
        "PA28": "PA28",
        "PA34": "PA34",
        "PA44": "PA44",
        "EA300L": "EA300L",
    }

    @classmethod
    def normalize_type(cls, aircraft_type):
        """
        Convert a logbook aircraft type into the
        normalized FlightStats aircraft type.
        """

        if not aircraft_type:
            return None

        aircraft_type = (
            aircraft_type.strip().upper()
        )

        return cls.NORMALIZATION.get(
            aircraft_type,
            aircraft_type,
        )

    # -----------------------------------------------------
    # Load database
    # -----------------------------------------------------

    def load(self):
        """Load aircraft fuel-burn profiles."""

        if not FUEL_DATABASE.exists():
            return

        with open(
            FUEL_DATABASE,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                aircraft_type = row.get(
                    "aircraft_type",
                    "",
                ).strip()

                if not aircraft_type:
                    continue

                try:
                    average_burn = float(
                        row["average_burn"]
                    )
                except (
                    KeyError,
                    ValueError,
                ):
                    continue

                unit = row.get(
                    "unit",
                    "",
                ).strip()

                if unit not in self.VALID_UNITS:
                    continue

                normalized_type = row.get(
                    "normalized_type",
                    aircraft_type,
                ).strip()

                profile = {
                    "aircraft_type": aircraft_type,
                    "normalized_type": normalized_type,
                    "average_burn": average_burn,
                    "unit": unit,
                    "method": row.get(
                        "method",
                        "",
                    ),
                    "source": row.get(
                        "source",
                        "",
                    ),
                    "notes": row.get(
                        "notes",
                        "",
                    ),
                }

                self.aircraft[
                    normalized_type.upper()
                ] = profile

    # -----------------------------------------------------
    # Lookup
    # -----------------------------------------------------

    def find(self, aircraft_type):
        """Find a normalized aircraft fuel profile."""

        normalized = self.normalize_type(
            aircraft_type
        )

        if not normalized:
            return None

        return self.aircraft.get(
            normalized.upper()
        )

    # -----------------------------------------------------
    # Add profile
    # -----------------------------------------------------

    def add(
        self,
        aircraft_type,
        average_burn,
        unit,
        method="User supplied",
        source="User",
        notes="",
    ):
        """Add or update a fuel-burn profile."""

        normalized_type = self.normalize_type(
            aircraft_type
        )

        if not normalized_type:
            raise ValueError(
                "Aircraft type is required."
            )

        if unit not in self.VALID_UNITS:
            raise ValueError(
                f"Invalid fuel unit: {unit}"
            )

        average_burn = float(
            average_burn
        )

        if average_burn <= 0:
            raise ValueError(
                "Average fuel burn must "
                "be greater than zero."
            )

        profile = {
            "aircraft_type": aircraft_type,
            "normalized_type": normalized_type,
            "average_burn": average_burn,
            "unit": unit,
            "method": method,
            "source": source,
            "notes": notes,
        }

        self.aircraft[
            normalized_type.upper()
        ] = profile

        self._rewrite_database()

        return profile

    # -----------------------------------------------------
    # Rewrite database
    # -----------------------------------------------------

    def _rewrite_database(self):
        """Rewrite the complete fuel database."""

        fieldnames = [
            "aircraft_type",
            "normalized_type",
            "average_burn",
            "unit",
            "method",
            "source",
            "notes",
        ]

        with open(
            FUEL_DATABASE,
            "w",
            encoding="utf-8",
            newline="",
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            for profile in sorted(
                self.aircraft.values(),
                key=lambda item: item[
                    "normalized_type"
                ],
            ):

                writer.writerow(
                    profile
                )

    # -----------------------------------------------------
    # Interactive fallback
    # -----------------------------------------------------

    def request_profile(
        self,
        aircraft_type,
    ):
        """Ask the user to provide a missing profile."""

        normalized_type = self.normalize_type(
            aircraft_type
        )

        print("\n" + "=" * 60)
        print("UNKNOWN AIRCRAFT FUEL PROFILE")
        print("=" * 60)

        print(
            f"\nAircraft type: "
            f"{aircraft_type}"
        )

        print(
            f"Normalized type: "
            f"{normalized_type}"
        )

        print(
            "\nFlightStats does not have a "
            "fuel-burn profile for this aircraft."
        )

        while True:

            try:
                average_burn = float(
                    input(
                        "\nAverage fuel burn: "
                    )
                )

                if average_burn <= 0:
                    raise ValueError

                break

            except ValueError:

                print(
                    "Enter a positive number."
                )

        while True:

            unit = input(
                "Unit (kg/h or L/h): "
            ).strip()

            if unit in self.VALID_UNITS:
                break

            print(
                "Please enter kg/h or L/h."
            )

        notes = input(
            "Notes (optional): "
        ).strip()

        return self.add(
            aircraft_type=aircraft_type,
            average_burn=average_burn,
            unit=unit,
            method="User supplied",
            source="User",
            notes=notes,
        )

    # -----------------------------------------------------
    # Resolve
    # -----------------------------------------------------

    def resolve(self, aircraft_type):
        """
        Find a fuel profile.

        If unavailable, ask the user to provide one.
        """

        profile = self.find(
            aircraft_type
        )

        if profile:
            return profile

        return self.request_profile(
            aircraft_type
        )


if __name__ == "__main__":

    database = FuelDatabase()

    print(
        f"Fuel profiles loaded: "
        f"{len(database.aircraft)}"
    )