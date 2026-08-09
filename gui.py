import sys

from PySide6.QtCore import (
    QObject,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from data_manager import FlightStatsData
from parser.fuel import FuelDatabase


LOGBOOK = "logbook.pdf"


def format_hours(minutes):
    """Convert minutes into H:MM format."""

    hours = minutes // 60
    remaining_minutes = minutes % 60

    return f"{hours}:{remaining_minutes:02d}"


def display_fuel_unit(unit):
    """Convert kg/h or L/h into kg or L."""

    return unit.replace("/h", "")


# =========================================================
# DATA LOADING WORKER
# =========================================================


class DataLoaderWorker(QObject):
    """
    Worker responsible for loading FlightStats data
    outside the GUI thread.
    """

    progress = Signal(int, str)

    finished = Signal(object)

    error = Signal(str)

    def __init__(self, logbook_path):
        super().__init__()

        self.logbook_path = logbook_path

    def run(self):
        """Load all FlightStats data."""

        try:

            data = FlightStatsData(
                self.logbook_path,
                progress_callback=(
                    self.report_progress
                ),
            )

            self.finished.emit(
                data
            )

        except Exception as error:

            self.error.emit(
                str(error)
            )

    def report_progress(
        self,
        percent,
        message,
    ):
        """Forward backend progress to the GUI."""

        self.progress.emit(
            percent,
            message,
        )


# =========================================================
# METRIC CARD
# =========================================================


class MetricCard(QFrame):
    """Reusable dashboard metric card."""

    def __init__(
        self,
        title,
        value="—",
    ):
        super().__init__()

        self.setObjectName(
            "card"
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )

        layout.setSpacing(6)

        self.title_label = QLabel(
            title
        )

        self.title_label.setObjectName(
            "cardLabel"
        )

        self.value_label = QLabel(
            value
        )

        self.value_label.setObjectName(
            "cardValue"
        )

        layout.addWidget(
            self.title_label
        )

        layout.addWidget(
            self.value_label
        )

    def set_value(self, value):
        """Update displayed metric."""

        self.value_label.setText(
            value
        )


# =========================================================
# DASHBOARD
# =========================================================


class DashboardPage(QWidget):
    """Main FlightStats dashboard with statistics separated by year."""

    def __init__(self):
        super().__init__()

        self.data = None
        self.selected_year = None
        self.database = FuelDatabase()

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 35, 40, 35)
        self.layout.setSpacing(20)

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

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

        self.refresh_button = QPushButton("Refresh Logbook")
        self.refresh_button.setObjectName("refreshButton")
        self.refresh_button.setCursor(Qt.PointingHandCursor)

        header.addWidget(self.refresh_button)
        self.layout.addLayout(header)

        # -------------------------------------------------
        # YEAR TABS
        # -------------------------------------------------

        self.year_tabs = QTabWidget()
        self.year_tabs.setObjectName("yearTabs")
        self.year_tabs.currentChanged.connect(
            self.year_tab_changed
        )

        self.layout.addWidget(self.year_tabs)

        # -------------------------------------------------
        # LOADING AREA
        # -------------------------------------------------

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

        # -------------------------------------------------
        # KPI CARDS
        # -------------------------------------------------

        cards_layout = QGridLayout()
        cards_layout.setSpacing(15)

        self.flights_card = MetricCard("Flights")
        self.time_card = MetricCard("Flight time")
        self.distance_card = MetricCard("Distance")
        self.jet_fuel_card = MetricCard("Estimated jet fuel")
        self.piston_fuel_card = MetricCard("Estimated piston fuel")
        self.airports_card = MetricCard("Airports")

        cards_layout.addWidget(self.flights_card, 0, 0)
        cards_layout.addWidget(self.time_card, 0, 1)
        cards_layout.addWidget(self.distance_card, 0, 2)
        cards_layout.addWidget(self.jet_fuel_card, 1, 0)
        cards_layout.addWidget(self.piston_fuel_card, 1, 1)
        cards_layout.addWidget(self.airports_card, 1, 2)

        self.layout.addLayout(cards_layout)

        # -------------------------------------------------
        # AIRCRAFT
        # -------------------------------------------------

        aircraft_title = QLabel("Aircraft")
        aircraft_title.setObjectName("sectionTitle")
        self.layout.addWidget(aircraft_title)

        self.aircraft_container = QFrame()
        self.aircraft_container.setObjectName("card")

        self.aircraft_layout = QVBoxLayout(self.aircraft_container)
        self.aircraft_layout.setContentsMargins(20, 15, 20, 15)
        self.aircraft_layout.setSpacing(8)

        self.layout.addWidget(self.aircraft_container)
        self.layout.addStretch()

    def set_data(self, data):
        """Set shared data and rebuild the available year tabs."""
        self.data = data
        self.build_year_tabs()

    def build_year_tabs(self):
        """Create a tab for every year represented in the logbook."""
        self.year_tabs.blockSignals(True)
        self.year_tabs.clear()

        if self.data is None or not self.data.flights:
            self.selected_year = None
            self.year_tabs.addTab(QWidget(), "ALL")
            self.year_tabs.blockSignals(False)
            self.update_dashboard()
            return

        years = sorted(
            {
                flight.date.year
                for flight in self.data.flights
            },
            reverse=True,
        )

        for year in years:
            self.year_tabs.addTab(
                QWidget(),
                str(year),
            )

        self.year_tabs.addTab(
            QWidget(),
            "ALL",
        )

        self.year_tabs.blockSignals(False)

        # Most recent year is the default view.
        # Signals are blocked while the tabs are rebuilt, so
        # selecting the tab does not call year_tab_changed().
        # Explicitly set the selected year and refresh the
        # dashboard now that the logbook has finished loading.
        self.selected_year = years[0]
        self.year_tabs.setCurrentIndex(0)
        self.update_dashboard()

    def year_tab_changed(self, index):
        """Change the active statistics period."""
        if index < 0 or self.data is None:
            return

        text = self.year_tabs.tabText(index)

        if text == "ALL":
            self.selected_year = None
        else:
            try:
                self.selected_year = int(text)
            except ValueError:
                self.selected_year = None

        self.update_dashboard()

    def get_filtered_indices(self):
        """Return original flight indices for the selected period."""
        if self.data is None:
            return []

        if self.selected_year is None:
            return list(range(len(self.data.flights)))

        return [
            index
            for index, flight in enumerate(self.data.flights)
            if flight.date.year == self.selected_year
        ]

    def update_dashboard(self):
        """Update all dashboard statistics for the selected period."""
        if self.data is None:
            return

        indices = self.get_filtered_indices()

        total_minutes = 0
        total_distance = 0.0
        jet_fuel = 0.0
        piston_fuel = 0.0
        airports = set()

        for index in indices:
            flight = self.data.flights[index]

            total_minutes += flight.flight_minutes or 0

            airports.add(flight.departure)
            airports.add(flight.arrival)

            if index < len(self.data.flight_distances):
                distance_result = self.data.flight_distances[index]

                if isinstance(distance_result, dict):
                    distance = distance_result.get("distance_km")

                    if distance is not None:
                        total_distance += distance

            if index < len(self.data.fuel_results):
                fuel_result = self.data.fuel_results[index]

                if isinstance(fuel_result, dict):
                    fuel = fuel_result.get("fuel")
                    unit = fuel_result.get("unit")

                    if fuel is not None:
                        if unit == "kg/h":
                            jet_fuel += fuel
                        elif unit == "L/h":
                            piston_fuel += fuel

        self.flights_card.set_value(
            f"{len(indices):,}"
        )

        self.time_card.set_value(
            format_hours(total_minutes)
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

        flights = [
            self.data.flights[index]
            for index in indices
        ]

        self.update_aircraft(flights)

    def clear_aircraft(self):
        """
        Remove every aircraft row.

        Each row is a QWidget rather than a bare layout, which means
        Qt can reliably remove the complete row and all of its labels.
        """
        while self.aircraft_layout.count() > 0:
            item = self.aircraft_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def update_aircraft(self, flights):
        """Update aircraft summary for the selected period."""
        self.clear_aircraft()

        aircraft_counts = {}
        aircraft_times = {}

        for flight in flights:
            aircraft = self.database.normalize_type(
                flight.aircraft
            )

            aircraft_counts[aircraft] = (
                aircraft_counts.get(aircraft, 0) + 1
            )

            aircraft_times[aircraft] = (
                aircraft_times.get(aircraft, 0)
                + (flight.flight_minutes or 0)
            )

        if not aircraft_counts:
            label = QLabel("No aircraft data available.")
            label.setObjectName("emptyLabel")
            self.aircraft_layout.addWidget(label)
            return

        for aircraft in sorted(
            aircraft_counts,
            key=lambda item: (
                -aircraft_counts[item],
                item,
            ),
        ):
            # IMPORTANT:
            # Use a QWidget as the row container. This ensures
            # that removing the row also removes all three labels.
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(12)

            aircraft_label = QLabel(aircraft)
            aircraft_label.setObjectName("aircraftName")

            count_label = QLabel(
                f"{aircraft_counts[aircraft]:,} flights"
            )
            count_label.setObjectName("aircraftCount")

            time_label = QLabel(
                format_hours(
                    aircraft_times[aircraft]
                )
            )
            time_label.setObjectName("aircraftTime")

            row.addWidget(aircraft_label)
            row.addStretch()
            row.addWidget(count_label)
            row.addWidget(time_label)

            self.aircraft_layout.addWidget(row_widget)


# =========================================================
# SHARED STATISTICS PAGE HELPERS
# =========================================================


class YearStatisticsPage(QWidget):
    """Base class for pages whose statistics can be filtered by year."""

    def __init__(self, title, subtitle):
        super().__init__()

        self.data = None
        self.selected_year = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 35, 40, 35)
        self.layout.setSpacing(15)

        header = QVBoxLayout()

        page_title = QLabel(title)
        page_title.setObjectName("pageTitle")

        page_subtitle = QLabel(subtitle)
        page_subtitle.setObjectName("pageSubtitle")

        header.addWidget(page_title)
        header.addWidget(page_subtitle)

        self.layout.addLayout(header)

        self.year_tabs = QTabWidget()
        self.year_tabs.setObjectName("yearTabs")
        self.year_tabs.currentChanged.connect(
            self.year_tab_changed
        )

        self.layout.addWidget(self.year_tabs)

    def set_data(self, data):
        self.data = data
        self.build_year_tabs()

    def build_year_tabs(self):
        self.year_tabs.blockSignals(True)
        self.year_tabs.clear()

        if self.data is None or not self.data.flights:
            self.year_tabs.addTab(QWidget(), "ALL")
            self.selected_year = None
            self.year_tabs.blockSignals(False)
            self.update_page()
            return

        years = sorted(
            {
                flight.date.year
                for flight in self.data.flights
            },
            reverse=True,
        )

        for year in years:
            self.year_tabs.addTab(
                QWidget(),
                str(year),
            )

        self.year_tabs.addTab(
            QWidget(),
            "ALL",
        )

        self.selected_year = years[0]

        self.year_tabs.setCurrentIndex(0)
        self.year_tabs.blockSignals(False)

        # Explicit initial update; currentChanged is blocked above.
        self.update_page()

    def year_tab_changed(self, index):
        if index < 0 or self.data is None:
            return

        text = self.year_tabs.tabText(index)

        if text == "ALL":
            self.selected_year = None
        else:
            try:
                self.selected_year = int(text)
            except ValueError:
                self.selected_year = None

        self.update_page()

    def get_filtered_indices(self):
        if self.data is None:
            return []

        if self.selected_year is None:
            return list(range(len(self.data.flights)))

        return [
            index
            for index, flight in enumerate(self.data.flights)
            if flight.date.year == self.selected_year
        ]

    def get_filtered_flights(self):
        return [
            self.data.flights[index]
            for index in self.get_filtered_indices()
        ]

    def update_page(self):
        """Implemented by subclasses."""
        pass


def create_table(headers, object_name="statsTable"):
    """Create a consistent FlightStats statistics table."""
    table = QTableWidget()
    table.setObjectName(object_name)
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)

    table.setSortingEnabled(True)
    table.setSelectionBehavior(
        QTableWidget.SelectRows
    )
    table.setSelectionMode(
        QTableWidget.SingleSelection
    )
    table.setEditTriggers(
        QTableWidget.NoEditTriggers
    )
    table.verticalHeader().setVisible(False)

    header = table.horizontalHeader()
    header.setStretchLastSection(True)

    for column in range(len(headers)):
        header.setSectionResizeMode(
            column,
            QHeaderView.ResizeToContents,
        )

    return table


def set_table_item(table, row, column, value):
    """Set one table cell."""
    item = QTableWidgetItem(str(value))
    table.setItem(row, column, item)


def calculate_fuel_totals(data, indices):
    """Return estimated jet and piston fuel totals."""
    jet = 0.0
    piston = 0.0

    for index in indices:
        if index >= len(data.fuel_results):
            continue

        result = data.fuel_results[index]

        if not isinstance(result, dict):
            continue

        fuel = result.get("fuel")
        unit = result.get("unit")

        if fuel is None:
            continue

        if unit == "kg/h":
            jet += fuel
        elif unit == "L/h":
            piston += fuel

    return jet, piston


def calculate_distance(data, indices):
    """Return total calculated distance for selected flights."""
    total = 0.0

    for index in indices:
        if index >= len(data.flight_distances):
            continue

        result = data.flight_distances[index]

        if not isinstance(result, dict):
            continue

        distance = result.get("distance_km")

        if distance is not None:
            total += distance

    return total


def calculate_sector_speed(data, index):
    """Calculate average sector speed from distance and flight time."""
    if index >= len(data.flight_distances):
        return None

    flight = data.flights[index]

    if not flight.flight_minutes:
        return None

    result = data.flight_distances[index]

    if not isinstance(result, dict):
        return None

    distance = result.get("distance_km")

    if distance is None:
        return None

    return distance / flight.flight_minutes * 60.0


# =========================================================
# LOGBOOK PAGE
# =========================================================


class LogbookPage(YearStatisticsPage):
    """Searchable and sortable logbook."""

    def __init__(self):
        super().__init__(
            "Logbook",
            "Browse and search your flight history",
        )

        filter_bar = QHBoxLayout()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Search date, airport, aircraft, registration..."
        )
        self.search_box.setObjectName("searchBox")

        filter_bar.addWidget(
            self.search_box,
            1,
        )

        self.aircraft_filter = QComboBox()
        self.aircraft_filter.setObjectName("filterBox")
        self.aircraft_filter.addItem(
            "All aircraft"
        )

        filter_bar.addWidget(
            self.aircraft_filter
        )

        self.layout.addLayout(filter_bar)

        self.result_label = QLabel("0 flights")
        self.result_label.setObjectName("statusLabel")
        self.layout.addWidget(
            self.result_label
        )

        self.table = create_table(
            [
                "Date",
                "Departure",
                "Dep.",
                "Arrival",
                "Arr.",
                "Aircraft",
                "Registration",
                "Flight Time",
                "Distance",
                "Fuel",
            ],
            "logbookTable",
        )

        self.layout.addWidget(
            self.table,
            1,
        )

        self.search_box.textChanged.connect(
            self.apply_filters
        )

        self.aircraft_filter.currentTextChanged.connect(
            self.apply_filters
        )

    def set_data(self, data):
        self.data = data

        self.aircraft_filter.blockSignals(True)
        self.aircraft_filter.clear()
        self.aircraft_filter.addItem(
            "All aircraft"
        )

        aircraft_types = {
            self.database.normalize_type(
                flight.aircraft
            )
            for flight in data.flights
        }

        for aircraft in sorted(aircraft_types):
            self.aircraft_filter.addItem(
                aircraft
            )

        self.aircraft_filter.blockSignals(False)

        self.build_year_tabs()
        self.apply_filters()

    def update_page(self):
        self.apply_filters()

    def apply_filters(self):
        if self.data is None:
            return

        search_text = (
            self.search_box.text()
            .strip()
            .lower()
        )

        selected_aircraft = (
            self.aircraft_filter.currentText()
        )

        matches = []

        for index in self.get_filtered_indices():
            flight = self.data.flights[index]

            aircraft = self.database.normalize_type(
                flight.aircraft
            )

            if (
                selected_aircraft != "All aircraft"
                and aircraft != selected_aircraft
            ):
                continue

            searchable = " ".join(
                [
                    str(flight.date),
                    flight.departure,
                    flight.arrival,
                    aircraft,
                    flight.registration,
                ]
            ).lower()

            if (
                search_text
                and search_text not in searchable
            ):
                continue

            matches.append(
                (index, flight)
            )

        self.populate_table(matches)

        self.result_label.setText(
            f"{len(matches):,} flights"
        )

    def populate_table(self, matches):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(
            len(matches)
        )

        for row, (
            original_index,
            flight,
        ) in enumerate(matches):

            distance = None

            if original_index < len(
                self.data.flight_distances
            ):
                result = self.data.flight_distances[
                    original_index
                ]

                if isinstance(result, dict):
                    distance = result.get(
                        "distance_km"
                    )

            fuel = None
            fuel_unit = None

            if original_index < len(
                self.data.fuel_results
            ):
                result = self.data.fuel_results[
                    original_index
                ]

                if isinstance(result, dict):
                    fuel = result.get("fuel")
                    fuel_unit = result.get("unit")

            set_table_item(
                self.table,
                row,
                0,
                flight.date.strftime("%Y-%m-%d"),
            )
            set_table_item(
                self.table,
                row,
                1,
                flight.departure,
            )
            set_table_item(
                self.table,
                row,
                2,
                (
                    flight.departure_time.strftime(
                        "%H:%M"
                    )
                    if flight.departure_time
                    else "—"
                ),
            )
            set_table_item(
                self.table,
                row,
                3,
                flight.arrival,
            )
            set_table_item(
                self.table,
                row,
                4,
                (
                    flight.arrival_time.strftime(
                        "%H:%M"
                    )
                    if flight.arrival_time
                    else "—"
                ),
            )
            set_table_item(
                self.table,
                row,
                5,
                self.database.normalize_type(
                    flight.aircraft
                ),
            )
            set_table_item(
                self.table,
                row,
                6,
                flight.registration,
            )
            set_table_item(
                self.table,
                row,
                7,
                format_hours(
                    flight.flight_minutes
                ),
            )
            set_table_item(
                self.table,
                row,
                8,
                (
                    "—"
                    if distance is None
                    else f"{distance:,.1f} km"
                ),
            )
            set_table_item(
                self.table,
                row,
                9,
                (
                    "—"
                    if fuel is None
                    else (
                        f"{fuel:,.1f} "
                        f"{display_fuel_unit(fuel_unit)}"
                    )
                ),
            )

        self.table.setSortingEnabled(True)


# =========================================================
# AIRCRAFT PAGE
# =========================================================


class AircraftPage(YearStatisticsPage):
    """Aircraft statistics for the selected year."""

    def __init__(self):
        super().__init__(
            "Aircraft",
            "Aircraft utilization and performance",
        )

        self.table = create_table(
            [
                "Aircraft",
                "Flights",
                "Flight Time",
                "Distance",
                "Avg. Speed",
                "Jet Fuel",
                "Piston Fuel",
            ],
            "statsTable",
        )

        self.layout.addWidget(
            self.table,
            1,
        )

    def update_page(self):
        if self.data is None:
            return

        indices = self.get_filtered_indices()

        stats = {}

        for index in indices:
            flight = self.data.flights[index]
            aircraft = self.database.normalize_type(
                flight.aircraft
            )

            if aircraft not in stats:
                stats[aircraft] = {
                    "flights": 0,
                    "minutes": 0,
                    "distance": 0.0,
                    "speed_total": 0.0,
                    "speed_count": 0,
                    "jet": 0.0,
                    "piston": 0.0,
                }

            item = stats[aircraft]

            item["flights"] += 1
            item["minutes"] += (
                flight.flight_minutes or 0
            )

            if index < len(
                self.data.flight_distances
            ):
                result = self.data.flight_distances[index]

                if isinstance(result, dict):
                    distance = result.get(
                        "distance_km"
                    )

                    if distance is not None:
                        item["distance"] += distance

            speed = calculate_sector_speed(
                self.data,
                index,
            )

            if speed is not None:
                item["speed_total"] += speed
                item["speed_count"] += 1

            if index < len(
                self.data.fuel_results
            ):
                result = self.data.fuel_results[index]

                if isinstance(result, dict):
                    fuel = result.get("fuel")
                    unit = result.get("unit")

                    if fuel is not None:
                        if unit == "kg/h":
                            item["jet"] += fuel
                        elif unit == "L/h":
                            item["piston"] += fuel

        self.table.setSortingEnabled(False)
        self.table.setRowCount(
            len(stats)
        )

        for row, aircraft in enumerate(
            sorted(
                stats,
                key=lambda name: (
                    -stats[name]["flights"],
                    name,
                ),
            )
        ):
            item = stats[aircraft]

            average_speed = (
                item["speed_total"]
                / item["speed_count"]
                if item["speed_count"]
                else None
            )

            set_table_item(
                self.table,
                row,
                0,
                aircraft,
            )
            set_table_item(
                self.table,
                row,
                1,
                f'{item["flights"]:,}',
            )
            set_table_item(
                self.table,
                row,
                2,
                format_hours(
                    item["minutes"]
                ),
            )
            set_table_item(
                self.table,
                row,
                3,
                f'{item["distance"]:,.1f} km',
            )
            set_table_item(
                self.table,
                row,
                4,
                (
                    "—"
                    if average_speed is None
                    else f"{average_speed:,.1f} km/h"
                ),
            )
            set_table_item(
                self.table,
                row,
                5,
                f'{item["jet"]:,.1f} kg',
            )
            set_table_item(
                self.table,
                row,
                6,
                f'{item["piston"]:,.1f} L',
            )

        self.table.setSortingEnabled(True)


# =========================================================
# AIRPORTS PAGE
# =========================================================


class AirportsPage(YearStatisticsPage):
    """Airport usage statistics for the selected year."""

    def __init__(self):
        super().__init__(
            "Airports",
            "Airport activity and route usage",
        )

        self.table = create_table(
            [
                "Airport",
                "Departures",
                "Arrivals",
                "Total",
                "Routes",
            ],
            "statsTable",
        )

        self.layout.addWidget(
            self.table,
            1,
        )

    def update_page(self):
        if self.data is None:
            return

        indices = self.get_filtered_indices()

        stats = {}

        for index in indices:
            flight = self.data.flights[index]
            departure = flight.departure
            arrival = flight.arrival

            if departure not in stats:
                stats[departure] = {
                    "departures": 0,
                    "arrivals": 0,
                    "routes": set(),
                }

            if arrival not in stats:
                stats[arrival] = {
                    "departures": 0,
                    "arrivals": 0,
                    "routes": set(),
                }

            stats[departure]["departures"] += 1
            stats[departure]["routes"].add(arrival)

            stats[arrival]["arrivals"] += 1
            stats[arrival]["routes"].add(departure)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(
            len(stats)
        )

        for row, airport in enumerate(
            sorted(
                stats,
                key=lambda code: (
                    -(
                        stats[code]["departures"]
                        + stats[code]["arrivals"]
                    ),
                    code,
                ),
            )
        ):
            item = stats[airport]

            departures = item["departures"]
            arrivals = item["arrivals"]
            total = departures + arrivals

            set_table_item(
                self.table,
                row,
                0,
                airport,
            )
            set_table_item(
                self.table,
                row,
                1,
                f"{departures:,}",
            )
            set_table_item(
                self.table,
                row,
                2,
                f"{arrivals:,}",
            )
            set_table_item(
                self.table,
                row,
                3,
                f"{total:,}",
            )
            set_table_item(
                self.table,
                row,
                4,
                f'{len(item["routes"]):,}',
            )

        self.table.setSortingEnabled(True)


# =========================================================
# FUEL PAGE
# =========================================================


class FuelPage(YearStatisticsPage):
    """Fuel statistics for the selected year."""

    def __init__(self):
        super().__init__(
            "Fuel",
            "Estimated fuel consumption",
        )

        cards = QGridLayout()
        cards.setSpacing(15)

        self.jet_card = MetricCard(
            "Jet fuel"
        )
        self.piston_card = MetricCard(
            "Piston fuel"
        )
        self.jet_average_card = MetricCard(
            "Jet fuel / flight"
        )
        self.piston_average_card = MetricCard(
            "Piston fuel / flight"
        )

        cards.addWidget(
            self.jet_card,
            0,
            0,
        )
        cards.addWidget(
            self.piston_card,
            0,
            1,
        )
        cards.addWidget(
            self.jet_average_card,
            0,
            2,
        )
        cards.addWidget(
            self.piston_average_card,
            0,
            3,
        )

        self.layout.addLayout(cards)

        section = QLabel(
            "Fuel by Aircraft"
        )
        section.setObjectName(
            "sectionTitle"
        )
        self.layout.addWidget(section)

        self.table = create_table(
            [
                "Aircraft",
                "Flights",
                "Jet Fuel",
                "Jet / Flight",
                "Piston Fuel",
                "Piston / Flight",
            ],
            "statsTable",
        )

        self.layout.addWidget(
            self.table,
            1,
        )

    def update_page(self):
        if self.data is None:
            return

        indices = self.get_filtered_indices()
        flights = len(indices)

        jet, piston = calculate_fuel_totals(
            self.data,
            indices,
        )

        self.jet_card.set_value(
            f"{jet:,.1f} kg"
        )
        self.piston_card.set_value(
            f"{piston:,.1f} L"
        )
        self.jet_average_card.set_value(
            (
                f"{jet / flights:,.1f} kg"
                if flights
                else "—"
            )
        )
        self.piston_average_card.set_value(
            (
                f"{piston / flights:,.1f} L"
                if flights
                else "—"
            )
        )

        stats = {}

        for index in indices:
            flight = self.data.flights[index]
            aircraft = self.database.normalize_type(
                flight.aircraft
            )

            if aircraft not in stats:
                stats[aircraft] = {
                    "flights": 0,
                    "jet": 0.0,
                    "piston": 0.0,
                }

            stats[aircraft]["flights"] += 1

            if index < len(
                self.data.fuel_results
            ):
                result = self.data.fuel_results[index]

                if isinstance(result, dict):
                    fuel = result.get("fuel")
                    unit = result.get("unit")

                    if fuel is not None:
                        if unit == "kg/h":
                            stats[aircraft]["jet"] += fuel
                        elif unit == "L/h":
                            stats[aircraft]["piston"] += fuel

        self.table.setSortingEnabled(False)
        self.table.setRowCount(
            len(stats)
        )

        for row, aircraft in enumerate(
            sorted(
                stats,
                key=lambda name: (
                    -stats[name]["flights"],
                    name,
                ),
            )
        ):
            item = stats[aircraft]
            count = item["flights"]

            set_table_item(
                self.table,
                row,
                0,
                aircraft,
            )
            set_table_item(
                self.table,
                row,
                1,
                f"{count:,}",
            )
            set_table_item(
                self.table,
                row,
                2,
                f'{item["jet"]:,.1f} kg',
            )
            set_table_item(
                self.table,
                row,
                3,
                (
                    f'{item["jet"] / count:,.1f} kg'
                    if count
                    else "—"
                ),
            )
            set_table_item(
                self.table,
                row,
                4,
                f'{item["piston"]:,.1f} L',
            )
            set_table_item(
                self.table,
                row,
                5,
                (
                    f'{item["piston"] / count:,.1f} L'
                    if count
                    else "—"
                ),
            )

        self.table.setSortingEnabled(True)


# =========================================================
# PERFORMANCE PAGE
# =========================================================


class PerformancePage(YearStatisticsPage):
    """Sector performance statistics for the selected year."""

    def __init__(self):
        super().__init__(
            "Performance",
            "Sector speed and flight-time analysis",
        )

        cards = QGridLayout()
        cards.setSpacing(15)

        self.average_speed_card = MetricCard(
            "Average sector speed"
        )
        self.fastest_card = MetricCard(
            "Fastest sector"
        )
        self.longest_card = MetricCard(
            "Longest sector"
        )
        self.average_time_card = MetricCard(
            "Average flight time"
        )

        cards.addWidget(
            self.average_speed_card,
            0,
            0,
        )
        cards.addWidget(
            self.fastest_card,
            0,
            1,
        )
        cards.addWidget(
            self.longest_card,
            0,
            2,
        )
        cards.addWidget(
            self.average_time_card,
            0,
            3,
        )

        self.layout.addLayout(cards)

        section = QLabel(
            "Performance by Aircraft"
        )
        section.setObjectName(
            "sectionTitle"
        )
        self.layout.addWidget(section)

        self.table = create_table(
            [
                "Aircraft",
                "Flights",
                "Flight Time",
                "Distance",
                "Avg. Speed",
                "Fastest Sector",
            ],
            "statsTable",
        )

        self.layout.addWidget(
            self.table,
            1,
        )

    def update_page(self):
        if self.data is None:
            return

        indices = self.get_filtered_indices()

        speeds = []
        longest_distance = 0.0
        fastest_speed = None

        total_minutes = 0
        valid_distance_count = 0

        stats = {}

        for index in indices:
            flight = self.data.flights[index]
            aircraft = self.database.normalize_type(
                flight.aircraft
            )

            total_minutes += (
                flight.flight_minutes or 0
            )

            if aircraft not in stats:
                stats[aircraft] = {
                    "flights": 0,
                    "minutes": 0,
                    "distance": 0.0,
                    "speed_total": 0.0,
                    "speed_count": 0,
                    "fastest": None,
                }

            item = stats[aircraft]
            item["flights"] += 1
            item["minutes"] += (
                flight.flight_minutes or 0
            )

            if index < len(
                self.data.flight_distances
            ):
                result = self.data.flight_distances[index]

                if isinstance(result, dict):
                    distance = result.get(
                        "distance_km"
                    )

                    if distance is not None:
                        item["distance"] += distance
                        longest_distance = max(
                            longest_distance,
                            distance,
                        )
                        valid_distance_count += 1

            speed = calculate_sector_speed(
                self.data,
                index,
            )

            if speed is not None:
                speeds.append(speed)
                item["speed_total"] += speed
                item["speed_count"] += 1

                if (
                    item["fastest"] is None
                    or speed > item["fastest"]
                ):
                    item["fastest"] = speed

                if (
                    fastest_speed is None
                    or speed > fastest_speed
                ):
                    fastest_speed = speed

        average_speed = (
            sum(speeds) / len(speeds)
            if speeds
            else None
        )

        average_time = (
            total_minutes / len(indices)
            if indices
            else None
        )

        self.average_speed_card.set_value(
            (
                f"{average_speed:,.1f} km/h"
                if average_speed is not None
                else "—"
            )
        )

        self.fastest_card.set_value(
            (
                f"{fastest_speed:,.1f} km/h"
                if fastest_speed is not None
                else "—"
            )
        )

        self.longest_card.set_value(
            (
                f"{longest_distance:,.1f} km"
                if valid_distance_count
                else "—"
            )
        )

        self.average_time_card.set_value(
            (
                format_hours(
                    average_time
                )
                if average_time is not None
                else "—"
            )
        )

        self.table.setSortingEnabled(False)
        self.table.setRowCount(
            len(stats)
        )

        for row, aircraft in enumerate(
            sorted(
                stats,
                key=lambda name: (
                    -stats[name]["flights"],
                    name,
                ),
            )
        ):
            item = stats[aircraft]

            average = (
                item["speed_total"]
                / item["speed_count"]
                if item["speed_count"]
                else None
            )

            set_table_item(
                self.table,
                row,
                0,
                aircraft,
            )
            set_table_item(
                self.table,
                row,
                1,
                f'{item["flights"]:,}',
            )
            set_table_item(
                self.table,
                row,
                2,
                format_hours(
                    item["minutes"]
                ),
            )
            set_table_item(
                self.table,
                row,
                3,
                f'{item["distance"]:,.1f} km',
            )
            set_table_item(
                self.table,
                row,
                4,
                (
                    "—"
                    if average is None
                    else f"{average:,.1f} km/h"
                ),
            )
            set_table_item(
                self.table,
                row,
                5,
                (
                    "—"
                    if item["fastest"] is None
                    else f'{item["fastest"]:,.1f} km/h'
                ),
            )

        self.table.setSortingEnabled(True)


# =========================================================
# MAIN
# =========================================================
# =========================================================
# MAIN
# =========================================================


def main():
    app = QApplication(
        sys.argv
    )

    apply_style(
        app
    )

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()