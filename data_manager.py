import hashlib
import sys
import json
from datetime import date, time
from pathlib import Path

from app_paths import CACHE_DIR
from parser.loader import parse_flight_file
from parser.airports import AirportDatabase
from parser.flight_analysis import (
    calculate_all_distances,
    total_distance_km,
)
from parser.fuel import FuelDatabase
from parser.fuel_analysis import (
    calculate_all_fuel,
    summarize_fuel,
)
from parser.performance_analysis import (
    calculate_all_sector_speeds,
    summarize_sector_speed,
)


CACHE_VERSION = 3


def _file_sha256(path):
    """Return the SHA-256 digest of a file."""

    digest = hashlib.sha256()

    with open(
        path,
        "rb",
    ) as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _parser_signature():
    """Return a signature for the parser code used by the cache.

    During development, hash the parser source files so changes
    automatically invalidate the parsed-logbook cache.

    In a PyInstaller build, parser modules are packaged inside the
    application archive and are not guaranteed to exist as normal
    filesystem files. Use an explicit frozen parser-cache version
    instead.
    """

    if getattr(sys, "frozen", False):
        return "flightstats-parser-cache-v2"

    parser_files = [
        Path(__file__).resolve().parent
        / "parser"
        / "easa_pdf.py",
        Path(__file__).resolve().parent
        / "parser"
        / "csv.py",
        Path(__file__).resolve().parent
        / "parser"
        / "loader.py",
        Path(__file__).resolve().parent
        / "parser"
        / "models.py",
    ]

    digest = hashlib.sha256()

    for path in parser_files:
        digest.update(
            path.read_bytes()
        )

    return digest.hexdigest()


def _cache_path():
    """Return the macOS Application Support path for the parsed-logbook cache."""

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    return (
        CACHE_DIR
        / "logbook_parsed.json"
    )


def _time_to_string(value):
    """Serialize a datetime.time value."""

    if value is None:
        return None

    return value.isoformat()


def _string_to_time(value):
    """Deserialize a datetime.time value."""

    if value is None:
        return None

    return time.fromisoformat(
        value
    )


def _serialize_cache_value(value):
    """Serialize values used in discrepancy records."""

    if isinstance(value, date):
        return {
            "__type__": "date",
            "value": value.isoformat(),
        }

    if isinstance(value, time):
        return {
            "__type__": "time",
            "value": value.isoformat(),
        }

    if isinstance(value, dict):
        return {
            key: _serialize_cache_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _serialize_cache_value(item)
            for item in value
        ]

    return value


def _deserialize_cache_value(value):
    """Restore values used in discrepancy records."""

    if isinstance(value, dict):

        if value.get("__type__") == "date":
            return date.fromisoformat(
                value["value"]
            )

        if value.get("__type__") == "time":
            return time.fromisoformat(
                value["value"]
            )

        return {
            key: _deserialize_cache_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _deserialize_cache_value(item)
            for item in value
        ]

    return value


def _flight_to_dict(flight):
    """Serialize one Flight dataclass."""

    return {
        "date": flight.date.isoformat(),
        "departure": flight.departure,
        "departure_time": _time_to_string(
            flight.departure_time
        ),
        "arrival": flight.arrival,
        "arrival_time": _time_to_string(
            flight.arrival_time
        ),
        "aircraft": flight.aircraft,
        "registration": flight.registration,
        "flight_minutes": flight.flight_minutes,
    }


def _dict_to_flight(item):
    """Deserialize one Flight dataclass."""

    from parser.models import Flight

    return Flight(
        date=date.fromisoformat(
            item["date"]
        ),
        departure=item["departure"],
        departure_time=_string_to_time(
            item.get("departure_time")
        ),
        arrival=item["arrival"],
        arrival_time=_string_to_time(
            item.get("arrival_time")
        ),
        aircraft=item["aircraft"],
        registration=item["registration"],
        flight_minutes=item.get(
            "flight_minutes"
        ),
    )


def _load_cached_flights(
    logbook_path,
    include_discrepancies=False,
    allow_missing_logbook=False,
):
    """
    Load parsed flights from cache.

    When the original logbook exists, the cache is validated against
    its SHA-256 digest and the parser signature.

    When allow_missing_logbook is True and the original logbook is
    unavailable, the cache can still be used as long as its cache
    version and parser signature are valid.
    """

    cache_path = _cache_path()

    if not cache_path.exists():
        return None

    logbook_path = Path(
        logbook_path
    ).expanduser()

    logbook_exists = (
        logbook_path.exists()
        and logbook_path.is_file()
    )

    if (
        not logbook_exists
        and not allow_missing_logbook
    ):
        return None

    try:
        with open(
            cache_path,
            "r",
            encoding="utf-8",
        ) as file:
            cache = json.load(file)

        if cache.get(
            "cache_version"
        ) != CACHE_VERSION:
            return None

        if logbook_exists:

            if cache.get(
                "logbook_sha256"
            ) != _file_sha256(
                logbook_path
            ):
                return None

        elif not allow_missing_logbook:
            return None

        if cache.get(
            "parser_signature"
        ) != _parser_signature():
            return None

        flights = [
            _dict_to_flight(item)
            for item in cache.get(
                "flights",
                [],
            )
        ]

        if include_discrepancies:
            discrepancies = [
                _deserialize_cache_value(item)
                for item in cache.get(
                    "discrepancies",
                    [],
                )
            ]

            return (
                flights,
                discrepancies,
            )

        return flights

    except Exception:
        # A corrupt or incompatible cache must never prevent
        # FlightStats from loading the original logbook.
        return None


def _save_cached_flights(
    logbook_path,
    flights,
    discrepancies=None,
):
    """Save parsed flights and discrepancies to the local JSON cache."""

    cache_path = _cache_path()

    cache = {
        "cache_version": CACHE_VERSION,
        "logbook_sha256": _file_sha256(
            logbook_path
        ),
        "parser_signature": _parser_signature(),
        "flights": [
            _flight_to_dict(flight)
            for flight in flights
        ],
        "discrepancies": [
            _serialize_cache_value(item)
            for item in (
                discrepancies or []
            )
        ],
    }

    temporary_path = cache_path.with_suffix(
        ".tmp"
    )

    try:
        with open(
            temporary_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                cache,
                file,
                ensure_ascii=False,
                indent=2,
            )

        temporary_path.replace(
            cache_path
        )

    except Exception:
        # Caching is an optimization. A cache write failure must
        # never break a successful logbook load.
        try:
            temporary_path.unlink(
                missing_ok=True
            )
        except Exception:
            pass



class FlightStatsData:
    """
    Central data and analysis layer for FlightStats.

    The logbook is parsed once and all derived statistics
    are calculated from the resulting flight dataset.
    """

    def __init__(
        self,
        logbook_path,
        progress_callback=None,
        discrepancy_callback=None,
    ):
        self.logbook_path = logbook_path
        self.progress_callback = (
            progress_callback
        )
        self.discrepancy_callback = (
            discrepancy_callback
        )

        self.flights = []
        self.discrepancies = []
        self.flight_distances = []
        self.fuel_results = []
        self.fuel_summary = {}
        self.speed_results = []
        self.speed_summary = {}
        self.airports = set()

        self.total_flight_minutes = 0
        self.total_distance_km = 0.0

        self.calculated_distance_flights = 0
        self.unresolved_distance_flights = 0

        self.airport_database = None
        self.fuel_database = None

        self.load()

    def report_discrepancy(
        self,
        discrepancy,
    ):
        """Store and optionally forward a parser discrepancy."""

        self.discrepancies.append(
            discrepancy
        )

        if self.discrepancy_callback is not None:
            self.discrepancy_callback(
                discrepancy
            )

    def report_progress(
        self,
        percent,
        message,
    ):
        """
        Report loading progress.

        The callback is optional so the data manager
        can still be used from the terminal/tests.
        """

        if self.progress_callback is not None:
            self.progress_callback(
                percent,
                message,
            )
        else:
            print(
                f"[{percent:3d}%] {message}"
            )

    def load(self):
        """
        Load the logbook and calculate all statistics.
        """

        # =================================================
        # PARSE LOGBOOK
        # =================================================

        self.report_progress(
            0,
            "Checking logbook cache...",
        )

        cached_data = _load_cached_flights(
            self.logbook_path,
            include_discrepancies=True,
            allow_missing_logbook=True,
        )

        if cached_data is None:
            self.flights = None
            self.discrepancies = []
        else:
            (
                self.flights,
                self.discrepancies,
            ) = cached_data

        if self.flights is None:
            self.report_progress(
                2,
                "Parsing logbook...",
            )

            self.discrepancies = []

            self.flights = parse_flight_file(
                self.logbook_path,
                discrepancy_callback=(
                    self.report_discrepancy
                ),
            )

            _save_cached_flights(
                self.logbook_path,
                self.flights,
                self.discrepancies,
            )

            self.report_progress(
                18,
                "Parsed logbook cached",
            )
        else:
            self.report_progress(
                18,
                "Loaded parsed logbook from cache",
            )

        self.total_flight_minutes = sum(
            flight.flight_minutes
            for flight in self.flights
        )

        self.report_progress(
            20,
            (
                f"Logbook ready — "
                f"{len(self.flights):,} flights found"
            ),
        )

        # =================================================
        # AIRPORTS
        # =================================================

        self.report_progress(
            25,
            "Building airport list...",
        )

        self.airports = set()

        for flight in self.flights:
            self.airports.add(
                flight.departure
            )

            self.airports.add(
                flight.arrival
            )

        # =================================================
        # AIRPORT DATABASE
        # =================================================

        self.report_progress(
            30,
            "Loading airport database...",
        )

        self.airport_database = (
            AirportDatabase()
        )

        # =================================================
        # DISTANCE
        # =================================================

        self.report_progress(
            35,
            "Calculating flight distances...",
        )

        def distance_progress(
            percent,
            message,
        ):
            """
            Convert distance progress (0–100)
            into overall progress (35–65).
            """

            overall_percent = (
                35
                + int(
                    percent
                    * 0.30
                )
            )

            self.report_progress(
                overall_percent,
                message,
            )

        self.flight_distances = (
            calculate_all_distances(
                self.flights,
                self.airport_database,
                progress_callback=(
                    distance_progress
                ),
            )
        )

        self.total_distance_km = (
            total_distance_km(
                self.flight_distances
            )
        )

        self.calculated_distance_flights = sum(
            1
            for result
            in self.flight_distances
            if result["distance_km"]
            is not None
        )

        self.unresolved_distance_flights = (
            len(self.flights)
            - self.calculated_distance_flights
        )

        self.report_progress(
            65,
            "Flight distances calculated",
        )

        # =================================================
        # FUEL DATABASE
        # =================================================

        self.report_progress(
            68,
            "Loading fuel database...",
        )

        self.fuel_database = (
            FuelDatabase()
        )

        # =================================================
        # FUEL
        # =================================================

        self.report_progress(
            72,
            "Calculating estimated fuel...",
        )

        def fuel_progress(
            percent,
            message,
        ):
            """
            Convert fuel progress (0–100)
            into overall progress (72–84).
            """

            overall_percent = (
                72
                + int(
                    percent
                    * 0.12
                )
            )

            self.report_progress(
                overall_percent,
                message,
            )

        self.fuel_results = (
            calculate_all_fuel(
                self.flights,
                self.fuel_database,
                progress_callback=(
                    fuel_progress
                ),
            )
        )

        self.fuel_summary = (
            summarize_fuel(
                self.fuel_results
            )
        )

        self.report_progress(
            84,
            "Fuel analysis complete",
        )

        # =================================================
        # SECTOR SPEED
        # =================================================

        self.report_progress(
            87,
            "Calculating sector speeds...",
        )

        def speed_progress(
            percent,
            message,
        ):
            """
            Convert sector-speed progress (0–100)
            into overall progress (87–97).
            """

            overall_percent = (
                87
                + int(
                    percent
                    * 0.10
                )
            )

            self.report_progress(
                overall_percent,
                message,
            )

        self.speed_results = (
            calculate_all_sector_speeds(
                self.flights,
                self.flight_distances,
                progress_callback=(
                    speed_progress
                ),
            )
        )

        self.speed_summary = (
            summarize_sector_speed(
                self.speed_results
            )
        )

        self.report_progress(
            97,
            "Finalizing statistics...",
        )

        # =================================================
        # COMPLETE
        # =================================================

        self.report_progress(
            100,
            "FlightStats data loaded",
        )

    def refresh(self):
        """
        Reload the logbook and recalculate
        all derived statistics.
        """

        self.load()

    @property
    def total_flights(self):
        """Return total number of flights."""

        return len(self.flights)

    @property
    def fuel_totals(self):
        """Return total estimated fuel by unit."""

        return self.fuel_summary.get(
            "totals",
            {},
        )

    @property
    def aircraft_summary(self):
        """Return aircraft fuel summaries."""

        return self.fuel_summary.get(
            "by_aircraft",
            {},
        )

    @property
    def aircraft_speed_summary(self):
        """Return sector-speed summaries."""

        return self.speed_summary