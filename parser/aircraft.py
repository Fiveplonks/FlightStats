"""
Aircraft type resolution for FlightStats.

Converts aircraft names/codes found in logbooks into canonical
aircraft identities and, where possible, OpenAP aircraft models.
"""

from dataclasses import dataclass
from typing import Optional

try:
    from openap import prop
except ImportError:
    prop = None


@dataclass(frozen=True)
class AircraftResolution:
    """Result of resolving one aircraft value."""

    raw: str
    canonical: Optional[str]
    icao: Optional[str]
    openap: Optional[str]
    openap_available: bool
    status: str


class AircraftResolver:
    """
    Resolve logbook aircraft representations.

    Resolution flow:

        logbook value
            -> canonical aircraft
            -> ICAO/OpenAP code
            -> installed OpenAP model
    """

    LOGBOOK_ALIASES = {
        # Boeing 737 Classic
        "733": ("Boeing 737-300", "B733"),
        "737-300": ("Boeing 737-300", "B733"),
        "B737-300": ("Boeing 737-300", "B733"),

        "734": ("Boeing 737-400", "B734"),
        "737-400": ("Boeing 737-400", "B734"),
        "B737-400": ("Boeing 737-400", "B734"),

        "735": ("Boeing 737-500", "B735"),
        "737-500": ("Boeing 737-500", "B735"),
        "B737-500": ("Boeing 737-500", "B735"),

        # Boeing 737 NG
        "737": ("Boeing 737-700", "B737"),
        "B737": ("Boeing 737-700", "B737"),
        "737-700": ("Boeing 737-700", "B737"),
        "B737-700": ("Boeing 737-700", "B737"),

        # KLM / logbook-specific representations
        "73H": ("Boeing 737-800", "B738"),


        "738": ("Boeing 737-800", "B738"),
        "800": ("Boeing 737-800", "B738"),
        "737-800": ("Boeing 737-800", "B738"),
        "B737-800": ("Boeing 737-800", "B738"),

        "739": ("Boeing 737-900", "B739"),
        "737-900": ("Boeing 737-900", "B739"),
        "B737-900": ("Boeing 737-900", "B739"),

        # Boeing 737 MAX
        "7M7": ("Boeing 737 MAX 7", "B37M"),
        "B37M": ("Boeing 737 MAX 7", "B37M"),
        "737 MAX 7": ("Boeing 737 MAX 7", "B37M"),
        "737-7 MAX": ("Boeing 737 MAX 7", "B37M"),

        "7M8": ("Boeing 737 MAX 8", "B38M"),
        "B38M": ("Boeing 737 MAX 8", "B38M"),
        "737 MAX 8": ("Boeing 737 MAX 8", "B38M"),
        "737-8 MAX": ("Boeing 737 MAX 8", "B38M"),
        "8200": ("Boeing 737 MAX 8", "B38M"),
        "737-8200": ("Boeing 737 MAX 8", "B38M"),
        "B737-8200": ("Boeing 737 MAX 8", "B38M"),

        "7M9": ("Boeing 737 MAX 9", "B39M"),
        "B39M": ("Boeing 737 MAX 9", "B39M"),
        "737 MAX 9": ("Boeing 737 MAX 9", "B39M"),
        "737-9 MAX": ("Boeing 737 MAX 9", "B39M"),

        "7MJ": ("Boeing 737 MAX 10", "B3XM"),
        "B3XM": ("Boeing 737 MAX 10", "B3XM"),
        "737 MAX 10": ("Boeing 737 MAX 10", "B3XM"),
        "737-10 MAX": ("Boeing 737 MAX 10", "B3XM"),

        # Boeing 747
        "744": ("Boeing 747-400", "B744"),
        "747-400": ("Boeing 747-400", "B744"),
        "B747-400": ("Boeing 747-400", "B744"),

        "748": ("Boeing 747-8", "B748"),
        "747-8": ("Boeing 747-8", "B748"),
        "B747-8": ("Boeing 747-8", "B748"),

        # Boeing 757
        "752": ("Boeing 757-200", "B752"),
        "757-200": ("Boeing 757-200", "B752"),
        "B757-200": ("Boeing 757-200", "B752"),

        # Boeing 767
        "762": ("Boeing 767-200", "B762"),
        "767-200": ("Boeing 767-200", "B762"),
        "B767-200": ("Boeing 767-200", "B762"),

        "763": ("Boeing 767-300", "B763"),
        "767-300": ("Boeing 767-300", "B763"),
        "B767-300": ("Boeing 767-300", "B763"),

        # Boeing 777
        "772": ("Boeing 777-200", "B772"),
        "777-200": ("Boeing 777-200", "B772"),
        "700-200": ("Boeing 777-200", "B772"),

        "B777-200": ("Boeing 777-200", "B772"),
        "777-200ER": ("Boeing 777-200", "B772"),
        "B777-200ER": ("Boeing 777-200", "B772"),

        "773": ("Boeing 777-300", "B773"),
        "777-300": ("Boeing 777-300", "B773"),
        "B777-300": ("Boeing 777-300", "B773"),

        "77W": ("Boeing 777-300ER", "B77W"),
        "777-300ER": ("Boeing 777-300ER", "B77W"),
        "B777-300ER": ("Boeing 777-300ER", "B77W"),

        # Boeing 787
        "788": ("Boeing 787-8", "B788"),
        "787-8": ("Boeing 787-8", "B788"),
        "B787-8": ("Boeing 787-8", "B788"),

        "789": ("Boeing 787-9", "B789"),
        "787-9": ("Boeing 787-9", "B789"),
        "B787-9": ("Boeing 787-9", "B789"),
        "787-900": ("Boeing 787-9", "B789"),
        "B787-900": ("Boeing 787-9", "B789"),


        # Recognized, but not available in this OpenAP installation.
        "78X": ("Boeing 787-10", "B78X"),
        "787-10": ("Boeing 787-10", "B78X"),
        "B787-10": ("Boeing 787-10", "B78X"),

        # Airbus
        "A318": ("Airbus A318", "A318"),
        "A319": ("Airbus A319", "A319"),
        "A320": ("Airbus A320", "A320"),
        "A321": ("Airbus A321", "A321"),

        "A332": ("Airbus A330-200", "A332"),
        "A330-200": ("Airbus A330-200", "A332"),

        "A333": ("Airbus A330-300", "A333"),
        "A330-300": ("Airbus A330-300", "A333"),

        "A343": ("Airbus A340-300", "A343"),
        "A350-900": ("Airbus A350-900", "A359"),
        "A359": ("Airbus A350-900", "A359"),

        "A388": ("Airbus A380-800", "A388"),
        "A380": ("Airbus A380-800", "A388"),

        # Regional
        "CRJ9": ("Bombardier CRJ-900", "CRJ9"),
        "CRJ900": ("Bombardier CRJ-900", "CRJ9"),

        "E145": ("Embraer ERJ-145", "E145"),
        "E170": ("Embraer E170", "E170"),
        "E190": ("Embraer E190", "E190"),
        "E195": ("Embraer E195", "E195"),
        "E75L": ("Embraer E175", "E75L"),

        # Business
        "GLF6": ("Gulfstream G650", "GLF6"),
    }

    def __init__(self):
        self._available_openap = set()
        self._available_openap_with_synonyms = set()

        if prop is None:
            return

        try:
            self._available_openap = {
                value.upper()
                for value in prop.available_aircraft()
            }
        except Exception:
            pass

        try:
            self._available_openap_with_synonyms = {
                value.upper()
                for value in prop.available_aircraft(
                    use_synonym=True
                )
            }
        except Exception:
            pass

    DISPLAY_NAMES = {
        # Boeing 737 Classic / NG
        "B733": "B737-300",
        "B734": "B737-400",
        "B735": "B737-500",
        "B737": "B737-700",
        "B738": "B737-800",
        "B739": "B737-900",

        # Boeing 737 MAX
        "B37M": "B737-7 MAX",
        "B38M": "B737-8 MAX",
        "B39M": "B737-9 MAX",
        "B3XM": "B737-10 MAX",

        # Boeing 747
        "B744": "B747-400",
        "B748": "B747-8",

        # Boeing 757
        "B752": "B757-200",

        # Boeing 767
        "B762": "B767-200",
        "B763": "B767-300",

        # Boeing 777
        "B772": "B777-200",
        "B773": "B777-300",
        "B77W": "B777-300ER",

        # Boeing 787
        "B788": "B787-8",
        "B789": "B787-9",
        "B78X": "B787-10",

        # Airbus
        "A318": "A318",
        "A319": "A319",
        "A320": "A320",
        "A321": "A321",
        "A332": "A330-200",
        "A333": "A330-300",
        "A343": "A340-300",
        "A359": "A350-900",
        "A388": "A380-800",

        # Regional
        "CRJ9": "CRJ900",
        "E145": "E145",
        "E170": "E170",
        "E190": "E190",
        "E195": "E195",
    }

    def display_code(self, aircraft_type):
        """
        Return the stable FlightStats display/grouping identifier.

        This is deliberately separate from:
            canonical = human-readable aircraft identity
            icao      = ICAO/OpenAP lookup identifier
        """

        raw = (
            ""
            if aircraft_type is None
            else str(aircraft_type).strip()
        )

        if not raw:
            return ""

        resolution = self.resolve(raw)

        if resolution is None:
            return raw

        if resolution.icao:
            return self.DISPLAY_NAMES.get(
                resolution.icao.upper(),
                resolution.icao,
            )

        return raw

    @staticmethod
    def normalize(value):
        """Normalize whitespace and case for aircraft lookup."""

        if value is None:
            return ""

        return " ".join(
            str(value)
            .strip()
            .upper()
            .split()
        )

    def resolve(self, aircraft_type):
        """
        Resolve an aircraft type.

        status is:

            resolved
                A usable OpenAP model exists.

            known_unsupported
                We know what the aircraft is, but this OpenAP
                installation has no corresponding model.

            unknown
                The aircraft representation is not recognized.
        """

        raw = (
            ""
            if aircraft_type is None
            else str(aircraft_type).strip()
        )


        normalized = self.normalize(raw)

        if not normalized:
            return AircraftResolution(
                raw=raw,
                canonical=None,
                icao=None,
                openap=None,
                openap_available=False,
                status="unknown",
            )

        alias = self.LOGBOOK_ALIASES.get(
            normalized
        )

        # ---------------------------------------------------------
        # Already an OpenAP identifier / synonym
        # ---------------------------------------------------------

        if alias is None:
            if normalized in self._available_openap_with_synonyms:
                openap = (
                    normalized
                    if normalized in self._available_openap
                    else None
                )

                canonical = normalized

                if prop is not None:
                    try:
                        info = prop.aircraft(
                            normalized,
                            use_synonym=True,
                        )

                        canonical = info.get(
                            "aircraft",
                            normalized,
                        )
                    except Exception:
                        pass

                return AircraftResolution(
                    raw=raw,
                    canonical=canonical,
                    icao=normalized,
                    openap=openap,
                    openap_available=openap is not None,
                    status=(
                        "resolved"
                        if openap is not None
                        else "known_unsupported"
                    ),
                )

            # Completely unknown aircraft.
            return AircraftResolution(
                raw=raw,
                canonical=None,
                icao=None,
                openap=None,
                openap_available=False,
                status="unknown",
            )

        canonical, icao = alias

        openap = None

        # ---------------------------------------------------------
        # Direct OpenAP model
        # ---------------------------------------------------------

        if icao in self._available_openap:
            openap = icao

        # ---------------------------------------------------------
        # OpenAP synonym
        # ---------------------------------------------------------

        elif icao in self._available_openap_with_synonyms:
            if prop is not None:
                try:
                    info = prop.aircraft(
                        icao,
                        use_synonym=True,
                    )

                    resolved_code = info.get(
                        "aircraft_type"
                    )

                    if resolved_code:
                        resolved_code = (
                            resolved_code.upper()
                        )

                    if (
                        resolved_code
                        in self._available_openap
                    ):
                        openap = resolved_code

                except Exception:
                    pass

        return AircraftResolution(
            raw=raw,
            canonical=canonical,
            icao=icao,
            openap=openap,
            openap_available=openap is not None,
            status=(
                "resolved"
                if openap is not None
                else "known_unsupported"
            ),
        )

    def is_resolved(self, aircraft_type):
        """Return True when an OpenAP model is available."""

        return self.resolve(
            aircraft_type
        ).openap_available
