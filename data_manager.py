from parser.easa_pdf import parse_logbook
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
    ):
        self.logbook_path = logbook_path
        self.progress_callback = (
            progress_callback
        )

        self.flights = []
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

        def logbook_progress(
            percent,
            message,
        ):
            """
            Convert parser progress (0–100)
            into overall progress (0–20).
            """

            overall_percent = int(
                percent * 0.20
            )

            self.report_progress(
                overall_percent,
                message,
            )

        self.flights = parse_logbook(
            self.logbook_path,
            progress_callback=(
                logbook_progress
            ),
        )

        self.total_flight_minutes = sum(
            flight.flight_minutes
            for flight in self.flights
        )

        self.report_progress(
            20,
            (
                f"Logbook parsed — "
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
                    percent * 0.30
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
                    percent * 0.12
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
                    percent * 0.10
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