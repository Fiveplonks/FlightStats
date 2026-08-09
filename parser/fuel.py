import csv

from app_paths import (
    BUNDLED_FUEL_DATABASE,
    USER_FUEL_DATABASE,
    migrate_file_if_needed,
)


class FuelDatabase:
    """Aircraft fuel-burn database."""

    VALID_UNITS = {
        "kg/h",
        "L/h",
    }

    NORMALIZATION = {
        "737-700": "B737-700",
        "B737-700": "B737-700",
        "800": "B737-800",
        "737-800": "B737-800",
        "B737-800": "B737-800",
        "8200": "B737-8200",
        "737-8200": "B737-8200",
        "B737-8200": "B737-8200",
        "B38M": "B737-8200",
        "737 MAX 8": "B737-8200",
        "B737 MAX 8": "B737-8200",
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

    def __init__(self):
        self.aircraft = {}

        USER_FUEL_DATABASE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Preserve the current development fuel database on first run.
        migrate_file_if_needed(
            BUNDLED_FUEL_DATABASE,
            USER_FUEL_DATABASE,
        )

        self.load()

    @classmethod
    def normalize_type(cls, aircraft_type):
        if not aircraft_type:
            return None

        aircraft_type = aircraft_type.strip().upper()

        return cls.NORMALIZATION.get(
            aircraft_type,
            aircraft_type,
        )

    def _active_database(self):
        if USER_FUEL_DATABASE.exists():
            return USER_FUEL_DATABASE

        return BUNDLED_FUEL_DATABASE

    def load(self):
        """Load aircraft fuel-burn profiles."""

        database = self._active_database()

        if not database.exists():
            return

        with open(
            database,
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
                except (KeyError, ValueError):
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
                    "method": row.get("method", ""),
                    "source": row.get("source", ""),
                    "notes": row.get("notes", ""),
                }

                self.aircraft[
                    normalized_type.upper()
                ] = profile

    def find(self, aircraft_type):
        normalized = self.normalize_type(aircraft_type)

        if not normalized:
            return None

        return self.aircraft.get(
            normalized.upper()
        )

    def add(
        self,
        aircraft_type,
        average_burn,
        unit,
        method="User supplied",
        source="User",
        notes="",
    ):
        normalized_type = self.normalize_type(aircraft_type)

        if not normalized_type:
            raise ValueError(
                "Aircraft type is required."
            )

        if unit not in self.VALID_UNITS:
            raise ValueError(
                f"Invalid fuel unit: {unit}"
            )

        average_burn = float(average_burn)

        if average_burn <= 0:
            raise ValueError(
                "Average fuel burn must be greater than zero."
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

    def _rewrite_database(self):
        """Rewrite only the writable user fuel database."""

        USER_FUEL_DATABASE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

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
            USER_FUEL_DATABASE,
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
                key=lambda item: item["normalized_type"],
            ):
                writer.writerow(profile)

    def request_profile(self, aircraft_type):
        normalized_type = self.normalize_type(aircraft_type)

        print("\n" + "=" * 60)
        print("UNKNOWN AIRCRAFT FUEL PROFILE")
        print("=" * 60)
        print(f"\nAircraft type: {aircraft_type}")
        print(f"Normalized type: {normalized_type}")
        print("\nFlightStats does not have a fuel-burn profile for this aircraft.")

        while True:
            try:
                average_burn = float(input("\nAverage fuel burn: "))
                if average_burn <= 0:
                    raise ValueError
                break
            except ValueError:
                print("Enter a positive number.")

        while True:
            unit = input("Unit (kg/h or L/h): ").strip()
            if unit in self.VALID_UNITS:
                break
            print("Please enter kg/h or L/h.")

        notes = input("Notes (optional): ").strip()

        return self.add(
            aircraft_type=aircraft_type,
            average_burn=average_burn,
            unit=unit,
            method="User supplied",
            source="User",
            notes=notes,
        )

    def resolve(self, aircraft_type):
        profile = self.find(aircraft_type)

        if profile:
            return profile

        return self.request_profile(aircraft_type)
