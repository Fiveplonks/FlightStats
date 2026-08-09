import csv
import math

try:
    from openap import FuelFlow, prop
except ImportError:
    FuelFlow = None
    prop = None

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
        "CRJ900": "CRJ900",
        "DH8D": "DH8D",
        "ATR72": "ATR72",
        "PA44": "PA44",
        "PA28": "PA28",
        "PA34": "PA34",
        "PA44": "PA44",
        "EA300L": "EA300L",
    }

    OPENAP_TYPES = {
        "B737-700": "B737",
        "B737-800": "B738",
        "B737-8200": "B38M",
        "B737-900": "B739",
        "B737-COMBI": "B737",
        "A319": "A319",
        "A320": "A320",
        "A330-200": "A332",
        "A330-200F": "A332",
        "CRJ900": "CRJ9",
    }

    # Supplementary profiles are used only when OpenAP cannot resolve
    # the aircraft. Values are deliberately kept separate from OpenAP
    # and include provenance/methodology in the profile notes.
    SUPPLEMENTARY_PROFILES = {
        "ATR72": {
            "aircraft_type": "ATR72",
            "average_burn": 650.0,
            "unit": "kg/h",
            "method": "Manufacturer cruise estimate",
            "source": "ATR 72-600 manufacturer data",
            "notes": (
                "ATR 72-600 fuel consumption in cruise at 95% MTOW, "
                "ISA, FL240. Generic ATR72 mapping; actual variant, "
                "weight, power setting and conditions may differ."
            ),
        },
        "DH8D": {
            "aircraft_type": "DH8D",
            "average_burn": 812.5,
            "unit": "kg/h",
            "method": "Manufacturer trip-fuel-derived estimate",
            "source": "De Havilland Dash 8-400 manufacturer data",
            "notes": (
                "Derived as the mean of manufacturer trip-fuel rates "
                "for 200 NM (696 kg / 51 min) and 500 NM "
                "(1478 kg / 110 min). This is a representative "
                "trip-average estimate, not pure cruise fuel flow."
            ),
        },
        "PA44": {
            "aircraft_type": "PA44",
            "average_burn": 88.2,
            "unit": "L/h",
            "method": "Manufacturer 75% power estimate",
            "source": "Piper Seminole manufacturer data",
            "notes": (
                "Current Piper Seminole fuel burn at 75% power and "
                "6,000 ft: 23.3 US gal/h, converted to 88.2 L/h. "
                "Actual burn varies with engine variant, power, "
                "altitude and operating conditions."
            ),
        },
    }


    def __init__(self):
        self.aircraft = {}
        # Aircraft types that could not be resolved during this run.
        # Prevents repeated OpenAP lookups and repeated terminal output.
        self._unresolved_types = set()

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

    @staticmethod
    def _speed_of_sound_knots(altitude_m):
        """ISA speed of sound at altitude, returned in knots."""
        temperature = 288.15 - 0.0065 * altitude_m
        temperature = max(temperature, 216.65)

        speed_of_sound_ms = math.sqrt(
            1.4 * 287.05 * temperature
        )

        return speed_of_sound_ms * 1.94384449

    def lookup_openap(self, aircraft_type):
        """
        Derive an indicative average cruise fuel burn from OpenAP.

        OpenAP is an open aircraft-performance model. We evaluate its
        fuel-flow model at the aircraft's representative cruise altitude
        and Mach number using 75% MTOW. The result is intentionally marked
        as an estimate; it is not an airline-specific fuel-flow figure.
        """
        if FuelFlow is None or prop is None:
            return None

        normalized = self.normalize_type(aircraft_type)

        if not normalized:
            return None

        openap_type = self.OPENAP_TYPES.get(
            normalized,
            normalized,
        )

        try:
            aircraft = prop.aircraft(
                openap_type,
                use_synonym=True,
            )

            limits = aircraft.get("limits", {})
            mtow = limits.get("MTOW")

            cruise = aircraft.get("cruise", {})
            cruise_height_m = cruise.get(
                "height",
                11000,
            )
            cruise_mach = cruise.get(
                "mach",
                0.78,
            )

            if not mtow or not cruise_height_m:
                return None

            mass = float(mtow) * 0.75
            altitude_ft = float(cruise_height_m) * 3.280839895
            tas_knots = (
                float(cruise_mach)
                * self._speed_of_sound_knots(
                    float(cruise_height_m)
                )
            )

            flow_kg_s = FuelFlow(
                openap_type,
                use_synonym=True,
            ).enroute(
                mass=mass,
                tas=tas_knots,
                alt=altitude_ft,
                vs=0,
            )

            average_burn = float(flow_kg_s) * 3600

            if not math.isfinite(average_burn):
                return None

            if average_burn <= 0:
                return None

            return {
                "aircraft_type": aircraft_type,
                "normalized_type": normalized,
                "average_burn": round(
                    average_burn,
                    1,
                ),
                "unit": "kg/h",
                "method": "OpenAP cruise estimate",
                "source": "OpenAP",
                "notes": (
                    "Indicative cruise fuel-flow estimate "
                    "at 75% MTOW and representative cruise "
                    "conditions. Not an airline-specific "
                    "operational fuel-flow value."
                ),
            }

        except (
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            IndexError,
            RuntimeError,
        ) as error:
            print(
                f"OpenAP fuel lookup failed for "
                f"{aircraft_type}: {error}"
            )
            return None

    def lookup_supplementary(self, aircraft_type):
        """Return a provenance-aware supplementary profile if available."""
        normalized = self.normalize_type(aircraft_type)

        if not normalized:
            return None

        profile = self.SUPPLEMENTARY_PROFILES.get(
            normalized.upper()
        )

        if not profile:
            return None

        return {
            "aircraft_type": profile["aircraft_type"],
            "normalized_type": normalized,
            "average_burn": profile["average_burn"],
            "unit": profile["unit"],
            "method": profile["method"],
            "source": profile["source"],
            "notes": profile["notes"],
        }

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

    def resolve(
        self,
        aircraft_type,
        interactive=False,
    ):
        """
        Resolve a fuel profile.

        Resolution order:
            1. Local FlightStats database
            2. OpenAP automatic estimate
            3. Supplementary sourced profile
            4. Optional interactive manual entry

        Successful OpenAP-derived profiles are persisted in the writable
        user database. Failed automatic resolutions are cached only for
        the current run, preventing repeated lookups for every flight
        using the same unsupported aircraft type.
        """
        normalized = self.normalize_type(
            aircraft_type
        )

        if not normalized:
            return None

        profile = self.find(
            normalized
        )

        if profile:
            return profile

        cache_key = normalized.upper()

        if cache_key in self._unresolved_types:
            if interactive:
                return self.request_profile(
                    aircraft_type
                )
            return None

        profile = self.lookup_openap(
            aircraft_type
        )

        if profile:
            return self.add(
                aircraft_type=profile[
                    "aircraft_type"
                ],
                average_burn=profile[
                    "average_burn"
                ],
                unit=profile["unit"],
                method=profile["method"],
                source=profile["source"],
                notes=profile["notes"],
            )

        profile = self.lookup_supplementary(
            aircraft_type
        )

        if profile:
            return self.add(
                aircraft_type=profile[
                    "aircraft_type"
                ],
                average_burn=profile[
                    "average_burn"
                ],
                unit=profile["unit"],
                method=profile["method"],
                source=profile["source"],
                notes=profile["notes"],
            )

        self._unresolved_types.add(
            cache_key
        )

        print(
            "No automatic fuel profile available "
            f"for {aircraft_type}."
        )

        if interactive:
            return self.request_profile(
                aircraft_type
            )

        return None

