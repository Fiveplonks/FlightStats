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

from gui_components import LogbookDropZone, MetricCard
from gui_flight_time_chart import FlightTimeChart, monthly_cumulative_flight_time
from gui_unit_dialog import UnitSettingsDialog
from gui_units import UnitSettings, format_distance, format_fuel_quantity
from gui_utils import format_hours


class DashboardPage(QWidget):
    """Main FlightStats dashboard."""

    logbook_selected = Signal(str)
    units_changed = Signal()

    def __init__(self):
        super().__init__()
        self._data = None
        self.units = UnitSettings()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 35, 40, 35)
        self.layout.setSpacing(20)

        header = QHBoxLayout()
        title_layout = QVBoxLayout()

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")
        subtitle = QLabel("FlightStats overview")
        subtitle.setObjectName("pageSubtitle")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header.addLayout(title_layout)
        header.addStretch()

        self.units_button = QPushButton("Units")
        self.units_button.setObjectName("refreshButton")
        self.units_button.setCursor(Qt.PointingHandCursor)
        self.units_button.clicked.connect(self.open_units_dialog)
        header.addWidget(self.units_button)

        self.change_logbook_button = QPushButton("Change Logbook")
        self.change_logbook_button.setObjectName("refreshButton")
        self.change_logbook_button.setCursor(Qt.PointingHandCursor)
        header.addWidget(self.change_logbook_button)

        self.refresh_button = QPushButton("Refresh Logbook")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        header.addWidget(self.refresh_button)
        self.layout.addLayout(header)

        self.logbook_drop_zone = LogbookDropZone()
        self.logbook_drop_zone.logbook_selected.connect(self.logbook_selected)
        self.layout.addWidget(self.logbook_drop_zone)

        self.logbook_status_label = QLabel("")
        self.logbook_status_label.setObjectName("logbookStatusLabel")
        self.logbook_status_label.setWordWrap(True)
        self.layout.addWidget(self.logbook_status_label)

        self.loading_frame = QFrame()
        self.loading_frame.setObjectName("loadingFrame")
        loading_layout = QVBoxLayout(self.loading_frame)
        loading_layout.setContentsMargins(0, 5, 0, 5)
        loading_layout.setSpacing(6)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progressBar")
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        loading_layout.addWidget(self.status_label)
        loading_layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.loading_frame)

        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)

        self.flights_card = MetricCard("Flights")
        self.time_card = MetricCard("Calculated flight time")
        self.previous_experience_card = MetricCard("Previous experience")
        self.validated_logbook_card = MetricCard("Validated logbook time")
        self.total_experience_card = MetricCard("Total experience")
        self.distance_card = MetricCard("Distance")
        self.jet_fuel_card = MetricCard("Estimated jet fuel")
        self.piston_fuel_card = MetricCard("Estimated Avgas")
        self.airports_card = MetricCard("Airports")

        cards = (
            (self.flights_card, 0, 0),
            (self.time_card, 0, 1),
            (self.previous_experience_card, 0, 2),
            (self.total_experience_card, 1, 0),
            (self.validated_logbook_card, 1, 1),
            (self.distance_card, 1, 2),
            (self.jet_fuel_card, 2, 0),
            (self.piston_fuel_card, 2, 1),
            (self.airports_card, 2, 2),
        )
        for widget, row, column in cards:
            cards_layout.addWidget(widget, row, column)
        self.layout.addLayout(cards_layout)

        # High-level career graph. It is intentionally monthly rather than
        # per-flight so a 1,500+ flight logbook remains readable.
        graph_frame = QFrame()
        graph_frame.setObjectName("careerStatsFrame")
        graph_layout = QVBoxLayout(graph_frame)
        graph_layout.setContentsMargins(18, 14, 18, 14)
        graph_layout.setSpacing(8)

        graph_title = QLabel("Total flying hours")
        graph_title.setObjectName("careerStatsTitle")
        graph_layout.addWidget(graph_title)

        graph_subtitle = QLabel("Cumulative logbook flight time by month")
        graph_subtitle.setObjectName("pageSubtitle")
        graph_layout.addWidget(graph_subtitle)

        self.flight_time_chart = FlightTimeChart(
            export_title="FlightStats Total Flying Hours"
        )
        graph_layout.addWidget(self.flight_time_chart)
        self.graph_frame = graph_frame
        self.layout.addWidget(graph_frame)

        self.year_tabs = QTabWidget()
        self.year_tabs.setObjectName("yearTabs")
        year_bar = self.year_tabs.tabBar()
        year_bar.setUsesScrollButtons(True)
        year_bar.setExpanding(False)
        self.year_tabs.currentChanged.connect(self.year_tab_changed)
        self.layout.addWidget(self.year_tabs)

        self.career_stats_frame = QFrame()
        self.career_stats_frame.setObjectName("careerStatsFrame")
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
        career_layout = QVBoxLayout(self.career_stats_frame)
        career_layout.setContentsMargins(22, 18, 22, 18)
        career_layout.setSpacing(12)

        career_title = QLabel("Career stats")
        career_title.setObjectName("careerStatsTitle")
        career_layout.addWidget(career_title)

        career_grid = QGridLayout()
        career_grid.setHorizontalSpacing(35)
        career_grid.setVerticalSpacing(12)
        self.career_stat_labels = {}

        career_items = (
            ("first_flight", "First flight"),
            ("latest_flight", "Latest flight"),
            ("longest_flight", "Longest flight"),
            ("top_aircraft", "Most flown aircraft"),
            ("top_airport", "Most visited airport"),
            ("airport_count", "Airports visited"),
        )
        for index, (key, item_title) in enumerate(career_items):
            row = index // 3
            column = index % 3
            item_widget = QWidget()
            item_layout = QVBoxLayout(item_widget)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(2)
            label = QLabel(item_title)
            label.setObjectName("careerStatLabel")
            value = QLabel("—")
            value.setObjectName("careerStatValue")
            item_layout.addWidget(label)
            item_layout.addWidget(value)
            career_grid.addWidget(item_widget, row, column)
            self.career_stat_labels[key] = value

        career_layout.addLayout(career_grid)
        self.layout.addWidget(self.career_stats_frame)
        self.layout.addStretch()

    def open_units_dialog(self):
        dialog = UnitSettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.units.load()
            if self._data is not None:
                current = self.year_tabs.currentIndex()
                self.update_for_year(self._year_from_index(current))
                self.update_flight_time_chart(self._data.flights)
            self.units_changed.emit()

    def _year_from_index(self, index):
        if index < 0:
            return None
        text = self.year_tabs.tabText(index)
        return None if text == "ALL" else int(text)

    def show_logbook_selector(self, message=None):
        self.logbook_drop_zone.show()
        self.logbook_status_label.show()
        self.logbook_status_label.setText(
            message or "No logbook selected. Choose your flight logbook PDF to begin."
        )
        self.loading_frame.hide()
        for widget in (
            self.flights_card, self.time_card, self.previous_experience_card,
            self.validated_logbook_card, self.total_experience_card,
            self.distance_card, self.jet_fuel_card, self.piston_fuel_card,
            self.airports_card, self.graph_frame, self.year_tabs,
            self.career_stats_frame,
        ):
            widget.hide()

    def show_loading(self):
        self.logbook_drop_zone.hide()
        self.logbook_status_label.hide()
        self.loading_frame.show()
        for widget in (
            self.flights_card, self.time_card, self.previous_experience_card,
            self.total_experience_card, self.distance_card, self.jet_fuel_card,
            self.piston_fuel_card, self.airports_card, self.graph_frame,
            self.year_tabs, self.career_stats_frame,
        ):
            widget.hide()

    def show_statistics(self, logbook_path):
        self.logbook_drop_zone.hide()
        self.logbook_status_label.show()
        self.logbook_status_label.setText(
            f"Current logbook: {Path(logbook_path).name}"
        )
        self.loading_frame.hide()
        for widget in (
            self.flights_card, self.time_card, self.previous_experience_card,
            self.total_experience_card, self.distance_card, self.jet_fuel_card,
            self.piston_fuel_card, self.airports_card, self.graph_frame,
            self.year_tabs, self.career_stats_frame,
        ):
            widget.show()

    def set_data(self, data, logbook_path=None):
        self._data = data
        if logbook_path is not None:
            self.show_statistics(logbook_path)
        self.update_flight_time_chart(data.flights)
        self.build_year_tabs()

    def update_flight_time_chart(self, flights):
        self.flight_time_chart.set_points(monthly_cumulative_flight_time(flights))

    def build_year_tabs(self):
        self.year_tabs.blockSignals(True)
        self.year_tabs.clear()
        years = sorted({flight.date.year for flight in self._data.flights}, reverse=True)
        self.year_tabs.addTab(QWidget(), "ALL")
        for year in years:
            self.year_tabs.addTab(QWidget(), str(year))
        self.year_tabs.blockSignals(False)
        self.year_tabs.setCurrentIndex(0)
        self.update_for_year(None)

    def year_tab_changed(self, index):
        if index < 0:
            return
        self.update_for_year(self._year_from_index(index))

    def update_for_year(self, year):
        flights = [
            flight for flight in self._data.flights
            if year is None or flight.date.year == year
        ]
        indexes = [
            index for index, flight in enumerate(self._data.flights)
            if year is None or flight.date.year == year
        ]

        total_minutes = sum(flight.flight_minutes or 0 for flight in flights)
        validated_logged_minutes = sum(
            flight.logged_flight_minutes or 0
            for flight in flights
            if flight.logged_time_status == "valid"
        )

        total_distance = 0.0
        jet_fuel = 0.0
        piston_fuel = 0.0
        for index in indexes:
            if index < len(self._data.flight_distances):
                result = self._data.flight_distances[index]
                if isinstance(result, dict):
                    distance = result.get("distance_km")
                    if distance is not None:
                        total_distance += distance
            if index < len(self._data.fuel_results):
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

        self.flights_card.set_value(f"{len(flights):,}")
        self.time_card.set_value(format_hours(total_minutes))
        previous_experience = self._data.previous_experience_minutes or 0
        self.previous_experience_card.set_value(format_hours(previous_experience))
        self.validated_logbook_card.set_value(format_hours(validated_logged_minutes))
        self.total_experience_card.set_value(format_hours(total_minutes + previous_experience))
        self.distance_card.set_value(format_distance(total_distance, self.units.distance_unit))

        jet_display = format_fuel_quantity(jet_fuel, "kg/h", self.units.fuel_unit)
        piston_display = format_fuel_quantity(piston_fuel, "L/h", self.units.fuel_unit)
        self.jet_fuel_card.set_value(jet_display)
        self.piston_fuel_card.set_value(piston_display)
        self.airports_card.set_value(f"{len(airports):,}")
        self.update_career_stats(flights)

    def update_career_stats(self, flights):
        if not flights:
            for label in self.career_stat_labels.values():
                label.setText("—")
            return

        dated_flights = [flight for flight in flights if getattr(flight, "date", None) is not None]
        if dated_flights:
            first_flight = min(dated_flights, key=lambda flight: flight.date)
            latest_flight = max(dated_flights, key=lambda flight: flight.date)
            self.career_stat_labels["first_flight"].setText(first_flight.date.strftime("%d %b %Y"))
            self.career_stat_labels["latest_flight"].setText(latest_flight.date.strftime("%d %b %Y"))
        else:
            self.career_stat_labels["first_flight"].setText("—")
            self.career_stat_labels["latest_flight"].setText("—")

        longest_minutes = max((getattr(flight, "flight_minutes", 0) or 0) for flight in flights)
        self.career_stat_labels["longest_flight"].setText(format_hours(longest_minutes))

        database = FuelDatabase()
        aircraft_counts = {}
        for flight in flights:
            aircraft = database.normalize_type(flight.aircraft)
            aircraft_counts[aircraft] = aircraft_counts.get(aircraft, 0) + 1
        if aircraft_counts:
            top_aircraft = max(aircraft_counts, key=aircraft_counts.get)
            self.career_stat_labels["top_aircraft"].setText(
                f"{top_aircraft} ({aircraft_counts[top_aircraft]} flights)"
            )
        else:
            self.career_stat_labels["top_aircraft"].setText("—")

        airport_counts = {}
        for flight in flights:
            for airport in (flight.departure, flight.arrival):
                if airport:
                    airport_counts[airport] = airport_counts.get(airport, 0) + 1
        if airport_counts:
            top_airport = max(airport_counts, key=airport_counts.get)
            self.career_stat_labels["top_airport"].setText(
                f"{top_airport} ({airport_counts[top_airport]} visits)"
            )
        else:
            self.career_stat_labels["top_airport"].setText("—")
        self.career_stat_labels["airport_count"].setText(f"{len(airport_counts):,}")
