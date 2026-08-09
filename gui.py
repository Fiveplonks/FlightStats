import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

from PySide6.QtCore import (
    QObject,
    Qt,
    QThread,
    Signal,
    QEvent,
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
    QFileDialog,
    QPushButton,
    QProgressBar,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
)

from app_paths import (
    SETTINGS_FILE,
    get_logbook_path,
)
from data_manager import FlightStatsData
from parser.airports import AirportDatabase
from parser.fuel import FuelDatabase


def load_saved_logbook():
    """Return the user's saved logbook path when it still exists."""
    try:
        if not SETTINGS_FILE.exists():
            return None

        with SETTINGS_FILE.open(
            "r",
            encoding="utf-8",
        ) as handle:
            settings = json.load(handle)

        if not isinstance(settings, dict):
            return None

        value = settings.get(
            "logbook_path"
        )

        if not value:
            return None

        path = Path(
            str(value)
        ).expanduser()

        if (
            path.exists()
            and path.is_file()
            and path.suffix.lower() == ".pdf"
        ):
            return path

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):
        pass

    return None


def save_logbook_path(path):
    """Persist the selected logbook path."""
    SETTINGS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings = {}

    try:
        if SETTINGS_FILE.exists():
            with SETTINGS_FILE.open(
                "r",
                encoding="utf-8",
            ) as handle:
                settings = json.load(handle)

            if not isinstance(settings, dict):
                settings = {}

    except (
        OSError,
        json.JSONDecodeError,
    ):
        settings = {}

    settings["logbook_path"] = str(
        Path(path).expanduser().resolve()
    )

    with SETTINGS_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            settings,
            handle,
            indent=2,
        )


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
# LOGBOOK DROP ZONE
# =========================================================


class LogbookDropZone(QFrame):
    """Dashboard drop zone for selecting a logbook PDF."""

    logbook_selected = Signal(str)

    def __init__(self):
        super().__init__()

        self.setObjectName(
            "logbookDropZone"
        )

        self.setAcceptDrops(
            True
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            30,
            30,
            30,
            30,
        )

        layout.setSpacing(
            10
        )

        self.icon_label = QLabel(
            "✈"
        )

        self.icon_label.setObjectName(
            "logbookDropIcon"
        )

        self.icon_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.icon_label
        )

        self.title_label = QLabel(
            "Drop your logbook PDF here"
        )

        self.title_label.setObjectName(
            "logbookDropTitle"
        )

        self.title_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.title_label
        )

        self.subtitle_label = QLabel(
            "or click to browse for a PDF"
        )

        self.subtitle_label.setObjectName(
            "logbookDropSubtitle"
        )

        self.subtitle_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.subtitle_label
        )

        self.browse_button = QPushButton(
            "Choose Logbook PDF"
        )

        self.browse_button.setObjectName(
            "logbookBrowseButton"
        )

        self.browse_button.setCursor(
            Qt.PointingHandCursor
        )

        self.browse_button.clicked.connect(
            self.browse_for_logbook
        )

        layout.addWidget(
            self.browse_button,
            0,
            Qt.AlignCenter,
        )

    def browse_for_logbook(self):
        """Open the PDF file picker."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Flight Logbook",
            "",
            "PDF files (*.pdf)",
        )

        if path:
            self._select_path(
                path
            )

    def _select_path(self, path):
        """Validate and emit a selected PDF path."""
        path = Path(path)

        if (
            not path.exists()
            or not path.is_file()
            or path.suffix.lower() != ".pdf"
        ):
            QMessageBox.warning(
                self,
                "Invalid Logbook",
                "Please select a valid PDF logbook.",
            )
            return

        self.logbook_selected.emit(
            str(path.resolve())
        )

    def mousePressEvent(self, event):
        """Allow clicking anywhere in the drop zone."""
        if event.button() == Qt.LeftButton:
            self.browse_for_logbook()
            return

        super().mousePressEvent(
            event
        )

    def dragEnterEvent(self, event):
        """Accept dragged PDF files."""
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        urls = event.mimeData().urls()

        if any(
            url.isLocalFile()
            and Path(
                url.toLocalFile()
            ).suffix.lower() == ".pdf"
            for url in urls
        ):
            event.acceptProposedAction()
            self.setProperty(
                "dragActive",
                True,
            )
            self.style().unpolish(self)
            self.style().polish(self)
            return

        event.ignore()

    def dragLeaveEvent(self, event):
        """Restore the normal drop-zone appearance."""
        self.setProperty(
            "dragActive",
            False,
        )

        self.style().unpolish(self)
        self.style().polish(self)

        event.accept()

    def dropEvent(self, event):
        """Handle a dropped PDF logbook."""
        self.setProperty(
            "dragActive",
            False,
        )

        self.style().unpolish(self)
        self.style().polish(self)

        urls = event.mimeData().urls()

        for url in urls:
            if not url.isLocalFile():
                continue

            path = Path(
                url.toLocalFile()
            )

            if path.suffix.lower() == ".pdf":
                self._select_path(
                    str(path)
                )
                event.acceptProposedAction()
                return

        event.ignore()


# =========================================================
# DASHBOARD
# =========================================================


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
            "Refresh"
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

        self.show_logbook_selector()

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
            self.distance_card,
            self.jet_fuel_card,
            self.piston_fuel_card,
            self.airports_card,
            self.year_tabs,
            self.aircraft_container,
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
            self.distance_card,
            self.jet_fuel_card,
            self.piston_fuel_card,
            self.airports_card,
            self.year_tabs,
            self.aircraft_container,
        ):
            widget.hide()

    def show_statistics(self, logbook_path):
        """Show loaded statistics and the current logbook path."""
        self.logbook_drop_zone.hide()
        self.logbook_status_label.show()
        self.logbook_status_label.setText(
            f"Current logbook: {Path(logbook_path).name}"
        )

        self.loading_frame.show()

        for widget in (
            self.flights_card,
            self.time_card,
            self.distance_card,
            self.jet_fuel_card,
            self.piston_fuel_card,
            self.airports_card,
            self.year_tabs,
            self.aircraft_container,
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

        self.selected_year = None

        self.year_tabs.blockSignals(
            False
        )

        # Explicitly populate the initial ALL-years selection.
        self.year_tabs.setCurrentIndex(0)
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




class SortableTableWidgetItem(QTableWidgetItem):
    """Table item that sorts using a hidden numeric value when supplied."""

    def __init__(
        self,
        text,
        sort_value=None,
    ):
        super().__init__(
            str(text)
        )

        self.sort_value = sort_value

    def __lt__(
        self,
        other,
    ):
        if isinstance(
            other,
            SortableTableWidgetItem,
        ):
            if (
                self.sort_value is not None
                and other.sort_value is not None
            ):
                return (
                    self.sort_value
                    < other.sort_value
                )

        # Do not call QTableWidgetItem.__lt__ here.
        # PySide6 can route that call back through this Python
        # override, causing infinite recursion.
        return str(
            self.text()
        ).casefold() < str(
            other.text()
        ).casefold()


# =========================================================
# AIRCRAFT PAGE
# =========================================================


class AircraftPage(QWidget):
    """Aircraft statistics for the selected year."""

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
            "Aircraft"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Aircraft utilization and performance"
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

        layout.addWidget(
            self.year_tabs
        )

        # -------------------------------------------------
        # TABLE
        # -------------------------------------------------

        self.table = QTableWidget()

        self.table.setObjectName(
            "aircraftTable"
        )

        self.table.setColumnCount(
            8
        )

        self.table.setHorizontalHeaderLabels(
            [
                "Aircraft",
                "Flights",
                "Share",
                "Flight Time",
                "Distance",
                "Avg. Speed",
                "Registrations",
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

        for column in range(
            self.table.columnCount()
        ):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        layout.addWidget(
            self.table,
            1,
        )

    def set_data(
        self,
        data,
    ):
        """Load shared FlightStats data."""

        self.data = data

        self.build_year_tabs()

    def build_year_tabs(self):
        """Build one tab for every year in the logbook."""

        self.year_tabs.blockSignals(
            True
        )

        self.year_tabs.clear()

        if self.data is None:
            self.year_tabs.blockSignals(
                False
            )
            return

        years = sorted(
            {
                flight.date.year
                for flight in self.data.flights
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

        self.selected_year = None

        self.year_tabs.blockSignals(
            False
        )

        # currentChanged is blocked while building,
        # so explicitly populate the initial ALL-years selection.
        self.year_tabs.setCurrentIndex(0)
        self.update_page()

    def year_tab_changed(
        self,
        index,
    ):
        """Update aircraft statistics for the selected year."""

        if (
            self.data is None
            or index < 0
        ):
            return

        text = self.year_tabs.tabText(
            index
        )

        self.selected_year = (
            None
            if text == "ALL"
            else int(text)
        )

        self.update_page()

    def update_page(self):
        """Calculate and display aircraft statistics."""

        if self.data is None:
            return

        selected_indexes = []

        for index, flight in enumerate(
            self.data.flights
        ):
            if (
                self.selected_year is None
                or flight.date.year
                == self.selected_year
            ):
                selected_indexes.append(
                    index
                )

        total_flights = len(
            selected_indexes
        )

        stats = {}

        for index in selected_indexes:
            flight = self.data.flights[index]

            aircraft = (
                self.database.normalize_type(
                    flight.aircraft
                )
            )

            if aircraft not in stats:
                stats[aircraft] = {
                    "flights": 0,
                    "minutes": 0,
                    "distance": 0.0,
                    "speed_total": 0.0,
                    "speed_count": 0,
                    "registrations": set(),
                    "fuel": 0.0,
                    "fuel_unit": None,
                }

            item = stats[aircraft]

            item["flights"] += 1

            item["minutes"] += (
                flight.flight_minutes or 0
            )

            if flight.registration:
                item["registrations"].add(
                    flight.registration
                )

            # ---------------------------------------------
            # DISTANCE / SPEED
            # ---------------------------------------------

            if index < len(
                self.data.flight_distances
            ):
                distance_result = (
                    self.data.flight_distances[
                        index
                    ]
                )

                if isinstance(
                    distance_result,
                    dict,
                ):
                    distance = (
                        distance_result.get(
                            "distance_km"
                        )
                    )

                    if distance is not None:
                        item["distance"] += (
                            distance
                        )

                        if flight.flight_minutes:
                            speed = (
                                distance
                                / flight.flight_minutes
                                * 60
                            )

                            item[
                                "speed_total"
                            ] += speed

                            item[
                                "speed_count"
                            ] += 1

            # ---------------------------------------------
            # FUEL
            # ---------------------------------------------

            if index < len(
                self.data.fuel_results
            ):
                fuel_result = (
                    self.data.fuel_results[
                        index
                    ]
                )

                if isinstance(
                    fuel_result,
                    dict,
                ):
                    fuel = fuel_result.get(
                        "fuel"
                    )

                    unit = fuel_result.get(
                        "unit"
                    )

                    if fuel is not None:
                        item["fuel"] += fuel

                        if (
                            item["fuel_unit"]
                            is None
                        ):
                            item[
                                "fuel_unit"
                            ] = (
                                display_fuel_unit(
                                    unit
                                )
                                if unit
                                else None
                            )

        self.table.setSortingEnabled(
            False
        )

        self.table.setRowCount(
            len(stats)
        )

        sorted_aircraft = sorted(
            stats,
            key=lambda aircraft: aircraft.upper(),
        )

        for row, aircraft in enumerate(
            sorted_aircraft
        ):
            item = stats[aircraft]

            flights = item[
                "flights"
            ]

            share = (
                flights
                / total_flights
                * 100
                if total_flights
                else 0
            )

            average_speed = (
                item["speed_total"]
                / item["speed_count"]
                if item["speed_count"]
                else None
            )

            fuel_text = "—"

            if item["fuel_unit"]:
                fuel_text = (
                    f'{item["fuel"]:,.1f} '
                    f'{item["fuel_unit"]}'
                )

            values = [
                (
                    aircraft,
                    aircraft,
                ),
                (
                    f"{flights:,}",
                    flights,
                ),
                (
                    f"{share:.1f}%",
                    share,
                ),
                (
                    format_hours(
                        item["minutes"]
                    ),
                    item["minutes"],
                ),
                (
                    f'{item["distance"]:,.1f} km',
                    item["distance"],
                ),
                (
                    "—"
                    if average_speed is None
                    else (
                        f"{average_speed:,.1f} "
                        "km/h"
                    ),
                    average_speed,
                ),
                (
                    f'{len(item["registrations"]):,}',
                    len(item["registrations"]),
                ),
                (
                    fuel_text,
                    item["fuel"],
                ),
            ]

            for column, (
                value,
                sort_value,
            ) in enumerate(values):
                self.set_item(
                    row,
                    column,
                    value,
                    sort_value,
                )

        self.table.setSortingEnabled(
            True
        )

    def set_item(
        self,
        row,
        column,
        text,
        sort_value=None,
    ):
        """Set one table cell with optional numeric sorting."""

        item = SortableTableWidgetItem(
            text,
            sort_value,
        )

        self.table.setItem(
            row,
            column,
            item,
        )


# =========================================================
# AIRPORTS PAGE
# =========================================================


# =========================================================
# USER SETTINGS
# =========================================================

def load_home_bases():
    """Load saved home bases from the local settings file."""

    try:
        if not SETTINGS_FILE.exists():
            return []

        with SETTINGS_FILE.open(
            "r",
            encoding="utf-8",
        ) as handle:
            settings = json.load(handle)

        home_bases = settings.get(
            "home_bases",
            [],
        )

        if not isinstance(home_bases, list):
            return []

        return sorted(
            {
                str(code).strip().upper()
                for code in home_bases
                if str(code).strip()
            }
        )

    except (
        OSError,
        json.JSONDecodeError,
        TypeError,
    ):
        return []


def save_home_bases(home_bases):
    """Persist the user's home bases."""

    SETTINGS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    settings = {}

    try:
        if SETTINGS_FILE.exists():
            with SETTINGS_FILE.open(
                "r",
                encoding="utf-8",
            ) as handle:
                settings = json.load(handle)

            if not isinstance(settings, dict):
                settings = {}

    except (
        OSError,
        json.JSONDecodeError,
    ):
        settings = {}

    settings["home_bases"] = sorted(
        {
            str(code).strip().upper()
            for code in home_bases
            if str(code).strip()
        }
    )

    with SETTINGS_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            settings,
            handle,
            indent=2,
        )


class AirportsPage(QWidget):
    """Airport statistics for the selected year."""

    def __init__(self):
        super().__init__()

        self.data = None
        self.selected_year = None
        self.database = AirportDatabase()

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
            "Airports"
        )

        title.setObjectName(
            "pageTitle"
        )

        subtitle = QLabel(
            "Airport visits, turnaround times and layovers"
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
        # HOME BASES
        # -------------------------------------------------

        home_base_layout = QHBoxLayout()

        home_base_label = QLabel(
            "Home Bases:"
        )

        home_base_label.setStyleSheet(
            "font-weight: 600;"
            " color: #374151;"
        )

        home_base_layout.addWidget(
            home_base_label
        )

        self.home_base_input = QLineEdit()

        self.home_base_input.setPlaceholderText(
            "ICAO code"
        )

        self.home_base_input.setMaximumWidth(
            120
        )

        self.home_base_input.setMaxLength(
            4
        )

        self.home_base_input.returnPressed.connect(
            self.add_home_base
        )

        home_base_layout.addWidget(
            self.home_base_input
        )

        add_home_base_button = QPushButton(
            "Add"
        )

        add_home_base_button.clicked.connect(
            self.add_home_base
        )

        home_base_layout.addWidget(
            add_home_base_button
        )

        self.home_base_list = QListWidget()

        self.home_base_list.setObjectName(
            "homeBaseList"
        )

        self.home_base_list.setFlow(
            QListWidget.LeftToRight
        )

        self.home_base_list.setWrapping(
            False
        )

        self.home_base_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.home_base_list.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.home_base_list.setFixedHeight(
            42
        )

        home_base_layout.addWidget(
            self.home_base_list,
            1,
        )

        layout.addLayout(
            home_base_layout
        )

        self.home_bases = set(
            load_home_bases()
        )

        self.refresh_home_base_list()

        self.home_base_list.installEventFilter(
            self
        )

        # -------------------------------------------------
        # YEAR TABS
        # -------------------------------------------------

        self.year_tabs = QTabWidget()

        self.year_tabs.setObjectName(
            "yearTabs"
        )

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

        layout.addWidget(
            self.year_tabs
        )

        # -------------------------------------------------
        # TABLE
        # -------------------------------------------------

        self.table = QTableWidget()

        self.table.setObjectName(
            "airportsTable"
        )

        self.table.setColumnCount(
            6
        )

        self.table.setHorizontalHeaderLabels(
            [
                "Airport",
                "Country",
                "Flights",
                "Share",
                "Avg. Turnaround Time",
                "Avg. Layover Time",
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

        for column in range(
            self.table.columnCount()
        ):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        layout.addWidget(
            self.table,
            1,
        )

    def refresh_home_base_list(self):
        """Refresh the visible list of configured home bases."""

        self.home_base_list.clear()

        for airport in sorted(self.home_bases):
            item = QListWidgetItem(airport)

            item.setToolTip(
                "Double-click to remove this home base"
            )

            self.home_base_list.addItem(item)

    def add_home_base(self):
        """Add a validated airport as a home base."""

        airport = (
            self.home_base_input.text()
            .strip()
            .upper()
        )

        if not airport:
            return

        record = self.database.find(airport)

        if record is None:
            QMessageBox.warning(
                self,
                "Unknown airport",
                (
                    f"{airport} was not found "
                    "in the airport database."
                ),
            )
            return

        self.home_bases.add(airport)

        save_home_bases(self.home_bases)

        self.home_base_input.clear()

        self.refresh_home_base_list()

        self.update_page()

    def remove_home_base(self, item):
        """Remove a home base and recalculate the page."""

        airport = item.text()

        if airport not in self.home_bases:
            return

        self.home_bases.remove(airport)

        save_home_bases(self.home_bases)

        self.refresh_home_base_list()

        self.update_page()

    def eventFilter(self, watched, event):
        """Support double-click removal of home-base entries."""

        if (
            watched is self.home_base_list
            and event.type() == QEvent.MouseButtonDblClick
        ):
            item = self.home_base_list.itemAt(
                event.position().toPoint()
            )

            if item is not None:
                self.remove_home_base(item)
                return True

        return super().eventFilter(
            watched,
            event,
        )

    def set_data(
        self,
        data,
    ):
        """Load shared FlightStats data."""

        self.data = data

        self.build_year_tabs()

    def build_year_tabs(self):
        """Build year tabs from the loaded flight data."""

        self.year_tabs.blockSignals(
            True
        )

        self.year_tabs.clear()

        if self.data is None:
            self.year_tabs.blockSignals(
                False
            )
            return

        years = sorted(
            {
                flight.date.year
                for flight in self.data.flights
            },
            reverse=True,
        )

        # ALL first, then individual years.
        self.year_tabs.addTab(
            QWidget(),
            "ALL",
        )

        for year in years:
            self.year_tabs.addTab(
                QWidget(),
                str(year),
            )

        self.selected_year = None

        self.year_tabs.blockSignals(
            False
        )

        # ALL is the default selection.
        self.year_tabs.setCurrentIndex(
            0
        )

        self.update_page()

    def year_tab_changed(
        self,
        index,
    ):
        """Update airport statistics for the selected year."""

        if (
            self.data is None
            or index < 0
        ):
            return

        text = self.year_tabs.tabText(
            index
        )

        self.selected_year = (
            None
            if text == "ALL"
            else int(text)
        )

        self.update_page()

    def update_page(
        self,
    ):
        """Calculate and display airport statistics."""

        if self.data is None:
            return

        stats = {}

        selected_indexes = []

        for index, flight in enumerate(
            self.data.flights
        ):
            if (
                self.selected_year is not None
                and flight.date.year
                != self.selected_year
            ):
                continue

            selected_indexes.append(
                index
            )

        total_flights = len(
            selected_indexes
        )

        # -------------------------------------------------
        # AIRPORT VISITS
        # -------------------------------------------------

        for index in selected_indexes:
            flight = self.data.flights[
                index
            ]

            for airport_code in (
                flight.departure,
                flight.arrival,
            ):
                if airport_code not in stats:
                    stats[airport_code] = {
                        "flights": 0,
                        "turnarounds": [],
                        "layovers": [],
                    }

                item = stats[
                    airport_code
                ]

                item["flights"] += 1

        # -------------------------------------------------
        # TURNAROUND TIMES
        # -------------------------------------------------

        turnaround_data = (
            self.calculate_turnarounds(
                selected_indexes
            )
        )

        for airport, values in (
            turnaround_data.items()
        ):
            if airport not in stats:
                continue

            stats[airport][
                "turnarounds"
            ] = values["turnarounds"]

            stats[airport][
                "layovers"
            ] = values["layovers"]

        self.table.setSortingEnabled(
            False
        )

        self.table.setRowCount(
            len(stats)
        )

        sorted_airports = sorted(
            stats,
            key=lambda airport: airport.upper(),
        )

        for row, airport in enumerate(
            sorted_airports
        ):
            item = stats[
                airport
            ]

            flights = item[
                "flights"
            ]

            share = (
                flights
                / total_flights
                * 100
                if total_flights
                else 0
            )

            country = self.get_country(
                airport
            )

            turnaround_values = item[
                "turnarounds"
            ]

            layover_values = item[
                "layovers"
            ]

            if turnaround_values:
                average_turnaround = (
                    sum(turnaround_values)
                    / len(turnaround_values)
                )

                turnaround_text = (
                    format_hours(
                        int(
                            round(
                                average_turnaround
                            )
                        )
                    )
                )

                turnaround_sort_value = (
                    average_turnaround
                )
            else:
                turnaround_text = "—"
                turnaround_sort_value = None

            if layover_values:
                average_layover = (
                    sum(layover_values)
                    / len(layover_values)
                )

                layover_text = (
                    format_hours(
                        int(
                            round(
                                average_layover
                            )
                        )
                    )
                )

                layover_sort_value = (
                    average_layover
                )
            else:
                layover_text = "—"
                layover_sort_value = None

            values = [
                (
                    airport,
                    airport.upper(),
                ),
                (
                    country,
                    country.upper(),
                ),
                (
                    f"{flights:,}",
                    flights,
                ),
                (
                    f"{share:.1f}%",
                    share,
                ),
                (
                    turnaround_text,
                    turnaround_sort_value,
                ),
                (
                    layover_text,
                    layover_sort_value,
                ),
            ]

            for column, (
                value,
                sort_value,
            ) in enumerate(
                values
            ):
                self.set_item(
                    row,
                    column,
                    value,
                    sort_value,
                )

        self.table.setSortingEnabled(
            True
        )

    def calculate_turnarounds(
        self,
        selected_indexes,
    ):
        """
        Calculate airport turnaround and layover times.

        The next flight is paired only when it departs from the same
        airport where the previous flight arrived.

        < 10 hours:
            classified as a turnaround.

        >= 10 hours:
            classified as a layover.

        Flights without both arrival and departure times are ignored.
        """

        results = {}

        chronological = []

        for index in selected_indexes:
            flight = self.data.flights[
                index
            ]

            if (
                flight.departure_time is None
                or flight.arrival_time is None
            ):
                continue

            departure_datetime = (
                datetime.combine(
                    flight.date,
                    flight.departure_time,
                )
            )

            arrival_datetime = (
                datetime.combine(
                    flight.date,
                    flight.arrival_time,
                )
            )

            # Handle a sector crossing midnight.
            if arrival_datetime < departure_datetime:
                arrival_datetime += timedelta(
                    days=1
                )

            chronological.append(
                (
                    index,
                    flight,
                    departure_datetime,
                    arrival_datetime,
                )
            )

        chronological.sort(
            key=lambda item: item[2]
        )

        for position in range(
            len(chronological) - 1
        ):
            (
                index,
                flight,
                departure_datetime,
                arrival_datetime,
            ) = chronological[position]

            (
                next_index,
                next_flight,
                next_departure_datetime,
                next_arrival_datetime,
            ) = chronological[
                position + 1
            ]

            # The following flight must depart from the
            # airport where this flight arrived.
            if (
                flight.arrival
                != next_flight.departure
            ):
                continue

            if (
                next_departure_datetime
                <= arrival_datetime
            ):
                continue

            elapsed_minutes = (
                next_departure_datetime
                - arrival_datetime
            ).total_seconds() / 60

            airport = flight.arrival

            if airport not in results:
                results[airport] = {
                    "turnarounds": [],
                    "layovers": [],
                }

            # A stay of 10 hours or more is treated as a layover.
            # Anything shorter than 10 hours is treated as a turnaround.
            if elapsed_minutes >= 10 * 60:
                # Long stays at a configured home base are time at home,
                # not layovers.
                if airport in self.home_bases:
                    continue

                results[airport][
                    "layovers"
                ].append(
                    elapsed_minutes
                )
            else:
                results[airport][
                    "turnarounds"
                ].append(
                    elapsed_minutes
                )

        return results


    def get_country(
        self,
        airport,
    ):
        """Return the airport country when available."""

        try:
            record = (
                self.database.find(
                    airport
                )
            )

            if record is None:
                return "—"

            if isinstance(
                record,
                dict,
            ):
                country = (
                    record.get("country")
                    or record.get(
                        "country_name"
                    )
                )

                if country:
                    return str(
                        country
                    )

            return "—"

        except Exception:
            return "—"

    def set_item(
        self,
        row,
        column,
        text,
        sort_value=None,
    ):
        """Set one table cell with optional numeric sorting."""

        item = SortableTableWidgetItem(
            text,
            sort_value,
        )

        self.table.setItem(
            row,
            column,
            item,
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

        self.logbook_path = load_saved_logbook()

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
            AircraftPage()
        )

        self.airports_page = (
            AirportsPage()
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

        self.dashboard_page.change_logbook_button.clicked.connect(
            self.choose_logbook
        )

        self.dashboard_page.logbook_selected.connect(
            self.set_logbook
        )

        # -------------------------------------------------
        # INITIAL LOAD
        # -------------------------------------------------

        if self.logbook_path is not None:
            self.load_data()
        else:
            self.dashboard_page.show_logbook_selector()

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

        if self.logbook_path is None:
            self.dashboard_page.show_logbook_selector()
            return

        self.logbook_path = Path(
            self.logbook_path
        ).expanduser()

        if (
            not self.logbook_path.exists()
            or not self.logbook_path.is_file()
        ):
            self.data = None
            self.dashboard_page.show_logbook_selector(
                "The previously selected logbook could not be found. "
                "Please select it again."
            )
            return

        self.dashboard_page.show_loading()

        self.dashboard_page.refresh_button.setEnabled(
            False
        )

        self.dashboard_page.change_logbook_button.setEnabled(
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
                self.logbook_path
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

    def choose_logbook(self):
        """Open the logbook file picker."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Flight Logbook",
            "",
            "PDF files (*.pdf)",
        )

        if path:
            self.set_logbook(
                path
            )

    def set_logbook(self, path):
        """Set, persist and load a new user logbook."""
        path = Path(
            path
        ).expanduser()

        if (
            not path.exists()
            or not path.is_file()
            or path.suffix.lower() != ".pdf"
        ):
            QMessageBox.warning(
                self,
                "Invalid Logbook",
                "Please select a valid PDF logbook.",
            )
            return

        if (
            self.loader_thread is not None
            and self.loader_thread.isRunning()
        ):
            return

        self.logbook_path = path.resolve()

        try:
            save_logbook_path(
                self.logbook_path
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Could Not Save Setting",
                f"FlightStats could not save the logbook location:\n{error}",
            )
            return

        self.data = None

        self.dashboard_page.show_loading()
        self.dashboard_page.status_label.setText(
            f"Loading {self.logbook_path.name}..."
        )

        self.load_data()

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
            self.data,
            self.logbook_path,
        )

        self.logbook_page.set_data(
            self.data
        )

        self.aircraft_page.set_data(
            self.data
        )

        self.airports_page.set_data(
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

        self.dashboard_page.change_logbook_button.setEnabled(
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

        #aircraftTable {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            gridline-color: #eef0f2;
            selection-background-color: #e5e7eb;
            selection-color: #111827;
        }

        #aircraftTable QHeaderView::section {
            background: #f9fafb;
            color: #4b5563;
            border: none;
            border-bottom: 1px solid #e5e7eb;
            padding: 10px 8px;
            font-size: 12px;
            font-weight: 600;
        }

        #aircraftTable QTableWidgetItem {
            padding: 8px;
        }

        #homeBaseList {
            background: transparent;
            border: none;
            padding: 0;
        }

        #homeBaseList::item {
            background: #111827;
            color: white;
            border-radius: 7px;
            padding: 7px 12px;
            margin-right: 5px;
            font-weight: 600;
        }

        #homeBaseList::item:selected {
            background: #374151;
        }

        #airportsTable {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            gridline-color: #eef0f2;
            selection-background-color: #e5e7eb;
            selection-color: #111827;
        }

        #airportsTable QHeaderView::section {
            background: #f9fafb;
            color: #4b5563;
            border: none;
            border-bottom: 1px solid #e5e7eb;
            padding: 10px 8px;
            font-size: 12px;
            font-weight: 600;
        }

        #airportsTable QTableWidgetItem {
            padding: 8px;
        }

        #yearTabs::pane {
            border: none;
            background: transparent;
        }

        #yearTabs QTabBar::tab {
            background: #111827;
            color: #d1d5db;
            border: 1px solid #111827;
            border-radius: 7px;
            padding: 9px 20px;
            margin-right: 6px;
            min-width: 58px;
            font-size: 13px;
            font-weight: 600;
        }

        #yearTabs QTabBar::tab:hover {
            background: #1f2937;
            color: white;
        }

        #yearTabs QTabBar::tab:selected {
            background: #374151;
            color: white;
            border: 1px solid #374151;
            font-weight: 700;
        }

        #yearTabs QTabBar::tab:pressed {
            background: #4b5563;
        }

        #logbookDropZone {
            background: white;
            border: 2px dashed #d1d5db;
            border-radius: 14px;
            min-height: 210px;
        }

        #logbookDropZone:hover {
            border: 2px dashed #6b7280;
            background: #f9fafb;
        }

        #logbookDropZone[dragActive="true"] {
            border: 2px dashed #111827;
            background: #f3f4f6;
        }

        #logbookDropIcon {
            color: #374151;
            font-size: 30px;
            font-weight: 700;
        }

        #logbookDropTitle {
            color: #111827;
            font-size: 20px;
            font-weight: 700;
        }

        #logbookDropSubtitle {
            color: #6b7280;
            font-size: 13px;
        }

        #logbookBrowseButton {
            background: #111827;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
        }

        #logbookBrowseButton:hover {
            background: #1f2937;
        }

        #logbookBrowseButton:pressed {
            background: #374151;
        }

        #logbookStatusLabel {
            color: #6b7280;
            font-size: 12px;
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