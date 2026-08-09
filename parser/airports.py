import csv
import json
import urllib.request
from datetime import date
from pathlib import Path

from app_paths import (
    BUNDLED_AIRPORT_DATABASE,
    USER_AIRPORT_DATABASE,
    USER_AIRPORT_METADATA,
    USER_CUSTOM_AIRPORT_DATABASE,
    migrate_file_if_needed,
)

# ---------------------------------------------------------
# File locations
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Read-only reference database supplied with FlightStats.
BUNDLED_DATABASE = BUNDLED_AIRPORT_DATABASE

# Writable user copies.
AIRPORT_DATABASE = USER_AIRPORT_DATABASE
CUSTOM_AIRPORT_DATABASE = USER_CUSTOM_AIRPORT_DATABASE
DATABASE_METADATA = USER_AIRPORT_METADATA

# ---------------------------------------------------------
# OurAirports
# ---------------------------------------------------------

OURAIRPORTS_URL = (
    "https://ourairports.com/data/airports.csv"
)

class AirportDatabase:
    """
    Airport database for FlightStats.

    Airport lookup order:

        1. Worldwide OurAirports database
        2. User-created custom airport database
        3. Interactive user input
    """

    def __init__(self):
        self.airports = {}

        AIRPORT_DATABASE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Preserve existing development/user files on first run.
        migrate_file_if_needed(
            DATA_DIR / "airports.csv",
            AIRPORT_DATABASE,
        )

        migrate_file_if_needed(
            DATA_DIR / "custom_airports.csv",
            CUSTOM_AIRPORT_DATABASE,
        )

        migrate_file_if_needed(
            DATA_DIR / "airport_database.json",
            DATABASE_METADATA,
        )

        self.load_database()
        self.load_custom_airports()

    # -----------------------------------------------------
    # Loading the worldwide database
    # -----------------------------------------------------

    def load_database(self):
        """Load the worldwide airport database."""

        database_path = AIRPORT_DATABASE

        if not database_path.exists():
            database_path = BUNDLED_DATABASE

        if not database_path.exists():
            print(
                "\nWARNING: Airport database not found."
            )

            return

        print(
            "\nLoading worldwide airport database..."
        )

        count = 0

        with open(
            database_path,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                latitude = row.get(
                    "latitude_deg"
                )

                longitude = row.get(
                    "longitude_deg"
                )

                if not latitude or not longitude:
                    continue

                airport = {
                    "code": row.get(
                        "ident",
                        "",
                    ),
                    "icao": row.get(
                        "icao_code",
                        "",
                    ),
                    "iata": row.get(
                        "iata_code",
                        "",
                    ),
                    "gps": row.get(
                        "gps_code",
                        "",
                    ),
                    "local": row.get(
                        "local_code",
                        "",
                    ),
                    "name": row.get(
                        "name",
                        "",
                    ),
                    "country": row.get(
                        "iso_country",
                        "",
                    ),
                    "latitude": float(
                        latitude
                    ),
                    "longitude": float(
                        longitude
                    ),
                }

                identifiers = (
                    airport["code"],
                    airport["icao"],
                    airport["gps"],
                    airport["iata"],
                    airport["local"],
                )

                for identifier in identifiers:

                    if not identifier:
                        continue

                    identifier = (
                        identifier.upper()
                    )

                    # Keep the first match.
                    self.airports.setdefault(
                        identifier,
                        airport,
                    )

                count += 1

        print(
            f"Worldwide airports loaded: "
            f"{count}"
        )

    # -----------------------------------------------------
    # Loading custom airports
    # -----------------------------------------------------

    def load_custom_airports(self):
        """
        Load airports manually added by the user.
        """

        if not CUSTOM_AIRPORT_DATABASE.exists():
            return

        count = 0

        with open(
            CUSTOM_AIRPORT_DATABASE,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                code = row.get(
                    "code",
                    "",
                ).strip().upper()

                if not code:
                    continue

                try:
                    latitude = float(
                        row["latitude"]
                    )

                    longitude = float(
                        row["longitude"]
                    )

                except (
                    KeyError,
                    ValueError,
                ):
                    continue

                airport = {
                    "code": code,
                    "icao": code,
                    "iata": "",
                    "gps": code,
                    "local": code,
                    "name": row.get(
                        "name",
                        "",
                    ),
                    "country": row.get(
                        "country",
                        "",
                    ),
                    "latitude": latitude,
                    "longitude": longitude,
                    "custom": True,
                }

                self.airports[code] = airport

                count += 1

        if count:
            print(
                f"Custom airports loaded: "
                f"{count}"
            )

    # -----------------------------------------------------
    # Lookup
    # -----------------------------------------------------

    def find(self, code):
        """
        Find an airport by identifier.

        Returns airport information or None.
        """

        if not code:
            return None

        code = code.strip().upper()

        return self.airports.get(code)

    # -----------------------------------------------------
    # Add custom airport
    # -----------------------------------------------------

    def add_custom_airport(
        self,
        code,
        name,
        latitude,
        longitude,
        country="",
    ):
        """
        Add a manually entered airport.
        """

        code = code.strip().upper()

        airport = {
            "code": code,
            "icao": code,
            "iata": "",
            "gps": code,
            "local": code,
            "name": name,
            "country": country,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "custom": True,
        }

        self.airports[code] = airport

        file_exists = (
            CUSTOM_AIRPORT_DATABASE.exists()
        )

        with open(
            CUSTOM_AIRPORT_DATABASE,
            "a",
            encoding="utf-8",
            newline="",
        ) as file:

            fieldnames = [
                "code",
                "name",
                "country",
                "latitude",
                "longitude",
            ]

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )

            if not file_exists:
                writer.writeheader()

            writer.writerow(
                {
                    "code": code,
                    "name": name,
                    "country": country,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

        print(
            f"\n✓ {code} saved to "
            f"custom airport database."
        )

        return airport

    # -----------------------------------------------------
    # Interactive airport entry
    # -----------------------------------------------------

    def request_custom_airport(self, code):
        """
        Ask the user for coordinates when an
        airport cannot be found automatically.
        """

        code = code.strip().upper()

        print("\n" + "=" * 60)
        print("UNKNOWN AIRPORT")
        print("=" * 60)

        print(
            f"\nAirport code '{code}' was not found "
            f"in the worldwide airport database."
        )

        print(
            "\nThis may be a historical, military, "
            "private, or otherwise unlisted airport."
        )

        while True:
            name = input(
                "\nAirport name: "
            ).strip()

            if name:
                break

            print(
                "Please enter an airport name."
            )

        while True:
            try:
                latitude = float(
                    input(
                        "Latitude "
                        "(decimal degrees): "
                    )
                )

                if not -90 <= latitude <= 90:
                    raise ValueError

                break

            except ValueError:
                print(
                    "Invalid latitude. "
                    "Enter a value between "
                    "-90 and 90."
                )

        while True:
            try:
                longitude = float(
                    input(
                        "Longitude "
                        "(decimal degrees): "
                    )
                )

                if not -180 <= longitude <= 180:
                    raise ValueError

                break

            except ValueError:
                print(
                    "Invalid longitude. "
                    "Enter a value between "
                    "-180 and 180."
                )

        country = input(
            "Country code (optional): "
        ).strip().upper()

        return self.add_custom_airport(
            code=code,
            name=name,
            latitude=latitude,
            longitude=longitude,
            country=country,
        )

    # -----------------------------------------------------
    # Resolve airport
    # -----------------------------------------------------

    def resolve(self, code):
        """
        Resolve an airport.

        If it exists, return it.

        If it doesn't exist, ask the user to
        enter the coordinates.
        """

        airport = self.find(code)

        if airport:
            return airport

        return self.request_custom_airport(
            code
        )

    # -----------------------------------------------------
    # Database freshness
    # -----------------------------------------------------

    def database_age_days(self):
        """
        Return the age of the local database in days.

        Returns None if no metadata exists.
        """

        if not DATABASE_METADATA.exists():
            return None

        try:
            with open(
                DATABASE_METADATA,
                "r",
                encoding="utf-8",
            ) as file:

                metadata = json.load(file)

            updated = metadata.get(
                "downloaded"
            )

            if not updated:
                return None

            downloaded = date.fromisoformat(
                updated
            )

            return (
                date.today()
                - downloaded
            ).days

        except (
            OSError,
            ValueError,
            json.JSONDecodeError,
        ):
            return None

    def check_database_freshness(self):
        """
        Check how old the local airport database is.

        This currently checks the age of our local
        metadata rather than contacting the internet.
        """

        age = self.database_age_days()

        if age is None:
            print(
                "\nAirport database age: "
                "unknown"
            )

            return

        print(
            f"\nAirport database age: "
            f"{age} day(s)"
        )

        if age > 30:
            print(
                "⚠ Airport database is more "
                "than 30 days old."
            )
        else:
            print(
                "✓ Airport database is "
                "recent."
            )

    # -----------------------------------------------------
    # Update database
    # -----------------------------------------------------

    def update_database(self):
        """
        Download the latest worldwide airport
        database from OurAirports.
        """

        print(
            "\nDownloading latest airport "
            "database..."
        )

        temporary_file = (
            AIRPORT_DATABASE.parent / "airports.tmp.csv"
        )

        try:

            urllib.request.urlretrieve(
                OURAIRPORTS_URL,
                temporary_file,
            )

            temporary_file.replace(
                AIRPORT_DATABASE
            )

            metadata = {
                "source": "OurAirports",
                "url": OURAIRPORTS_URL,
                "downloaded": str(
                    date.today()
                ),
            }

            with open(
                DATABASE_METADATA,
                "w",
                encoding="utf-8",
            ) as file:

                json.dump(
                    metadata,
                    file,
                    indent=4,
                )

            print(
                "✓ Airport database updated."
            )

            # Reload worldwide database.
            self.airports = {}

            self.load_database()
            self.load_custom_airports()

            return True

        except Exception as error:

            print(
                "\n✗ Airport database update "
                "failed:"
            )

            print(error)

            if temporary_file.exists():
                temporary_file.unlink()

            return False

# ---------------------------------------------------------
# Test
# ---------------------------------------------------------
