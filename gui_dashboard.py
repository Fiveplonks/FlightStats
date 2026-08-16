"""Dashboard page for FlightStats."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from parser.fuel import FuelDatabase

from gui_components import (
    LogbookDropZone,
    MetricCard,
)
from gui_utils import format_hours

class DashboardPage(QWidget):
    """Main FlightStats dashboard."""

    logbook_selected = Signal(str)

    def __init__(self):
        super().__init__()

        self.layout = QVBoxLayout(
            self
        )

        self.layout.setContentsMargins(
            40,
            35,
            40,
            35,
        )

        self.layout.setSpacing(20)

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        header = QHBoxLayout()

        title_layout = QVBoxLayout()

        title = QLabel(
            "Dashboard"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "FlightStats overview"
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        title_layout.addWidget(
            title
        )

        title_layout.addWidget(
            subtitle
        )

        header.addLayout(
            title_layout
        )

        header.addStretch()

        self.change_logbook_button = QPushButton(
            "Change Logbook"
        )

        self.change_logbook_button.setObjectName(
            "refreshButton"
        )

        self.change_logbook_button.setCursor(
            Qt.PointingHandCursor
        )

        header.addWidget(
            self.change_logbook_button
        )

        self.refresh_button = QPushButton(
            "Refresh Logbook"
        )

        self.refresh_button.setObjectName(
            "refreshButton"
        )

        self.refresh_button.setCursor(
            Qt.PointingHandCursor
        )

        header.addWidget(
            self.refresh_button
        )

        self.layout.addLayout(
            header
        )

        # -------------------------------------------------
        # -------------------------------------------------
        # LOGBOOK SELECTION
        # -------------------------------------------------

        self.logbook_drop_zone = LogbookDropZone()

        self.logbook_drop_zone.logbook_selected.connect(
            self.logbook_selected
        )

        self.layout.addWidget(
            self.logbook_drop_zone
        )

        self.logbook_status_label = QLabel(
            ""
        )

        self.logbook_status_label.setObjectName(
            "logbookStatusLabel"
        )

        self.logbook_status_label.setWordWrap(
            True
        )

        self.layout.addWidget(
            self.logbook_status_label
        )

        # LOADING AREA
        # -------------------------------------------------

        self.loading_frame = QFrame()

        self.loading_frame.setObjectName(
            "loadingFrame"
        )

        loading_layout = QVBoxLayout(
            self.loading_frame
        )

        loading_layout.setContentsMargins(
            0,
            5,
            0,
            5,
        )

        loading_layout.setSpacing(
            6
        )

        self.status_label = QLabel(
            "Ready"
        )

        self.status_label.setObjectName(
            "statusLabel"
        )

        self.progress_bar = QProgressBar()

        self.progress_bar.setObjectName(
            "progressBar"
        )

        self.progress_bar.setMinimum(
            0
        )

        self.progress_bar.setMaximum(
            100
        )

        self.progress_bar.setValue(
            0
        )

        self.progress_bar.setTextVisible(
            True
        )

        loading_layout.addWidget(
            self.status_label
        )

        loading_layout.addWidget(
            self.progress_bar
        )

        self.layout.addWidget(
            self.loading_frame
        )

        # -------------------------------------------------
        # KPI CARDS
        # -------------------------------------------------

        cards_layout = QGridLayout()

        cards_layout.setSpacing(
            15
        )

        self.flights_card = MetricCard(
            "Flights"
        )

        self.time_card = MetricCard(
            "Calculated flight time"
        )

        self.previous_experience_card = MetricCard(
            "Previous experience"
        )

        self.validated_logbook_card = MetricCard(
            "Validated logbook time"
        )

        self.total_experience_card = MetricCard(
            "Total experience"
        )

        self.distance_card = MetricCard(
            "Distance"
        )

        self.jet_fuel_card = MetricCard(
            "Estimated jet fuel"
        )

        self.piston_fuel_card = MetricCard(
            "Estimated Avgas"
        )

        self.airports_card = MetricCard(
            "Airports"
        )

        cards_layout.addWidget(
            self.flights_card,
            0,
            0,
        )

        cards_layout.addWidget(
            self.time_card,
            0,
            1,
        )

        cards_layout.addWidget(
            self.previous_experience_card,
            0,
            2,
        )

        cards_layout.addWidget(
            self.total_experience_card,
            1,
            0,
        )

        cards_layout.addWidget(
            self.validated_logbook_card,
            1,
            1,
        )

        cards_layout.addWidget(
            self.distance_card,
            1,
            2,
        )

        cards_layout.addWidget(
            self.jet_fuel_card,
            2,
            0,
        )

        cards_layout.addWidget(
            self.piston_fuel_card,
            2,
            1,
        )

        cards_layout.addWidget(
            self.airports_card,
            2,
            2,
        )

        self.layout.addLayout(
            cards_layout
        )

        # -------------------------------------------------
        # YEAR TABS
        # -------------------------------------------------

        self.year_tabs = QTabWidget()
        self.year_tabs.setObjectName(
            "yearTabs"
        )

        # Allow the year buttons to scroll horizontally when there
        # are more years than can fit in the available window width.
        year_bar = self.year_tabs.tabBar()

        year_bar.setUsesScrollButtons(
            True
        )

        year_bar.setExpanding(
            False
        )
        self.year_tabs.currentChanged.connect(
            self.year_tab_changed
        )

        self.layout.addWidget(
            self.year_tabs
        )

        # -------------------------------------------------
        # CAREER STATS
        # -------------------------------------------------

        self.career_stats_frame = QFrame()

        self.career_stats_frame.setObjectName(
            "careerStatsFrame"
        )

        self.career_stats_frame.setStyleSheet(
            """
            QFrame#careerStatsFrame {
                background-color: #ffffff;
                border: 1px solid #dce3ea;
                border-radius: 10px;
            }

            QLabel#careerStatsTitle {
                color: #152238;
                font-size: 17px;
                font-weight: 700;
            }

            QLabel#careerStatLabel {
                color: #718096;
                font-size: 11px;
                font-weight: 600;
            }

            QLabel#careerStatValue {
                color: #152238;
                font-size: 15px;
                font-weight: 700;
            }
            """
        )

        career_layout = QVBoxLayout(
            self.career_stats_frame
        )

        career_layout.setContentsMargins(
            22,
            18,
            22,
            18,
        )

        career_layout.setSpacing(
            12
        )

        career_title = QLabel(
            "Career stats"
        )

        career_title.setObjectName(
            "careerStatsTitle"
        )

        career_layout.addWidget(
            career_title
        )

        career_grid = QGridLayout()

        career_grid.setHorizontalSpacing(
            35
        )

        career_grid.setVerticalSpacing(
            12
        )

        self.career_stat_labels = {}

        career_items = (
            ("first_flight", "First flight"),
            ("latest_flight", "Latest flight"),
            ("longest_flight", "Longest flight"),
            ("top_aircraft", "Most flown aircraft"),
            ("top_airport", "Most visited airport"),
            ("airport_count", "Airports visited"),
        )

        for index, (
            key,
            title,
        ) in enumerate(
            career_items
        ):
            row = index // 3
            column = index % 3

            item_widget = QWidget()

            item_layout = QVBoxLayout(
                item_widget
            )

            item_layout.setContentsMargins(
                0,
                0,
                0,
                0,
            )

            item_layout.setSpacing(
                2
            )

            label = QLabel(
                title
            )

            label.setObjectName(
                "careerStatLabel"
            )

            value = QLabel(
                "—"
            )

            value.setObjectName(
                "careerStatValue"
            )

            item_layout.addWidget(
                label
            )

            item_layout.addWidget(
                value
            )

            career_grid.addWidget(
                item_widget,
                row,
                column,
            )

            self.career_stat_labels[
                key
            ] = value

        career_layout.addLayout(
            career_grid
        )

        self.layout.addWidget(
            self.career_stats_frame
        )

        self.layout.addStretch()

    def show_logbook_selector(self, message=None):
        """Show the logbook selector and hide statistics."""
        self.logbook_drop_zone.show()
        self.logbook_status_label.show()

        if message:
            self.logbook_status_label.setText(
                message
            )
        else:
            self.logbook_status_label.setText(
                "No logbook selected. Choose your flight logbook PDF to begin."
            )

        self.loading_frame.hide()

        for widget in (
            self.flights_card,
            self.time_card,
            self.previous_experience_card,
            self.validated_logbook_card,
            self.total_experience_card,
            self.distance_card,
            self.jet_fuel_card,
            self.piston_fuel_card,
            self.airports_card,
            self.year_tabs,
            self.career_stats_frame,
        ):
            widget.hide()

    def show_loading(self):
        """Show loading state while keeping the dashboard compact."""
        self.logbook_drop_zone.hide()
        self.logbook_status_label.hide()
        self.loading_frame.show()

        for widget in (
            self.flights_card,
            self.time_card,
            self.previous_experience_card,
            self.total_experience_card,
            self.distance_card,
            self.jet_fuel_card,
            self.piston_fuel_card,
            self.airports_card,
            self.year_tabs,
            self.career_stats_frame,
        ):
            widget.hide()

    def show_statistics(self, logbook_path):
        """Show loaded statistics and the current logbook path."""
        self.logbook_drop_zone.hide()
        self.logbook_status_label.show()
        self.logbook_status_label.setText(
            f"Current logbook: {Path(logbook_path).name}"
        )

        # Parsing has completed. The loading/progress area
        # should not remain visible on the finished dashboard.
        self.loading_frame.hide()

        for widget in (
            self.flights_card,
            self.time_card,
            self.previous_experience_card,
            self.total_experience_card,
            self.distance_card,
            self.jet_fuel_card,
            self.piston_fuel_card,
            self.airports_card,
            self.year_tabs,
            self.career_stats_frame,
        ):
            widget.show()

    def set_data(self, data, logbook_path=None):
        """Load data and build Dashboard year tabs."""

        self._data = data

        if logbook_path is not None:
            self.show_statistics(
                logbook_path
            )

        self.build_year_tabs()

    def build_year_tabs(self):
        """Create one tab for every year in the logbook."""

        self.year_tabs.blockSignals(True)
        self.year_tabs.clear()

        years = sorted(
            {
                flight.date.year
                for flight in self._data.flights
            },
            reverse=True,
        )

        # ALL is the default and is intentionally placed first.
        self.year_tabs.addTab(
            QWidget(),
            "ALL",
        )

        for year in years:
            self.year_tabs.addTab(
                QWidget(),
                str(year),
            )

        self.year_tabs.blockSignals(False)

        # Default to ALL years.
        self.year_tabs.setCurrentIndex(0)
        self.update_for_year(None)

    def year_tab_changed(self, index):
        """Update Dashboard when the selected year changes."""

        if index < 0:
            return

        text = self.year_tabs.tabText(index)

        if text == "ALL":
            year = None
        else:
            year = int(text)

        self.update_for_year(year)

    def update_for_year(self, year):
        """Update Dashboard statistics for one year or all years."""

        flights = [
            flight
            for flight in self._data.flights
            if year is None
            or flight.date.year == year
        ]

        indexes = [
            index
            for index, flight in enumerate(
                self._data.flights
            )
            if year is None
            or flight.date.year == year
        ]

        total_minutes = sum(
            flight.flight_minutes or 0
            for flight in flights
        )

        validated_logged_minutes = sum(
            flight.logged_flight_minutes or 0
            for flight in flights
            if flight.logged_time_status == "valid"
        )

        total_distance = 0.0
        jet_fuel = 0.0
        piston_fuel = 0.0

        for index in indexes:
            if index < len(
                self._data.flight_distances
            ):
                result = self._data.flight_distances[index]

                if isinstance(result, dict):
                    distance = result.get(
                        "distance_km"
                    )

                    if distance is not None:
                        total_distance += distance

            if index < len(
                self._data.fuel_results
            ):
                result = self._data.fuel_results[index]

                if isinstance(result, dict):
                    fuel = result.get("fuel")
                    unit = result.get("unit")

                    if fuel is not None:
                        if unit == "kg/h":
                            jet_fuel += fuel
                        elif unit == "L/h":
                            piston_fuel += fuel

        airports = set()

        for flight in flights:
            airports.add(flight.departure)
            airports.add(flight.arrival)

        self.flights_card.set_value(
            f"{len(flights):,}"
        )
        self.time_card.set_value(
            format_hours(total_minutes)
        )

        previous_experience = (
            self._data.previous_experience_minutes
            or 0
        )

        self.previous_experience_card.set_value(
            format_hours(
                previous_experience
            )
        )

        self.validated_logbook_card.set_value(
            format_hours(
                validated_logged_minutes
            )
        )

        self.total_experience_card.set_value(
            format_hours(
                total_minutes
                + previous_experience
            )
        )

        self.distance_card.set_value(
            f"{total_distance:,.1f} km"
        )
        self.jet_fuel_card.set_value(
            f"{jet_fuel:,.1f} kg"
        )
        self.piston_fuel_card.set_value(
            f"{piston_fuel:,.1f} L"
        )
        self.airports_card.set_value(
            f"{len(airports):,}"
        )

        self.update_career_stats(
            flights
        )

# =========================================================
# LOGBOOK PAGE
# =========================================================


    def update_career_stats(
        self,
        flights,
    ):
        """Update the dashboard career statistics panel."""

        if not flights:
            for label in self.career_stat_labels.values():
                label.setText("—")
            return

        dated_flights = [
            flight
            for flight in flights
            if getattr(
                flight,
                "date",
                None,
            ) is not None
        ]

        # -------------------------------------------------
        # FIRST / LATEST FLIGHT
        # -------------------------------------------------

        if dated_flights:
            first_flight = min(
                dated_flights,
                key=lambda flight: flight.date,
            )

            latest_flight = max(
                dated_flights,
                key=lambda flight: flight.date,
            )

            self.career_stat_labels[
                "first_flight"
            ].setText(
                first_flight.date.strftime(
                    "%d %b %Y"
                )
            )

            self.career_stat_labels[
                "latest_flight"
            ].setText(
                latest_flight.date.strftime(
                    "%d %b %Y"
                )
            )
        else:
            self.career_stat_labels[
                "first_flight"
            ].setText("—")

            self.career_stat_labels[
                "latest_flight"
            ].setText("—")

        # -------------------------------------------------
        # LONGEST FLIGHT
        # -------------------------------------------------

        longest_minutes = max(
            (
                getattr(
                    flight,
                    "flight_minutes",
                    0,
                )
                or 0
            )
            for flight in flights
        )

        self.career_stat_labels[
            "longest_flight"
        ].setText(
            format_hours(
                longest_minutes
            )
        )

        # -------------------------------------------------
        # MOST-FLOWN AIRCRAFT
        # -------------------------------------------------

        database = FuelDatabase()

        aircraft_counts = {}

        for flight in flights:
            aircraft = database.normalize_type(
                flight.aircraft
            )

            aircraft_counts[
                aircraft
            ] = (
                aircraft_counts.get(
                    aircraft,
                    0,
                )
                + 1
            )

        if aircraft_counts:
            top_aircraft = max(
                aircraft_counts,
                key=aircraft_counts.get,
            )

            self.career_stat_labels[
                "top_aircraft"
            ].setText(
                f"{top_aircraft} "
                f"({aircraft_counts[top_aircraft]} flights)"
            )
        else:
            self.career_stat_labels[
                "top_aircraft"
            ].setText("—")

        # -------------------------------------------------
        # MOST-VISITED AIRPORT
        # -------------------------------------------------

        airport_counts = {}

        for flight in flights:
            for airport in (
                flight.departure,
                flight.arrival,
            ):
                if airport:
                    airport_counts[
                        airport
                    ] = (
                        airport_counts.get(
                            airport,
                            0,
                        )
                        + 1
                    )

        if airport_counts:
            top_airport = max(
                airport_counts,
                key=airport_counts.get,
            )

            self.career_stat_labels[
                "top_airport"
            ].setText(
                f"{top_airport} "
                f"({airport_counts[top_airport]} visits)"
            )
        else:
            self.career_stat_labels[
                "top_airport"
            ].setText("—")

        self.career_stat_labels[
            "airport_count"
        ].setText(
            f"{len(airport_counts):,}"
        )

