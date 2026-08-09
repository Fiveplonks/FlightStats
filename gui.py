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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
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
    """Main FlightStats dashboard."""

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
            "Flight time"
        )

        self.distance_card = MetricCard(
            "Distance"
        )

        self.jet_fuel_card = MetricCard(
            "Estimated jet fuel"
        )

        self.piston_fuel_card = MetricCard(
            "Estimated piston fuel"
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
            self.distance_card,
            0,
            2,
        )

        cards_layout.addWidget(
            self.jet_fuel_card,
            1,
            0,
        )

        cards_layout.addWidget(
            self.piston_fuel_card,
            1,
            1,
        )

        cards_layout.addWidget(
            self.airports_card,
            1,
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
        self.year_tabs.currentChanged.connect(
            self.year_tab_changed
        )

        self.layout.addWidget(
            self.year_tabs
        )

        # -------------------------------------------------
        # AIRCRAFT
        # -------------------------------------------------

        aircraft_title = QLabel(
            "Aircraft"
        )

        aircraft_title.setObjectName(
            "sectionTitle"
        )

        self.layout.addWidget(
            aircraft_title
        )

        self.aircraft_container = QFrame()

        self.aircraft_container.setObjectName(
            "card"
        )

        self.aircraft_layout = QVBoxLayout(
            self.aircraft_container
        )

        self.aircraft_layout.setContentsMargins(
            20,
            15,
            20,
            15,
        )

        self.aircraft_layout.setSpacing(
            8
        )

        self.layout.addWidget(
            self.aircraft_container
        )

        self.layout.addStretch()

    def set_data(self, data):
        """Load data and build Dashboard year tabs."""

        self._data = data
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

        if years:
            self.year_tabs.setCurrentIndex(0)
            self.update_for_year(years[0])
        else:
            self.year_tabs.setCurrentIndex(
                self.year_tabs.count() - 1
            )
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

        self.update_filtered_aircraft(
            flights
        )

    def update_filtered_aircraft(self, flights):
        """Update aircraft rows for the selected year."""

        self.clear_aircraft()

        database = FuelDatabase()
        aircraft_counts = {}
        aircraft_times = {}

        for flight in flights:
            aircraft = database.normalize_type(
                flight.aircraft
            )

            aircraft_counts[aircraft] = (
                aircraft_counts.get(aircraft, 0) + 1
            )
            aircraft_times[aircraft] = (
                aircraft_times.get(aircraft, 0)
                + (flight.flight_minutes or 0)
            )

        for aircraft in sorted(
            aircraft_counts,
            key=lambda item: (
                -aircraft_counts[item],
                item,
            ),
        ):
            row_widget = QWidget()
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 0, 0, 0)

            aircraft_label = QLabel(aircraft)
            aircraft_label.setObjectName(
                "aircraftName"
            )

            count_label = QLabel(
                f"{aircraft_counts[aircraft]} flights"
            )
            count_label.setObjectName(
                "aircraftCount"
            )

            time_label = QLabel(
                format_hours(
                    aircraft_times[aircraft]
                )
            )
            time_label.setObjectName(
                "aircraftTime"
            )

            row.addWidget(aircraft_label)
            row.addStretch()
            row.addWidget(count_label)
            row.addWidget(time_label)

            self.aircraft_layout.addWidget(
                row_widget
            )

    def clear_aircraft(self):
        """Remove aircraft rows."""

        while self.aircraft_layout.count() > 0:
            item = self.aircraft_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()


    def update_aircraft(
        self,
        data,
    ):
        """Update aircraft summary."""

        self.clear_aircraft()

        database = FuelDatabase()

        aircraft_counts = {}
        aircraft_times = {}

        for flight in data.flights:

            aircraft = (
                database.normalize_type(
                    flight.aircraft
                )
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

            aircraft_times[
                aircraft
            ] = (
                aircraft_times.get(
                    aircraft,
                    0,
                )
                + flight.flight_minutes
            )

        for aircraft in sorted(
            aircraft_counts,
            key=lambda item: (
                -aircraft_counts[item],
                item,
            ),
        ):

            row = QHBoxLayout()

            aircraft_label = QLabel(
                aircraft
            )

            aircraft_label.setObjectName(
                "aircraftName"
            )

            count_label = QLabel(
                f"{aircraft_counts[aircraft]} flights"
            )

            count_label.setObjectName(
                "aircraftCount"
            )

            time_label = QLabel(
                format_hours(
                    aircraft_times[
                        aircraft
                    ]
                )
            )

            time_label.setObjectName(
                "aircraftTime"
            )

            row.addWidget(
                aircraft_label
            )

            row.addStretch()

            row.addWidget(
                count_label
            )

            row.addWidget(
                time_label
            )

            self.aircraft_layout.addLayout(
                row
            )


# =========================================================
# LOGBOOK PAGE
# =========================================================


class LogbookPage(QWidget):
    """Searchable and sortable logbook."""

    def __init__(self):
        super().__init__()

        self.data = None
        self.selected_year = None

        self.database = FuelDatabase()

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            40,
            35,
            40,
            35,
        )

        layout.setSpacing(
            15
        )

        title = QLabel(
            "Logbook"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Browse and search your flight history"
        )

        subtitle.setObjectName(
            "pageSubtitle"
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        # -------------------------------------------------
        # YEAR TABS
        # -------------------------------------------------

        self.year_tabs = QTabWidget()

        self.year_tabs.setObjectName(
            "yearTabs"
        )

        self.year_tabs.currentChanged.connect(
            self.year_tab_changed
        )

        layout.addWidget(
            self.year_tabs
        )

        # -------------------------------------------------
        # FILTERS
        # -------------------------------------------------

        filter_bar = QHBoxLayout()

        self.search_box = QLineEdit()

        self.search_box.setPlaceholderText(
            "Search date, airport, aircraft, registration..."
        )

        self.search_box.setObjectName(
            "searchBox"
        )

        filter_bar.addWidget(
            self.search_box,
            1,
        )

        self.aircraft_filter = QComboBox()

        self.aircraft_filter.setObjectName(
            "filterBox"
        )

        self.aircraft_filter.addItem(
            "All aircraft"
        )

        filter_bar.addWidget(
            self.aircraft_filter
        )

        layout.addLayout(
            filter_bar
        )

        self.result_label = QLabel(
            "0 flights"
        )

        self.result_label.setObjectName(
            "statusLabel"
        )

        layout.addWidget(
            self.result_label
        )

        # -------------------------------------------------
        # TABLE
        # -------------------------------------------------

        self.table = QTableWidget()

        self.table.setObjectName(
            "logbookTable"
        )

        self.table.setColumnCount(
            10
        )

        self.table.setHorizontalHeaderLabels(
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
            ]
        )

        self.table.setSortingEnabled(
            True
        )

        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )

        self.table.setSelectionMode(
            QTableWidget.SingleSelection
        )

        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )

        self.table.verticalHeader().setVisible(
            False
        )

        header = (
            self.table.horizontalHeader()
        )

        header.setStretchLastSection(
            True
        )

        for column in range(9):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        layout.addWidget(
            self.table,
            1,
        )

        self.search_box.textChanged.connect(
            self.apply_filters
        )

        self.aircraft_filter.currentTextChanged.connect(
            self.apply_filters
        )

    def set_data(
        self,
        data,
    ):
        """Load data and build the Logbook year tabs."""

        self.data = data

        self.aircraft_filter.blockSignals(
            True
        )

        self.aircraft_filter.clear()

        self.aircraft_filter.addItem(
            "All aircraft"
        )

        aircraft_types = set()

        for flight in data.flights:
            aircraft_types.add(
                self.database.normalize_type(
                    flight.aircraft
                )
            )

        for aircraft in sorted(
            aircraft_types
        ):
            self.aircraft_filter.addItem(
                aircraft
            )

        self.aircraft_filter.blockSignals(
            False
        )

        self.build_year_tabs()

    def build_year_tabs(self):
        """Build one tab for each year in the logbook."""

        self.year_tabs.blockSignals(
            True
        )

        self.year_tabs.clear()

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

        self.selected_year = (
            years[0]
            if years
            else None
        )

        self.year_tabs.blockSignals(
            False
        )

        self.apply_filters()

    def year_tab_changed(
        self,
        index,
    ):
        """Filter the Logbook to the selected year."""

        if (
            self.data is None
            or index < 0
        ):
            return

        tab_text = self.year_tabs.tabText(
            index
        )

        self.selected_year = (
            None
            if tab_text == "ALL"
            else int(tab_text)
        )

        self.apply_filters()

    def apply_filters(self):
        """Apply search/filter criteria."""

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

        for index, flight in enumerate(
            self.data.flights
        ):

            if (
                self.selected_year is not None
                and flight.date.year
                != self.selected_year
            ):
                continue

            aircraft = (
                self.database.normalize_type(
                    flight.aircraft
                )
            )

            if (
                selected_aircraft
                != "All aircraft"
                and aircraft
                != selected_aircraft
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
                and search_text
                not in searchable
            ):
                continue

            matches.append(
                (
                    index,
                    flight,
                )
            )

        self.populate_table(
            matches
        )

        self.result_label.setText(
            f"{len(matches):,} flights"
        )

    def populate_table(
        self,
        matches,
    ):
        """Populate logbook table."""

        self.table.setSortingEnabled(
            False
        )

        self.table.setRowCount(
            len(matches)
        )

        for row, (
            original_index,
            flight,
        ) in enumerate(matches):

            distance = (
                self.data.flight_distances[
                    original_index
                ][
                    "distance_km"
                ]
            )

            fuel_result = (
                self.data.fuel_results[
                    original_index
                ]
            )

            fuel = fuel_result.get(
                "fuel"
            )

            fuel_unit = fuel_result.get(
                "unit"
            )

            self.set_item(
                row,
                0,
                flight.date.strftime(
                    "%d-%m-%Y"
                ),
            )

            self.set_item(
                row,
                1,
                flight.departure,
            )

            departure_time = (
                flight.departure_time
            )

            self.set_item(
                row,
                2,
                departure_time.strftime(
                    "%H:%M"
                )
                if departure_time
                else "—",
            )

            self.set_item(
                row,
                3,
                flight.arrival,
            )

            arrival_time = (
                flight.arrival_time
            )

            self.set_item(
                row,
                4,
                arrival_time.strftime(
                    "%H:%M"
                )
                if arrival_time
                else "—",
            )

            aircraft = (
                self.database.normalize_type(
                    flight.aircraft
                )
            )

            self.set_item(
                row,
                5,
                aircraft,
            )

            self.set_item(
                row,
                6,
                flight.registration,
            )

            self.set_item(
                row,
                7,
                format_hours(
                    flight.flight_minutes
                ),
            )

            distance_text = (
                "—"
                if distance is None
                else (
                    f"{distance:,.1f} km"
                )
            )

            self.set_item(
                row,
                8,
                distance_text,
            )

            fuel_text = (
                "—"
                if fuel is None
                else (
                    f"{fuel:,.1f} "
                    f"{display_fuel_unit(fuel_unit)}"
                )
            )

            self.set_item(
                row,
                9,
                fuel_text,
            )

        self.table.setSortingEnabled(
            True
        )

    def set_item(
        self,
        row,
        column,
        text,
    ):
        """Set table item."""

        item = QTableWidgetItem(
            str(text)
        )

        self.table.setItem(
            row,
            column,
            item
        )


# =========================================================
# PLACEHOLDER PAGE
# =========================================================


class PlaceholderPage(QWidget):
    """Temporary page."""

    def __init__(
        self,
        title,
    ):
        super().__init__()

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            40,
            40,
            40,
            40,
        )

        label = QLabel(
            title
        )

        label.setObjectName(
            "pageTitle"
        )

        layout.addWidget(
            label
        )

        layout.addStretch()


# =========================================================
# MAIN WINDOW
# =========================================================


class MainWindow(QMainWindow):
    """Main FlightStats application."""

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "FlightStats"
        )

        self.resize(
            1300,
            850,
        )

        self.data = None

        self.loader_thread = None
        self.loader_worker = None

        # -------------------------------------------------
        # CENTRAL WIDGET
        # -------------------------------------------------

        central = QWidget()

        self.setCentralWidget(
            central
        )

        main_layout = QHBoxLayout(
            central
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        main_layout.setSpacing(
            0
        )

        # -------------------------------------------------
        # SIDEBAR
        # -------------------------------------------------

        sidebar = QFrame()

        sidebar.setObjectName(
            "sidebar"
        )

        sidebar.setFixedWidth(
            220
        )

        sidebar_layout = QVBoxLayout(
            sidebar
        )

        sidebar_layout.setContentsMargins(
            15,
            25,
            15,
            25,
        )

        sidebar_layout.setSpacing(
            8
        )

        logo = QLabel(
            "✈  FlightStats"
        )

        logo.setObjectName(
            "logo"
        )

        sidebar_layout.addWidget(
            logo
        )

        sidebar_layout.addSpacing(
            25
        )

        # -------------------------------------------------
        # PAGES
        # -------------------------------------------------

        self.pages = QStackedWidget()

        self.dashboard_page = (
            DashboardPage()
        )

        self.logbook_page = (
            LogbookPage()
        )

        self.aircraft_page = (
            PlaceholderPage(
                "Aircraft"
            )
        )

        self.airports_page = (
            PlaceholderPage(
                "Airports"
            )
        )

        self.fuel_page = (
            PlaceholderPage(
                "Fuel"
            )
        )

        self.performance_page = (
            PlaceholderPage(
                "Performance"
            )
        )

        self.pages.addWidget(
            self.dashboard_page
        )

        self.pages.addWidget(
            self.logbook_page
        )

        self.pages.addWidget(
            self.aircraft_page
        )

        self.pages.addWidget(
            self.airports_page
        )

        self.pages.addWidget(
            self.fuel_page
        )

        self.pages.addWidget(
            self.performance_page
        )

        buttons = [
            ("Dashboard", 0),
            ("Logbook", 1),
            ("Aircraft", 2),
            ("Airports", 3),
            ("Fuel", 4),
            ("Performance", 5),
        ]

        for text, index in buttons:

            button = QPushButton(
                text
            )

            button.setObjectName(
                "navigationButton"
            )

            button.setCursor(
                Qt.PointingHandCursor
            )

            button.clicked.connect(
                lambda checked=False,
                i=index: (
                    self.pages.setCurrentIndex(
                        i
                    )
                )
            )

            sidebar_layout.addWidget(
                button
            )

        sidebar_layout.addStretch()

        version = QLabel(
            "FlightStats\n"
            "Development Version"
        )

        version.setObjectName(
            "versionLabel"
        )

        sidebar_layout.addWidget(
            version
        )

        # -------------------------------------------------
        # CONTENT
        # -------------------------------------------------

        content = QFrame()

        content.setObjectName(
            "content"
        )

        content_layout = QVBoxLayout(
            content
        )

        content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        content_layout.addWidget(
            self.pages
        )

        main_layout.addWidget(
            sidebar
        )

        main_layout.addWidget(
            content
        )

        # -------------------------------------------------
        # SIGNALS
        # -------------------------------------------------

        self.dashboard_page.refresh_button.clicked.connect(
            self.load_data
        )

        # -------------------------------------------------
        # INITIAL LOAD
        # -------------------------------------------------

        self.load_data()

    # =====================================================
    # DATA LOADING
    # =====================================================

    def load_data(self):
        """
        Start asynchronous FlightStats data loading.
        """

        if (
            self.loader_thread is not None
            and self.loader_thread.isRunning()
        ):
            return

        self.dashboard_page.refresh_button.setEnabled(
            False
        )

        self.dashboard_page.progress_bar.setValue(
            0
        )

        self.dashboard_page.status_label.setText(
            "Starting..."
        )

        # -------------------------------------------------
        # CREATE THREAD
        # -------------------------------------------------

        self.loader_thread = QThread()

        self.loader_worker = (
            DataLoaderWorker(
                LOGBOOK
            )
        )

        self.loader_worker.moveToThread(
            self.loader_thread
        )

        # -------------------------------------------------
        # SIGNALS
        # -------------------------------------------------

        self.loader_thread.started.connect(
            self.loader_worker.run
        )

        self.loader_worker.progress.connect(
            self.update_loading_progress
        )

        self.loader_worker.finished.connect(
            self.data_loaded
        )

        self.loader_worker.error.connect(
            self.loading_error
        )

        self.loader_worker.finished.connect(
            self.loader_thread.quit
        )

        self.loader_worker.error.connect(
            self.loader_thread.quit
        )

        self.loader_thread.finished.connect(
            self.loading_finished
        )

        # -------------------------------------------------
        # START
        # -------------------------------------------------

        self.loader_thread.start()

    def update_loading_progress(
        self,
        percent,
        message,
    ):
        """Update GUI progress."""

        self.dashboard_page.progress_bar.setValue(
            percent
        )

        self.dashboard_page.status_label.setText(
            message
        )

    def data_loaded(
        self,
        data,
    ):
        """Receive completed data from worker."""

        self.data = data

        self.dashboard_page.set_data(
            self.data
        )

        self.logbook_page.set_data(
            self.data
        )

    def loading_error(
        self,
        message,
    ):
        """Display loading error."""

        self.dashboard_page.progress_bar.setValue(
            0
        )

        self.dashboard_page.status_label.setText(
            f"Error loading logbook: {message}"
        )

        print(
            "\nFlightStats error:"
        )

        print(message)

    def loading_finished(self):
        """Clean up worker/thread."""

        self.dashboard_page.refresh_button.setEnabled(
            True
        )

        if self.loader_worker is not None:
            self.loader_worker.deleteLater()

        if self.loader_thread is not None:
            self.loader_thread.deleteLater()

        self.loader_worker = None
        self.loader_thread = None

    # =====================================================
    # DASHBOARD
    # =====================================================

    def update_dashboard(self):
        """Update Dashboard using the selected year tab."""

        if self.data is None:
            return

        index = self.dashboard_page.year_tabs.currentIndex()

        if index < 0:
            return

        text = self.dashboard_page.year_tabs.tabText(index)

        year = (
            None
            if text == "ALL"
            else int(text)
        )

        self.dashboard_page.update_for_year(
            year
        )


# =========================================================
# STYLE
# =========================================================


def apply_style(app):
    """Apply FlightStats visual style."""

    app.setStyleSheet(
        """
        QMainWindow {
            background: #f4f6f8;
        }

        QWidget {
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;

            color: #1f2937;
        }

        #sidebar {
            background: #111827;
        }

        #logo {
            color: white;
            font-size: 22px;
            font-weight: 700;
            padding-left: 10px;
        }

        #navigationButton {
            background: transparent;
            color: #d1d5db;
            border: none;
            border-radius: 8px;
            padding: 12px 15px;
            text-align: left;
            font-size: 14px;
        }

        #navigationButton:hover {
            background: #1f2937;
            color: white;
        }

        #navigationButton:pressed {
            background: #374151;
        }

        #content {
            background: #f4f6f8;
        }

        #pageTitle {
            font-size: 30px;
            font-weight: 700;
            color: #111827;
        }

        #pageSubtitle {
            font-size: 15px;
            color: #6b7280;
        }

        #sectionTitle {
            font-size: 20px;
            font-weight: 700;
            color: #111827;
        }

        #card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
        }

        #cardLabel {
            color: #6b7280;
            font-size: 13px;
        }

        #cardValue {
            color: #111827;
            font-size: 26px;
            font-weight: 700;
        }

        #refreshButton {
            background: #111827;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
        }

        #refreshButton:hover {
            background: #1f2937;
        }

        #refreshButton:pressed {
            background: #374151;
        }

        #refreshButton:disabled {
            background: #9ca3af;
        }

        #statusLabel {
            color: #6b7280;
            font-size: 12px;
        }

        #progressBar {
            height: 8px;
            border: none;
            border-radius: 4px;
            background: #e5e7eb;
        }

        #progressBar::chunk {
            border-radius: 4px;
            background: #111827;
        }

        #loadingFrame {
            background: transparent;
        }

        #aircraftName {
            font-size: 14px;
            font-weight: 600;
        }

        #aircraftCount {
            color: #6b7280;
            font-size: 13px;
        }

        #aircraftTime {
            color: #374151;
            font-size: 13px;
            font-weight: 600;
            min-width: 70px;
        }

        #searchBox {
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 10px 12px;
            font-size: 13px;
        }

        #searchBox:focus {
            border: 1px solid #6b7280;
        }

        #filterBox {
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 8px 12px;
            min-width: 150px;
        }

        #logbookTable {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            gridline-color: #eef0f2;
            selection-background-color: #e5e7eb;
            selection-color: #111827;
        }

        #logbookTable QHeaderView::section {
            background: #f9fafb;
            color: #4b5563;
            border: none;
            border-bottom: 1px solid #e5e7eb;
            padding: 10px 8px;
            font-size: 12px;
            font-weight: 600;
        }

        #logbookTable QTableWidgetItem {
            padding: 8px;
        }

        #yearTabs::pane {
            border: none;
            background: transparent;
        }

        #yearTabs QTabBar::tab {
            background: transparent;
            color: #6b7280;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 9px 18px;
            margin-right: 4px;
        }

        #yearTabs QTabBar::tab:selected {
            color: #111827;
            font-weight: 700;
            border-bottom: 2px solid #111827;
        }

        #versionLabel {
            color: #6b7280;
            font-size: 11px;
            padding-left: 10px;
        }
        """
    )


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