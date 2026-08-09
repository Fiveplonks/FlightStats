import sys
import json
import math
from pathlib import Path
from datetime import date, datetime, timedelta

from PySide6.QtCore import (
    QObject,
    Qt,
    QThread,
    Signal,
    QEvent,
    QTimer,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QPalette, QPalette

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
    QSlider,
    QStackedWidget,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
QScrollArea,
QSizePolicy,
    QHeaderView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QColorDialog,
    QFileDialog,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl


from app_paths import (
    SETTINGS_FILE,
    get_logbook_path,
)
from data_manager import FlightStatsData
from parser.airports import AirportDatabase
from parser.fuel import FuelDatabase


LOGBOOK = get_logbook_path()


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
# DASHBOARD
# =========================================================


class LogbookDropZone(QFrame):
    """Dashboard drop zone for selecting a logbook PDF or CSV."""

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
            "Drop your logbook PDF or CSV here"
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
            "or click to browse for a PDF or CSV"
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
            "Choose Logbook"
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
        """Open the logbook file picker."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Flight Logbook",
            "",
            "Logbook files (*.pdf *.csv)",
        )

        if path:
            self._select_path(
                path
            )

    def _select_path(self, path):
        """Validate and emit a selected logbook path."""
        path = Path(path)

        if (
            not path.exists()
            or not path.is_file()
            or path.suffix.lower() not in {".pdf", ".csv"}
        ):
            QMessageBox.warning(
                self,
                "Invalid Logbook",
                "Please select a valid PDF or CSV logbook.",
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
        """Accept dragged PDF or CSV files."""
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
        """Handle a dropped PDF or CSV logbook."""
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
            "Flight time"
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

        # Scrollable aircraft list so rows keep their
        # natural height regardless of aircraft count.
        self.aircraft_scroll = QScrollArea()

        self.aircraft_scroll.setWidgetResizable(
            True
        )

        self.aircraft_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.aircraft_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        self.aircraft_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.aircraft_scroll.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.aircraft_content = QWidget()

        self.aircraft_layout = QVBoxLayout(
            self.aircraft_content
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

        self.aircraft_scroll.setWidget(
            self.aircraft_content
        )

        container_layout = QVBoxLayout(
            self.aircraft_container
        )

        container_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        container_layout.addWidget(
            self.aircraft_scroll
        )

        self.layout.addWidget(
            self.aircraft_container
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
# FUEL PAGE
# =========================================================


class FuelPage(QWidget):
    """Estimated fuel consumption statistics."""

    def __init__(self):
        super().__init__()

        self.data = None
        self.selected_year = None
        self.database = FuelDatabase()

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            40,
            35,
            40,
            35,
        )

        layout.setSpacing(15)

        title = QLabel("Fuel")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Estimated fuel consumption based on aircraft fuel-burn profiles"
        )
        subtitle.setObjectName("pageSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # -------------------------------------------------
        # KPI CARDS
        # -------------------------------------------------

        cards_layout = QGridLayout()
        cards_layout.setSpacing(12)

        self.jet_total_card = MetricCard(
            "Estimated jet fuel"
        )
        self.piston_total_card = MetricCard(
            "Estimated Avgas"
        )
        self.jet_average_card = MetricCard(
            "Avg. jet fuel / flight"
        )
        self.piston_average_card = MetricCard(
            "Avg. Avgas / flight"
        )

        cards_layout.addWidget(
            self.jet_total_card,
            0,
            0,
        )
        cards_layout.addWidget(
            self.piston_total_card,
            0,
            1,
        )
        cards_layout.addWidget(
            self.jet_average_card,
            0,
            2,
        )
        cards_layout.addWidget(
            self.piston_average_card,
            0,
            3,
        )

        layout.addLayout(cards_layout)

        self.coverage_label = QLabel(
            "Fuel estimates: —"
        )
        self.coverage_label.setObjectName("statusLabel")
        layout.addWidget(self.coverage_label)

        # -------------------------------------------------
        # YEAR TABS
        # -------------------------------------------------

        self.year_tabs = QTabWidget()
        self.year_tabs.setObjectName("yearTabs")

        year_bar = self.year_tabs.tabBar()
        year_bar.setUsesScrollButtons(True)
        year_bar.setExpanding(False)

        self.year_tabs.currentChanged.connect(
            self.year_tab_changed
        )

        layout.addWidget(self.year_tabs)

        # -------------------------------------------------
        # AIRCRAFT TABLE
        # -------------------------------------------------

        aircraft_title = QLabel(
            "Fuel by Aircraft"
        )
        aircraft_title.setObjectName("sectionTitle")
        layout.addWidget(aircraft_title)

        self.aircraft_table = QTableWidget()
        self.aircraft_table.setObjectName("fuelTable")
        self.aircraft_table.setColumnCount(8)
        self.aircraft_table.setHorizontalHeaderLabels(
            [
                "Aircraft",
                "Flights",
                "Flight Time",
                "Estimated Fuel",
                "Avg. / Flight",
                "Avg. / Hour",
                "Source",
                "Coverage",
            ]
        )
        self.aircraft_table.setSortingEnabled(True)
        self.aircraft_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.aircraft_table.setSelectionMode(
            QTableWidget.SingleSelection
        )
        self.aircraft_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.aircraft_table.verticalHeader().setVisible(False)

        header = self.aircraft_table.horizontalHeader()
        header.setStretchLastSection(True)

        for column in range(
            self.aircraft_table.columnCount()
        ):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        layout.addWidget(
            self.aircraft_table,
            1,
        )

        # -------------------------------------------------
        # YEAR SUMMARY
        # -------------------------------------------------

        yearly_title = QLabel(
            "Fuel by Year"
        )
        yearly_title.setObjectName("sectionTitle")
        layout.addWidget(yearly_title)

        self.yearly_table = QTableWidget()
        self.yearly_table.setObjectName("fuelYearTable")
        self.yearly_table.setColumnCount(8)
        self.yearly_table.setHorizontalHeaderLabels(
            [
                "Year",
                "Flights",
                "Flight Time",
                "Jet Fuel",
                "Avgas",
                "Avg. Jet / Flight",
                "Avg. Piston / Flight",
                "Coverage",
            ]
        )
        self.yearly_table.setSortingEnabled(True)
        self.yearly_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.yearly_table.setSelectionMode(
            QTableWidget.SingleSelection
        )
        self.yearly_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.yearly_table.verticalHeader().setVisible(False)

        yearly_header = self.yearly_table.horizontalHeader()
        yearly_header.setStretchLastSection(True)

        for column in range(
            self.yearly_table.columnCount()
        ):
            yearly_header.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

        layout.addWidget(self.yearly_table)

    def set_data(self, data):
        """Load shared FlightStats data."""
        self.data = data
        self.build_year_tabs()
        self.update_yearly_table()

    def build_year_tabs(self):
        """Build ALL and one tab for every logbook year."""
        self.year_tabs.blockSignals(True)
        self.year_tabs.clear()

        if self.data is None:
            self.year_tabs.blockSignals(False)
            return

        years = sorted(
            {
                flight.date.year
                for flight in self.data.flights
            },
            reverse=True,
        )

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
        self.year_tabs.blockSignals(False)
        self.year_tabs.setCurrentIndex(0)
        self.update_page()

    def year_tab_changed(self, index):
        """Update fuel statistics for the selected year."""
        if self.data is None or index < 0:
            return

        text = self.year_tabs.tabText(index)
        self.selected_year = (
            None
            if text == "ALL"
            else int(text)
        )

        self.update_page()

    def _fuel_result(self, index):
        """Return a valid fuel result for a flight index."""
        if index >= len(self.data.fuel_results):
            return None

        result = self.data.fuel_results[index]

        if not isinstance(result, dict):
            return None

        return result

    def _format_fuel(self, amount, unit):
        """Format a fuel amount using the result's unit."""
        if amount is None or unit is None:
            return "—"

        return (
            f"{amount:,.1f} "
            f"{display_fuel_unit(unit)}"
        )

    def update_page(self):
        """Calculate and display fuel statistics for the selected year."""
        if self.data is None:
            return

        indexes = [
            index
            for index, flight in enumerate(
                self.data.flights
            )
            if (
                self.selected_year is None
                or flight.date.year == self.selected_year
            )
        ]

        jet_total = 0.0
        piston_total = 0.0
        jet_count = 0
        piston_count = 0
        covered_count = 0

        aircraft_stats = {}

        for index in indexes:
            flight = self.data.flights[index]
            aircraft = self.database.normalize_type(
                flight.aircraft
            ) if hasattr(self, "database") else flight.aircraft

            if aircraft not in aircraft_stats:
                aircraft_stats[aircraft] = {
                    "flights": 0,
                    "minutes": 0,
                    "fuel": 0.0,
                    "fuel_unit": None,
                    "source": None,
                    "method": None,
                    "covered": 0,
                }

            item = aircraft_stats[aircraft]
            item["flights"] += 1
            item["minutes"] += flight.flight_minutes or 0

            result = self._fuel_result(index)

            if result is None:
                continue

            fuel = result.get("fuel")
            unit = result.get("unit")

            if fuel is None or unit not in ("kg/h", "L/h"):
                continue

            item["fuel"] += fuel
            item["fuel_unit"] = display_fuel_unit(unit)
            item["source"] = result.get("source")
            item["method"] = result.get("method")
            item["covered"] += 1
            covered_count += 1

            if unit == "kg/h":
                jet_total += fuel
                jet_count += 1
            elif unit == "L/h":
                piston_total += fuel
                piston_count += 1

        # -------------------------------------------------
        # KPI CARDS
        # -------------------------------------------------

        self.jet_total_card.set_value(
            f"{jet_total:,.1f} kg"
        )
        self.piston_total_card.set_value(
            f"{piston_total:,.1f} L"
        )

        self.jet_average_card.set_value(
            (
                f"{jet_total / jet_count:,.1f} kg"
                if jet_count
                else "—"
            )
        )
        self.piston_average_card.set_value(
            (
                f"{piston_total / piston_count:,.1f} L"
                if piston_count
                else "—"
            )
        )

        total_flights = len(indexes)
        coverage = (
            covered_count / total_flights * 100
            if total_flights
            else 0
        )

        self.coverage_label.setText(
            f"Fuel estimates available for "
            f"{covered_count:,} of {total_flights:,} flights "
            f"({coverage:.1f}%)"
        )

        # -------------------------------------------------
        # AIRCRAFT TABLE
        # -------------------------------------------------

        self.aircraft_table.setSortingEnabled(False)
        self.aircraft_table.setRowCount(
            len(aircraft_stats)
        )

        for row, aircraft in enumerate(
            sorted(
                aircraft_stats,
                key=lambda value: str(value).upper(),
            )
        ):
            item = aircraft_stats[aircraft]
            flights = item["flights"]
            minutes = item["minutes"]
            fuel = item["fuel"]
            unit = item["fuel_unit"]
            source = item["source"] or "Unknown"
            covered = item["covered"]

            average_flight = (
                fuel / covered
                if covered
                else None
            )

            average_hour = (
                fuel / minutes * 60
                if covered and minutes
                else None
            )

            coverage_text = (
                f"{covered:,}/{flights:,}"
            )

            values = [
                (str(aircraft), str(aircraft)),
                (f"{flights:,}", flights),
                (
                    format_hours(minutes),
                    minutes,
                ),
                (
                    self._format_fuel(
                        fuel if covered else None,
                        unit,
                    ),
                    fuel if covered else -1,
                ),
                (
                    self._format_fuel(
                        average_flight,
                        unit,
                    ),
                    average_flight if average_flight is not None else -1,
                ),
                (
                    self._format_fuel(
                        average_hour,
                        unit,
                    ),
                    average_hour if average_hour is not None else -1,
                ),
                (
                    str(source),
                    str(source).upper(),
                ),
                (
                    coverage_text,
                    covered / flights if flights else 0,
                ),
            ]

            for column, (text, sort_value) in enumerate(values):
                self.set_item(
                    self.aircraft_table,
                    row,
                    column,
                    text,
                    sort_value,
                )

        self.aircraft_table.setSortingEnabled(True)

        # -------------------------------------------------
        # YEAR SUMMARY
        # -------------------------------------------------

        self.update_yearly_table()

    def update_yearly_table(self):
        """Display annual fuel totals independent of the selected tab."""
        if self.data is None:
            self.yearly_table.setRowCount(0)
            return

        years = sorted(
            {
                flight.date.year
                for flight in self.data.flights
            },
            reverse=True,
        )

        self.yearly_table.setSortingEnabled(False)
        self.yearly_table.setRowCount(len(years))

        for row, year in enumerate(years):
            indexes = [
                index
                for index, flight in enumerate(
                    self.data.flights
                )
                if flight.date.year == year
            ]

            jet_total = 0.0
            piston_total = 0.0
            jet_count = 0
            piston_count = 0
            covered = 0
            minutes = sum(
                self.data.flights[index].flight_minutes or 0
                for index in indexes
            )

            for index in indexes:
                result = self._fuel_result(index)

                if result is None:
                    continue

                fuel = result.get("fuel")
                unit = result.get("unit")

                if fuel is None:
                    continue

                covered += 1

                if unit == "kg/h":
                    jet_total += fuel
                    jet_count += 1
                elif unit == "L/h":
                    piston_total += fuel
                    piston_count += 1

            coverage = (
                covered / len(indexes) * 100
                if indexes
                else 0
            )

            values = [
                (str(year), year),
                (f"{len(indexes):,}", len(indexes)),
                (format_hours(minutes), minutes),
                (
                    f"{jet_total:,.1f} kg" if jet_count else "—",
                    jet_total,
                ),
                (
                    f"{piston_total:,.1f} L" if piston_count else "—",
                    piston_total,
                ),
                (
                    f"{jet_total / jet_count:,.1f} kg"
                    if jet_count else "—",
                    jet_total / jet_count if jet_count else -1,
                ),
                (
                    f"{piston_total / piston_count:,.1f} L"
                    if piston_count else "—",
                    piston_total / piston_count if piston_count else -1,
                ),
                (
                    f"{coverage:.1f}%",
                    coverage,
                ),
            ]

            for column, (text, sort_value) in enumerate(values):
                self.set_item(
                    self.yearly_table,
                    row,
                    column,
                    text,
                    sort_value,
                )

        self.yearly_table.setSortingEnabled(True)

    def set_item(
        self,
        table,
        row,
        column,
        text,
        sort_value=None,
    ):
        """Set a sortable table cell."""
        item = SortableTableWidgetItem(
            str(text),
            sort_value,
        )
        table.setItem(row, column, item)

# =========================================================
# MAP PAGE
# =========================================================


class WorldMapWidget(QWidget):
    """Online Leaflet map for the user's flights."""

    MONTH_ANIMATION_MS = 15000

    MAP_HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet"
      href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
      crossorigin="">
<style>
html, body, #map {
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
}
body {
    background: #e5e7eb;
}
.leaflet-container {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #dbeafe;
}
.airport-marker {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: 1.5px solid white;
    box-shadow: 0 0 0 1px rgba(17,24,39,.55);
    background: #ffffff;
}
.aircraft-icon {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    transform-origin: center center;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,.35));
}
.aircraft-icon svg {
    width: 22px;
    height: 22px;
}
</style>
</head>
<body>
<div id="map"></div>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
        crossorigin=""></script>
<script>
const map = L.map('map', {
    worldCopyJump: false,
    minZoom: 1,
    maxZoom: 18,
    zoomControl: true,
    attributionControl: true
});
            // Start with the complete world visible. Leaflet calculates
            // the appropriate zoom from the actual map container size.
            map.fitBounds([
                [-85, -180],
                [85, 180]
            ]);


L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    crossOrigin: true
}).addTo(map);

let traceColor = '#111827';
let currentRoutes = [];
let cumulativeRoutes = [];
let currentAirports = {};
let cumulativeAirports = {};
let currentLayers = [];
let cumulativeLayers = [];
let airportLayers = [];
let animationFrame = null;
let animationStartedAt = null;
let animationActive = false;
let aircraftMarker = null;

function clearLayers(list) {
    for (const layer of list) {
        map.removeLayer(layer);
    }
    list.length = 0;
}

function clearAircraft() {
    if (aircraftMarker) {
        map.removeLayer(aircraftMarker);
        aircraftMarker = null;
    }
}

function makeCurve(dep, arr) {
    // Quadratic curve in geographic coordinates. The route endpoints
    // remain exact WGS84 coordinates; curvature is purely visual.
    const lat1 = dep[0], lon1 = dep[1];
    const lat2 = arr[0], lon2 = arr[1];

    let dLon = lon2 - lon1;
    if (Math.abs(dLon) > 180) return null;

    const dx = dLon;
    const dy = lat2 - lat1;
    const length = Math.sqrt(dx * dx + dy * dy) || 1;

    const nx = -dy / length;
    const ny = dx / length;
    const bend = Math.min(12, length * 0.10);

    const cx = (lon1 + lon2) / 2 + nx * bend;
    const cy = (lat1 + lat2) / 2 + ny * bend;

    const points = [];
    const steps = 24;

    for (let i = 0; i <= steps; i++) {
        const t = i / steps;
        const u = 1 - t;
        const lon = u * u * lon1 + 2 * u * t * cx + t * t * lon2;
        const lat = u * u * lat1 + 2 * u * t * cy + t * t * lat2;
        points.push([lat, lon]);
    }

    return points;
}

function routePoints(route) {
    return makeCurve(route.dep, route.arr);
}

function drawRoutes(routes, target, opacity) {
    clearLayers(target);

    for (const route of routes) {
        const points = routePoints(route);
        if (!points) continue;

        const line = L.polyline(points, {
            color: traceColor,
            weight: 2.5,
            opacity: opacity,
            lineCap: 'round',
            lineJoin: 'round',
            interactive: false
        }).addTo(map);

        target.push(line);
    }
}

function drawAirports() {
    clearLayers(airportLayers);

    const all = {};
    Object.assign(all, cumulativeAirports);
    Object.assign(all, currentAirports);

    for (const code of Object.keys(all)) {
        const airport = all[code];
        const icon = L.divIcon({
            className: '',
            html: '<div class="airport-marker"></div>',
            iconSize: [8, 8],
            iconAnchor: [4, 4]
        });

        const marker = L.marker(
            [airport.lat, airport.lon],
            { icon: icon, interactive: true }
        ).bindTooltip(code, {
            direction: 'top',
            offset: [0, -4]
        });

        marker.addTo(map);
        airportLayers.push(marker);
    }
}

function setViewWorld() {
    map.fitWorld({ padding: [10, 10] });
}

function setData(data) {
    currentRoutes = data.currentRoutes || [];
    cumulativeRoutes = data.cumulativeRoutes || [];
    currentAirports = data.currentAirports || {};
    cumulativeAirports = data.cumulativeAirports || {};
    traceColor = data.traceColor || '#111827';

    drawRoutes(cumulativeRoutes, cumulativeLayers, 0.72);
    drawRoutes(currentRoutes, currentLayers, 0.95);
    drawAirports();

    if (data.animationActive) {
        startAnimation();
    } else {
        stopAnimation();
    }
}

function aircraftIcon(angle) {
    return L.divIcon({
        className: 'aircraft-icon',
        html: `<svg viewBox="0 0 24 24" style="transform:rotate(${angle}deg)">
            <path d="M21 11.2L13.6 8.4V3.3c0-.8-.7-1.3-1.6-1.3s-1.6.5-1.6 1.3v5.1L3 11.2v1.9l7.4-1.2v5.0l-2.3 1.5v1.4l3.9-.8 3.9.8v-1.4l-2.3-1.5v-5l7.4 1.2v-1.9z" fill="${traceColor}"/>
        </svg>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
    });
}

function interpolate(points, t) {
    if (!points || points.length === 0) return null;
    if (points.length === 1) return { lat: points[0][0], lon: points[0][1], angle: 0 };

    const scaled = t * (points.length - 1);
    const index = Math.min(points.length - 2, Math.floor(scaled));
    const local = scaled - index;

    const a = points[index];
    const b = points[index + 1];
    const lat = a[0] + (b[0] - a[0]) * local;
    const lon = a[1] + (b[1] - a[1]) * local;

    const dy = b[0] - a[0];
    const dx = b[1] - a[1];
    const angle = Math.atan2(dy, dx) * 180 / Math.PI + 90;

    return { lat, lon, angle };
}

function animationFrameStep(timestamp) {
    if (!animationActive) return;

    if (animationStartedAt === null) {
        animationStartedAt = timestamp;
    }

    const elapsed = timestamp - animationStartedAt;
    const progress = Math.min(1, elapsed / 15000);
    const count = currentRoutes.length;

    if (count > 0) {
        const timeline = progress * count;
        const completed = Math.min(count, Math.floor(timeline));
        const currentProgress = timeline - completed;

        // Re-render current month routes according to the sequential timeline.
        clearLayers(currentLayers);

        for (let i = 0; i < completed; i++) {
            const points = routePoints(currentRoutes[i]);
            if (!points) continue;
            currentLayers.push(
                L.polyline(points, {
                    color: traceColor,
                    weight: 2.5,
                    opacity: 0.95,
                    lineCap: 'round',
                    lineJoin: 'round',
                    interactive: false
                }).addTo(map)
            );
        }

        if (completed < count && currentProgress > 0) {
            const route = currentRoutes[completed];
            const points = routePoints(route);

            if (points) {
                const partialCount = Math.max(
                    2,
                    Math.floor(currentProgress * (points.length - 1)) + 1
                );
                const partial = points.slice(0, partialCount);
                const position = interpolate(points, currentProgress);

                currentLayers.push(
                    L.polyline(partial, {
                        color: traceColor,
                        weight: 2.5,
                        opacity: 0.95,
                        lineCap: 'round',
                        lineJoin: 'round',
                        interactive: false
                    }).addTo(map)
                );

                if (position) {
                    if (!aircraftMarker) {
                        aircraftMarker = L.marker(
                            [position.lat, position.lon],
                            { icon: aircraftIcon(position.angle), interactive: false }
                        ).addTo(map);
                    } else {
                        aircraftMarker.setLatLng([position.lat, position.lon]);
                        aircraftMarker.setIcon(aircraftIcon(position.angle));
                    }
                }
            }
        }
    }

    if (progress >= 1) {
        clearAircraft();
        animationActive = false;
        animationStartedAt = null;
        drawRoutes(currentRoutes, currentLayers, 0.95);
        return;
    }

    animationFrame = requestAnimationFrame(animationFrameStep);
}

function startAnimation() {
    if (animationFrame !== null) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
    }

    clearAircraft();
    animationActive = true;
    animationStartedAt = null;
    animationFrame = requestAnimationFrame(animationFrameStep);
}

function stopAnimation() {
    animationActive = false;
    animationStartedAt = null;

    if (animationFrame !== null) {
        cancelAnimationFrame(animationFrame);
        animationFrame = null;
    }

    clearAircraft();
    drawRoutes(currentRoutes, currentLayers, 0.95);
}

function resetAnimation() {
    animationStartedAt = null;
    clearAircraft();

    if (animationActive) {
        startAnimation();
    } else {
        drawRoutes(currentRoutes, currentLayers, 0.95);
    }
}

function zoomIn() { map.zoomIn(); }
function zoomOut() { map.zoomOut(); }
function resetView() { setViewWorld(); }
function setTraceColor(color) {
    traceColor = color;
    drawRoutes(cumulativeRoutes, cumulativeLayers, 0.72);
    drawRoutes(currentRoutes, currentLayers, 0.95);
    drawAirports();
}

window.flightStatsMap = {
    setData,
    startAnimation,
    stopAnimation,
    resetAnimation,
    zoomIn,
    zoomOut,
    resetView,
    setTraceColor
};

setViewWorld();
</script>
</body>
</html>
"""

    def __init__(self):
        super().__init__()

        self.routes = []
        self.airports = {}
        self.cumulative_routes = []
        self.cumulative_airports = {}

        self.trace_color = QColor("#111827")
        self.animation_active = False
        self._page_ready = False
        self._pending_sync = True

        self.setMinimumHeight(430)
        self.setObjectName("flightMap")

        self.web = QWebEngineView(self)
        self.web.setContextMenuPolicy(Qt.NoContextMenu)
        self.web.page().profile().setHttpUserAgent(
            "FlightStats desktop application"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web)

        self.web.loadFinished.connect(
            self._map_loaded
        )
        self.web.setHtml(
            self.MAP_HTML,
            QUrl("https://flightstats.local/")
        )

    # -----------------------------------------------------
    # MAP SYNCHRONISATION
    # -----------------------------------------------------

    @staticmethod
    def _airport_payload(airports):
        result = {}
        for code, value in airports.items():
            result[code] = {
                "lon": value[0],
                "lat": value[1],
            }
        return result

    @staticmethod
    def _route_payload(routes):
        result = []
        for dep, arr in routes:
            result.append({
                "dep": [dep[1], dep[0]],
                "arr": [arr[1], arr[0]],
            })
        return result

    def _sync_map(self):
        if not self._page_ready:
            self._pending_sync = True
            return

        import json

        payload = {
            "currentRoutes": self._route_payload(self.routes),
            "cumulativeRoutes": self._route_payload(
                self.cumulative_routes
            ),
            "currentAirports": self._airport_payload(
                self.airports
            ),
            "cumulativeAirports": self._airport_payload(
                self.cumulative_airports
            ),
            "traceColor": self.trace_color.name(),
            "animationActive": self.animation_active,
        }

        payload_json = json.dumps(payload)

        self.web.page().runJavaScript(
            "window.flightStatsMap.setData(" + payload_json + ");"
        )
        self._pending_sync = False

    def _map_loaded(self, ok):
        self._page_ready = bool(ok)
        if self._page_ready:
            self._pending_sync = False
            self._sync_map()

    # -----------------------------------------------------
    # DATA
    # -----------------------------------------------------

    def set_flights(self, flights, database):
        """Set the routes currently visible on the map."""

        self.routes = []
        self.airports = {}

        for flight in flights:
            departure = database.find(flight.departure)
            arrival = database.find(flight.arrival)

            if departure is None or arrival is None:
                continue

            if (
                departure.get("latitude") is None
                or departure.get("longitude") is None
                or arrival.get("latitude") is None
                or arrival.get("longitude") is None
            ):
                continue

            dep = (
                float(departure["longitude"]),
                float(departure["latitude"]),
                flight.departure,
            )
            arr = (
                float(arrival["longitude"]),
                float(arrival["latitude"]),
                flight.arrival,
            )

            self.routes.append((dep, arr))
            self.airports[flight.departure] = dep
            self.airports[flight.arrival] = arr

        self._sync_map()

    def set_cumulative_flights(self, flights, database):
        """Set routes belonging to months before the current month."""

        routes = []
        airports = {}

        for flight in flights:
            departure = database.find(flight.departure)
            arrival = database.find(flight.arrival)

            if departure is None or arrival is None:
                continue

            if (
                departure.get("latitude") is None
                or departure.get("longitude") is None
                or arrival.get("latitude") is None
                or arrival.get("longitude") is None
            ):
                continue

            dep = (
                float(departure["longitude"]),
                float(departure["latitude"]),
                flight.departure,
            )
            arr = (
                float(arrival["longitude"]),
                float(arrival["latitude"]),
                flight.arrival,
            )

            routes.append((dep, arr))
            airports[flight.departure] = dep
            airports[flight.arrival] = arr

        self.cumulative_routes = routes
        self.cumulative_airports = airports
        self._sync_map()

    # -----------------------------------------------------
    # AIRCRAFT ANIMATION
    # -----------------------------------------------------

    def start_animation(self):
        self.animation_active = True

        if self._page_ready:
            self.web.page().runJavaScript(
                "window.flightStatsMap.startAnimation();"
            )
        else:
            self._pending_sync = True

    def stop_animation(self):
        self.animation_active = False

        if self._page_ready:
            self.web.page().runJavaScript(
                "window.flightStatsMap.stopAnimation();"
            )

    def reset_animation(self):
        if self._page_ready:
            self.web.page().runJavaScript(
                "window.flightStatsMap.resetAnimation();"
            )

    # -----------------------------------------------------
    # ZOOM / PAN
    # -----------------------------------------------------

    def zoom_in(self):
        if self._page_ready:
            self.web.page().runJavaScript(
                "window.flightStatsMap.zoomIn();"
            )

    def zoom_out(self):
        if self._page_ready:
            self.web.page().runJavaScript(
                "window.flightStatsMap.zoomOut();"
            )

    def reset_view(self):
        if self._page_ready:
            self.web.page().runJavaScript(
                "window.flightStatsMap.resetView();"
            )

    # -----------------------------------------------------
    # TRACE COLOR
    # -----------------------------------------------------

    def set_trace_color(self, color):
        if not color.isValid():
            return

        self.trace_color = QColor(color)

        if self._page_ready:
            import json
            self.web.page().runJavaScript(
                "window.flightStatsMap.setTraceColor("
                + json.dumps(self.trace_color.name())
                + ");"
            )


class MapPage(QWidget):
    """Animated online map of the user's flights."""

    MONTHS = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    MONTH_PLAYBACK_MS = 15000

    def __init__(self):
        super().__init__()
        self.data = None
        self.database = AirportDatabase()
        self.selected_year = None
        self.selected_month = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 35, 40, 35)
        layout.setSpacing(15)

        title = QLabel("Map")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Explore your flights by year, month and aircraft"
        )
        subtitle.setObjectName("pageSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        map_disclaimer = QLabel(
            "Map visualization requires an active internet connection."
        )
        map_disclaimer.setObjectName("statusLabel")
        layout.addWidget(map_disclaimer)

        controls = QHBoxLayout()
        controls.setSpacing(10)

        year_label = QLabel("Year:")
        year_label.setStyleSheet("font-weight: 600;")
        controls.addWidget(year_label)

        self.year_combo = QComboBox()
        self.year_combo.setObjectName("filterBox")
        self.year_combo.currentIndexChanged.connect(
            self.filters_changed
        )
        controls.addWidget(self.year_combo)

        aircraft_label = QLabel("Aircraft:")
        aircraft_label.setStyleSheet("font-weight: 600;")
        controls.addWidget(aircraft_label)

        self.aircraft_combo = QComboBox()
        self.aircraft_combo.setObjectName("filterBox")
        self.aircraft_combo.currentIndexChanged.connect(
            self.filters_changed
        )
        controls.addWidget(self.aircraft_combo)

        controls.addStretch()
        layout.addLayout(controls)

        # -------------------------------------------------
        # MAP CONTROLS
        # -------------------------------------------------

        map_controls = QHBoxLayout()
        map_controls.setSpacing(8)

        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("font-weight: 600;")
        map_controls.addWidget(zoom_label)

        self.zoom_out_button = QPushButton("−")
        self.zoom_out_button.setFixedWidth(38)
        map_controls.addWidget(self.zoom_out_button)

        self.zoom_reset_button = QPushButton("Reset")
        self.zoom_reset_button.setFixedWidth(58)
        map_controls.addWidget(self.zoom_reset_button)

        self.zoom_in_button = QPushButton("+")
        self.zoom_in_button.setFixedWidth(38)
        map_controls.addWidget(self.zoom_in_button)

        self.zoom_out_button.clicked.connect(
            lambda: self.map.zoom_out()
        )
        self.zoom_reset_button.clicked.connect(
            lambda: self.map.reset_view()
        )
        self.zoom_in_button.clicked.connect(
            lambda: self.map.zoom_in()
        )

        map_controls.addSpacing(12)

        trace_label = QLabel("Flight trace:")
        trace_label.setStyleSheet("font-weight: 600;")
        map_controls.addWidget(trace_label)

        self.trace_color_button = QPushButton("Choose color")
        self.trace_color_button.clicked.connect(
            self.choose_trace_color
        )
        map_controls.addWidget(self.trace_color_button)

        map_controls.addStretch()
        layout.addLayout(map_controls)

        self.map = WorldMapWidget()
        layout.addWidget(self.map, 1)
        self.update_trace_color_button()

        self.month_label = QLabel("January")
        self.month_label.setObjectName("sectionTitle")
        self.month_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.month_label)

        slider_row = QHBoxLayout()

        self.previous_button = QPushButton("◀")
        self.previous_button.setFixedWidth(42)
        self.previous_button.clicked.connect(self.previous_month)

        self.month_slider = QSlider(Qt.Horizontal)
        self.month_slider.setMinimum(0)
        self.month_slider.setMaximum(11)
        self.month_slider.setValue(0)
        self.month_slider.setTickPosition(QSlider.TicksBelow)
        self.month_slider.setTickInterval(1)
        self.month_slider.valueChanged.connect(self.month_changed)

        self.next_button = QPushButton("▶")
        self.next_button.setFixedWidth(42)
        self.next_button.clicked.connect(self.next_month)

        slider_row.addWidget(self.previous_button)
        slider_row.addWidget(self.month_slider, 1)
        slider_row.addWidget(self.next_button)
        layout.addLayout(slider_row)

        bottom_row = QHBoxLayout()

        self.play_button = QPushButton("▶ Play")
        self.play_button.clicked.connect(self.toggle_play)
        bottom_row.addWidget(self.play_button)

        self.flight_count_label = QLabel("0 flights")
        self.flight_count_label.setObjectName("statusLabel")
        bottom_row.addWidget(self.flight_count_label)

        bottom_row.addStretch()
        layout.addLayout(bottom_row)

        # Parent timer advances the calendar one month every 15 seconds.
        # The WorldMapWidget has its own 40 ms timer for smooth aircraft
        # movement within that 15-second month.
        self.timer = QTimer(self)
        self.timer.setInterval(self.MONTH_PLAYBACK_MS)
        self.timer.timeout.connect(self.next_month)

    def choose_trace_color(self):
        """Open the color picker for flight traces."""

        color = QColorDialog.getColor(
            self.map.trace_color,
            self,
            "Choose flight trace color",
        )

        if not color.isValid():
            return

        self.map.set_trace_color(color)
        self.update_trace_color_button()

    def update_trace_color_button(self):
        """Reflect the selected trace color in the button."""

        color = self.map.trace_color

        self.trace_color_button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color.name()};
                color: white;
                border: 1px solid #9ca3af;
                border-radius: 6px;
                padding: 6px 12px;
            }}
            """
        )

    def set_data(self, data):
        self.data = data

        self.year_combo.blockSignals(True)
        self.aircraft_combo.blockSignals(True)

        self.year_combo.clear()
        self.aircraft_combo.clear()

        self.year_combo.addItem("All years", None)

        years = sorted(
            {flight.date.year for flight in data.flights},
            reverse=True,
        )

        for year in years:
            self.year_combo.addItem(str(year), year)

        self.aircraft_combo.addItem("All aircraft", None)

        aircraft_types = sorted(
            {
                FuelDatabase.normalize_type(flight.aircraft)
                for flight in data.flights
                if flight.aircraft
            },
            key=lambda value: str(value).upper(),
        )

        for aircraft in aircraft_types:
            self.aircraft_combo.addItem(aircraft, aircraft)

        # Default to the latest year when possible.
        if years:
            self.year_combo.setCurrentIndex(1)

        self.year_combo.blockSignals(False)
        self.aircraft_combo.blockSignals(False)

        self.month_slider.blockSignals(True)
        self.month_slider.setValue(0)
        self.month_slider.blockSignals(False)

        self.selected_month = 0
        self.map.reset_animation()
        self.map.cumulative_routes = []
        self.map.cumulative_airports = {}

        self.update_month_label()
        self.update_cumulative_routes()
        self.update_map()

    def filters_changed(self):
        if self.timer.isActive():
            self.timer.stop()

        self.map.stop_animation()
        self.play_button.setText("▶ Play")

        self.selected_month = self.month_slider.value()
        self.map.cumulative_routes = []
        self.map.cumulative_airports = {}

        self.update_month_label()
        self.update_cumulative_routes()
        self.update_map()

    def selected_calendar_year(self):
        """Return the year represented by the current year filter."""

        year = self.year_combo.currentData()

        if year is None:
            if self.data is not None and self.data.flights:
                return max(
                    flight.date.year
                    for flight in self.data.flights
                )

            return datetime.now().year

        return year

    def update_month_label(self):
        """Update the visible month label."""

        year = self.selected_calendar_year()

        self.month_label.setText(
            f"{self.MONTHS[self.month_slider.value()]} {year}"
        )

    def month_changed(self, value):
        """Change the selected month."""

        self.selected_month = value

        if hasattr(self, "map"):
            self.map.reset_animation()

        self.update_month_label()
        self.update_cumulative_routes()
        self.update_map()

    def previous_month(self):
        """Select the previous month."""

        value = self.month_slider.value()

        if value > self.month_slider.minimum():
            self.month_slider.setValue(value - 1)

    def next_month(self):
        """Advance to the next month and preserve the completed month."""

        value = self.month_slider.value()

        if value < self.month_slider.maximum():
            # The current month's flights have just completed.
            # Preserve them before switching the selected month.
            if self.timer.isActive():
                for route in self.map.routes:
                    if route not in self.map.cumulative_routes:
                        self.map.cumulative_routes.append(route)

                self.map.cumulative_airports.update(
                    self.map.airports
                )

            self.month_slider.setValue(value + 1)

        elif self.timer.isActive():
            # End of the selected year.
            # Leave December's completed traces visible.
            for route in self.map.routes:
                if route not in self.map.cumulative_routes:
                    self.map.cumulative_routes.append(route)

            self.map.cumulative_airports.update(
                self.map.airports
            )

            self.timer.stop()
            self.map.stop_animation()
            self.play_button.setText("▶ Play")
            self.update()

    def toggle_play(self):
        """Start or pause the 15-second-per-month yearly animation."""

        if self.timer.isActive():
            self.timer.stop()
            self.map.stop_animation()
            self.play_button.setText("▶ Play")
            return

        # Start the selected month. Any months before it remain cumulative.
        self.update_cumulative_routes()
        self.update_map()
        self.map.start_animation()
        self.timer.start()
        self.play_button.setText("Ⅱ Pause")

    def update_cumulative_routes(self):
        """Load all selected flights from months before the selected month."""

        if self.data is None:
            self.map.cumulative_routes = []
            self.map.cumulative_airports = {}
            return

        selected_year = self.selected_calendar_year()
        selected_aircraft = self.aircraft_combo.currentData()
        selected_month = self.month_slider.value() + 1

        flights = []

        for flight in self.data.flights:
            if flight.date.year != selected_year:
                continue

            if flight.date.month >= selected_month:
                continue

            aircraft = FuelDatabase.normalize_type(
                flight.aircraft
            )

            if (
                selected_aircraft is not None
                and aircraft != selected_aircraft
            ):
                continue

            flights.append(flight)

        self.map.set_cumulative_flights(
            flights,
            self.database,
        )

    def update_map(self):
        """Display flights belonging to the selected month."""

        if self.data is None:
            self.map.set_flights([], self.database)
            self.flight_count_label.setText("0 flights")
            return

        selected_year = self.selected_calendar_year()
        selected_aircraft = self.aircraft_combo.currentData()
        selected_month = self.month_slider.value() + 1

        flights = []

        for flight in self.data.flights:
            if flight.date.year != selected_year:
                continue

            if flight.date.month != selected_month:
                continue

            aircraft = FuelDatabase.normalize_type(
                flight.aircraft
            )

            if (
                selected_aircraft is not None
                and aircraft != selected_aircraft
            ):
                continue

            flights.append(flight)

        self.map.set_flights(
            flights,
            self.database,
        )

        self.flight_count_label.setText(
            f"{len(flights):,} flights"
        )


# =========================================================
# PLACEHOLDER PAGE
# =========================================================


class PerformancePage(QWidget):
    """Operational flight-performance statistics."""

    def __init__(self):
        super().__init__()

        self.data = None
        self.selected_year = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 35, 40, 35)
        layout.setSpacing(15)

        title = QLabel("Performance")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Flight-time, distance, speed and route analysis"
        )
        subtitle.setObjectName("pageSubtitle")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # -------------------------------------------------
        # YEAR TABS
        # -------------------------------------------------

        self.year_tabs = QTabWidget()
        self.year_tabs.setObjectName("yearTabs")

        year_bar = self.year_tabs.tabBar()
        year_bar.setUsesScrollButtons(True)
        year_bar.setExpanding(False)

        self.year_tabs.currentChanged.connect(
            self.year_tab_changed
        )

        layout.addWidget(self.year_tabs)

        # -------------------------------------------------
        # KPI CARDS
        # -------------------------------------------------

        cards = QGridLayout()
        cards.setSpacing(12)

        self.flights_card = MetricCard("Flights")
        self.time_card = MetricCard("Flight time")
        self.distance_card = MetricCard("Distance")
        self.average_card = MetricCard("Avg. sector")
        self.speed_card = MetricCard("Avg. speed")
        self.longest_card = MetricCard("Longest sector")

        cards.addWidget(self.flights_card, 0, 0)
        cards.addWidget(self.time_card, 0, 1)
        cards.addWidget(self.distance_card, 0, 2)
        cards.addWidget(self.average_card, 1, 0)
        cards.addWidget(self.speed_card, 1, 1)
        cards.addWidget(self.longest_card, 1, 2)

        layout.addLayout(cards)

        # -------------------------------------------------
        # AIRCRAFT PERFORMANCE
        # -------------------------------------------------

        aircraft_title = QLabel("Aircraft Performance")
        aircraft_title.setObjectName("sectionTitle")
        layout.addWidget(aircraft_title)

        self.aircraft_table = QTableWidget()
        self.aircraft_table.setObjectName("performanceTable")
        self.aircraft_table.setColumnCount(7)
        self.aircraft_table.setHorizontalHeaderLabels(
            [
                "Aircraft",
                "Flights",
                "Flight Time",
                "Distance",
                "Avg. Sector",
                "Avg. Speed",
                "Longest",
            ]
        )
        self._configure_table(self.aircraft_table)
        layout.addWidget(self.aircraft_table, 1)

        # -------------------------------------------------
        # ROUTE PERFORMANCE
        # -------------------------------------------------

        route_title = QLabel("Route Performance")
        route_title.setObjectName("sectionTitle")
        layout.addWidget(route_title)

        self.route_table = QTableWidget()
        self.route_table.setObjectName("performanceTable")
        self.route_table.setColumnCount(7)
        self.route_table.setHorizontalHeaderLabels(
            [
                "Route",
                "Flights",
                "Flight Time",
                "Avg. Sector",
                "Avg. Distance",
                "Avg. Speed",
                "Longest",
            ]
        )
        self._configure_table(self.route_table)
        layout.addWidget(self.route_table, 2)

    def _configure_table(self, table):
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)

        header = table.horizontalHeader()
        header.setStretchLastSection(True)

        for column in range(table.columnCount()):
            header.setSectionResizeMode(
                column,
                QHeaderView.ResizeToContents,
            )

    def set_data(self, data):
        """Load shared FlightStats data."""
        self.data = data
        self.build_year_tabs()

    def build_year_tabs(self):
        """Build ALL plus one tab for each flight year."""
        self.year_tabs.blockSignals(True)
        self.year_tabs.clear()

        if self.data is None:
            self.year_tabs.blockSignals(False)
            return

        years = sorted(
            {
                flight.date.year
                for flight in self.data.flights
            },
            reverse=True,
        )

        self.year_tabs.addTab(QWidget(), "ALL")

        for year in years:
            self.year_tabs.addTab(
                QWidget(),
                str(year),
            )

        self.selected_year = None
        self.year_tabs.blockSignals(False)
        self.year_tabs.setCurrentIndex(0)
        self.update_page()

    def year_tab_changed(self, index):
        """Update performance statistics for the selected year."""
        if self.data is None or index < 0:
            return

        text = self.year_tabs.tabText(index)

        self.selected_year = (
            None
            if text == "ALL"
            else int(text)
        )

        self.update_page()

    def _selected_flights(self):
        if self.data is None:
            return []

        return [
            (index, flight)
            for index, flight in enumerate(self.data.flights)
            if (
                self.selected_year is None
                or flight.date.year == self.selected_year
            )
        ]

    def _distance_for(self, index):
        if (
            index >= len(self.data.flight_distances)
        ):
            return None

        result = self.data.flight_distances[index]

        if not isinstance(result, dict):
            return None

        return result.get("distance_km")

    def _flight_metrics(self, index, flight):
        minutes = flight.flight_minutes or 0
        distance = self._distance_for(index)

        speed = None
        if distance is not None and minutes > 0:
            speed = distance / minutes * 60

        return minutes, distance, speed

    def update_page(self):
        """Calculate and display performance statistics."""
        if self.data is None:
            return

        selected = self._selected_flights()

        total_flights = len(selected)
        total_minutes = 0
        total_distance = 0.0
        distance_count = 0
        speed_total = 0.0
        speed_count = 0
        longest = None

        for index, flight in selected:
            minutes, distance, speed = self._flight_metrics(
                index,
                flight,
            )

            total_minutes += minutes

            if distance is not None:
                total_distance += distance
                distance_count += 1

            if speed is not None:
                speed_total += speed
                speed_count += 1

            if minutes > 0:
                longest = (
                    minutes
                    if longest is None
                    else max(longest, minutes)
                )

        average_minutes = (
            total_minutes / total_flights
            if total_flights
            else 0
        )

        average_speed = (
            speed_total / speed_count
            if speed_count
            else None
        )

        self.flights_card.set_value(
            f"{total_flights:,}"
        )
        self.time_card.set_value(
            format_hours(total_minutes)
        )
        self.distance_card.set_value(
            f"{total_distance:,.1f} km"
            if distance_count
            else "—"
        )
        self.average_card.set_value(
            format_hours(round(average_minutes))
            if total_flights
            else "—"
        )
        self.speed_card.set_value(
            f"{average_speed:,.1f} km/h"
            if average_speed is not None
            else "—"
        )
        self.longest_card.set_value(
            format_hours(longest)
            if longest is not None
            else "—"
        )

        self._update_aircraft_table(selected, total_flights)
        self._update_route_table(selected)

    def _update_aircraft_table(self, selected, total_flights):
        """Build aircraft-level operational performance."""
        database = FuelDatabase()
        stats = {}

        for index, flight in selected:
            aircraft = database.normalize_type(
                flight.aircraft
            )

            item = stats.setdefault(
                aircraft,
                {
                    "flights": 0,
                    "minutes": 0,
                    "distance": 0.0,
                    "distance_count": 0,
                    "speed_total": 0.0,
                    "speed_count": 0,
                    "longest": None,
                },
            )

            minutes, distance, speed = self._flight_metrics(
                index,
                flight,
            )

            item["flights"] += 1
            item["minutes"] += minutes

            if distance is not None:
                item["distance"] += distance
                item["distance_count"] += 1

            if speed is not None:
                item["speed_total"] += speed
                item["speed_count"] += 1

            if minutes > 0:
                item["longest"] = (
                    minutes
                    if item["longest"] is None
                    else max(item["longest"], minutes)
                )

        self.aircraft_table.setSortingEnabled(False)
        self.aircraft_table.setRowCount(len(stats))

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
            flights = item["flights"]

            average_minutes = (
                item["minutes"] / flights
                if flights
                else 0
            )

            average_speed = (
                item["speed_total"]
                / item["speed_count"]
                if item["speed_count"]
                else None
            )

            values = [
                (aircraft, aircraft),
                (f"{flights:,}", flights),
                (
                    format_hours(item["minutes"]),
                    item["minutes"],
                ),
                (
                    (
                        f'{item["distance"]:,.1f} km'
                        if item["distance_count"]
                        else "—"
                    ),
                    item["distance"],
                ),
                (
                    format_hours(round(average_minutes)),
                    average_minutes,
                ),
                (
                    (
                        f"{average_speed:,.1f} km/h"
                        if average_speed is not None
                        else "—"
                    ),
                    average_speed,
                ),
                (
                    (
                        format_hours(item["longest"])
                        if item["longest"] is not None
                        else "—"
                    ),
                    item["longest"] or 0,
                ),
            ]

            for column, (value, sort_value) in enumerate(values):
                self.set_item(
                    self.aircraft_table,
                    row,
                    column,
                    value,
                    sort_value,
                )

        self.aircraft_table.setSortingEnabled(True)

    def _update_route_table(self, selected):
        """Build route-level operational performance."""
        routes = {}

        for index, flight in selected:
            route = (
                f"{flight.departure} → {flight.arrival}"
            )

            item = routes.setdefault(
                route,
                {
                    "flights": 0,
                    "minutes": 0,
                    "distance": 0.0,
                    "distance_count": 0,
                    "speed_total": 0.0,
                    "speed_count": 0,
                    "longest": None,
                },
            )

            minutes, distance, speed = self._flight_metrics(
                index,
                flight,
            )

            item["flights"] += 1
            item["minutes"] += minutes

            if distance is not None:
                item["distance"] += distance
                item["distance_count"] += 1

            if speed is not None:
                item["speed_total"] += speed
                item["speed_count"] += 1

            if minutes > 0:
                item["longest"] = (
                    minutes
                    if item["longest"] is None
                    else max(item["longest"], minutes)
                )

        self.route_table.setSortingEnabled(False)
        self.route_table.setRowCount(len(routes))

        for row, route in enumerate(
            sorted(
                routes,
                key=lambda name: (
                    -routes[name]["flights"],
                    name,
                ),
            )
        ):
            item = routes[route]
            flights = item["flights"]

            average_minutes = (
                item["minutes"] / flights
                if flights
                else 0
            )

            average_distance = (
                item["distance"]
                / item["distance_count"]
                if item["distance_count"]
                else None
            )

            average_speed = (
                item["speed_total"]
                / item["speed_count"]
                if item["speed_count"]
                else None
            )

            values = [
                (route, route),
                (f"{flights:,}", flights),
                (
                    format_hours(item["minutes"]),
                    item["minutes"],
                ),
                (
                    format_hours(round(average_minutes)),
                    average_minutes,
                ),
                (
                    (
                        f"{average_distance:,.1f} km"
                        if average_distance is not None
                        else "—"
                    ),
                    average_distance,
                ),
                (
                    (
                        f"{average_speed:,.1f} km/h"
                        if average_speed is not None
                        else "—"
                    ),
                    average_speed,
                ),
                (
                    (
                        format_hours(item["longest"])
                        if item["longest"] is not None
                        else "—"
                    ),
                    item["longest"] or 0,
                ),
            ]

            for column, (value, sort_value) in enumerate(values):
                self.set_item(
                    self.route_table,
                    row,
                    column,
                    value,
                    sort_value,
                )

        self.route_table.setSortingEnabled(True)

    def set_item(
        self,
        table,
        row,
        column,
        text,
        sort_value=None,
    ):
        item = SortableTableWidgetItem(
            text,
            sort_value,
        )
        table.setItem(
            row,
            column,
            item,
        )


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

        # -------------------------------------------------
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
            FuelPage()
        )

        self.map_page = (
            MapPage()
        )

        self.performance_page = (
            PerformancePage()
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
            self.map_page
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
            ("Map", 5),
            ("Performance", 6),
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

        # -------------------------------------------------
        # RESPONSIVE WINDOW SIZE
        # -------------------------------------------------
        # Apply the final window geometry after all pages,
        # layouts and widgets have been constructed.

        screen = QApplication.primaryScreen()
        available = screen.availableGeometry()

        width = min(
            int(available.width() * 0.90),
            1800,
        )

        height = min(
            int(available.height() * 0.90),
            1100,
        )

        width = min(
            max(width, 1100),
            available.width(),
        )

        height = min(
            max(height, 700),
            available.height(),
        )

        self.resize(
            width,
            height,
        )

        # Center the window within the usable screen area.
        frame = self.frameGeometry()
        frame.moveCenter(
            available.center()
        )
        self.move(
            frame.topLeft()
        )

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
            "Logbook files (*.pdf *.csv)",
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
            or path.suffix.lower() not in {".pdf", ".csv"}
        ):
            QMessageBox.warning(
                self,
                "Invalid Logbook",
                "Please select a valid PDF or CSV logbook.",
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

        self.fuel_page.set_data(
            self.data
        )

        self.map_page.set_data(
            self.data
        )

        self.performance_page.set_data(
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

        #performanceTable {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            gridline-color: #eef0f2;
            selection-background-color: #e5e7eb;
            selection-color: #111827;
        }

        #performanceTable QHeaderView::section {
            background: #f9fafb;
            color: #4b5563;
            border: none;
            border-bottom: 1px solid #e5e7eb;
            padding: 10px 8px;
            font-size: 12px;
            font-weight: 600;
        }

        #performanceTable QTableWidgetItem {
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

    # -------------------------------------------------
    # DARK MODE SUPPORT
    # -------------------------------------------------
    # macOS can switch between Light and Dark appearance.
    # The base stylesheet defines the FlightStats light theme.
    # When Qt reports a dark system palette, apply a general
    # dark-mode layer so all Qt controls remain readable.

    if app.palette().window().color().lightness() < 128:
        app.setStyleSheet(
            app.styleSheet()
            + """

            /* ---------------------------------------------
               APPLICATION BACKGROUND
               --------------------------------------------- */

            QMainWindow {
                background: #111827;
            }

            QWidget {
                color: #f9fafb;
            }

            #content {
                background: #111827;
            }

            /* ---------------------------------------------
               TEXT
               --------------------------------------------- */

            QLabel {
                color: #f9fafb;
            }

            #pageTitle,
            #sectionTitle {
                color: #f9fafb;
            }

            #pageSubtitle,
            #statusLabel,
            #cardLabel,
            #aircraftCount {
                color: #9ca3af;
            }

            #aircraftName {
                color: #f9fafb;
            }

            #aircraftTime {
                color: #d1d5db;
            }

            #cardValue {
                color: #f9fafb;
            }

            #logbookStatusLabel,
            #versionLabel {
                color: #9ca3af;
            }

            /* ---------------------------------------------
               CARDS
               --------------------------------------------- */

            #card {
                background: #1f2937;
                border: 1px solid #374151;
            }

            /* ---------------------------------------------
               TEXT INPUTS
               --------------------------------------------- */

            QLineEdit {
                background: #1f2937;
                color: #f9fafb;
                border: 1px solid #4b5563;
            }

            QLineEdit:focus {
                border: 1px solid #9ca3af;
            }

            QLineEdit:disabled {
                background: #374151;
                color: #9ca3af;
            }

            QLineEdit::placeholder {
                color: #9ca3af;
            }

            #searchBox,
            #filterBox {
                background: #1f2937;
                color: #f9fafb;
                border: 1px solid #4b5563;
            }

            /* ---------------------------------------------
               COMBO BOXES
               --------------------------------------------- */

            QComboBox {
                background: #1f2937;
                color: #f9fafb;
                border: 1px solid #4b5563;
            }

            QComboBox:hover {
                border: 1px solid #6b7280;
            }

            QComboBox:focus {
                border: 1px solid #9ca3af;
            }

            QComboBox:disabled {
                background: #374151;
                color: #9ca3af;
                border-color: #4b5563;
            }

            QComboBox QAbstractItemView {
                background: #1f2937;
                color: #f9fafb;
                selection-background-color: #374151;
                selection-color: #ffffff;
                border: 1px solid #4b5563;
            }

            /* ---------------------------------------------
               BUTTONS
               --------------------------------------------- */

            QPushButton {
                color: #f9fafb;
            }

            QPushButton:disabled {
                color: #9ca3af;
            }

            #refreshButton {
                color: #ffffff;
            }

            #navigationButton {
                color: #d1d5db;
            }

            #navigationButton:hover,
            #navigationButton:pressed {
                color: #ffffff;
            }

            /* ---------------------------------------------
               TABLES
               --------------------------------------------- */

            QTableWidget {
                background: #1f2937;
                color: #f9fafb;
                alternate-background-color: #1f2937;
                border: 1px solid #4b5563;
                gridline-color: #9ca3af;
                selection-background-color: #4b5563;
                selection-color: #ffffff;
            }

            QTableWidget::item {
                color: #f9fafb;
                background: #1f2937;
            }

            QTableWidget::item:selected {
                color: #ffffff;
                background: #4b5563;
            }

            QHeaderView::section {
                background: #111827;
                color: #f9fafb;
                border: 1px solid #4b5563;
                border-bottom: 1px solid #9ca3af;
            }

            /* Explicitly cover all current application tables.
               This also preserves their existing object-specific
               styling while guaranteeing dark-mode readability. */

            #logbookTable,
            #aircraftTable,
            #airportsTable,
            #performanceTable,
            #fuelTable,
            #fuelYearTable {
                background: #1f2937;
                color: #f9fafb;
                gridline-color: #9ca3af;
            }

            #logbookTable::item,
            #aircraftTable::item,
            #airportsTable::item,
            #performanceTable::item,
            #fuelTable::item,
            #fuelYearTable::item {
                color: #f9fafb;
                background: #1f2937;
            }

            #logbookTable QHeaderView::section,
            #aircraftTable QHeaderView::section,
            #airportsTable QHeaderView::section,
            #performanceTable QHeaderView::section,
            #fuelTable QHeaderView::section,
            #fuelYearTable QHeaderView::section {
                background: #111827;
                color: #f9fafb;
                border: 1px solid #4b5563;
                border-bottom: 1px solid #9ca3af;
            }

            /* ---------------------------------------------
               TABS
               --------------------------------------------- */

            QTabBar::tab {
                color: #d1d5db;
            }

            QTabBar::tab:selected {
                color: #ffffff;
            }

            #yearTabs QTabBar::tab {
                background: #1f2937;
                border-color: #374151;
                color: #d1d5db;
            }

            #yearTabs QTabBar::tab:hover,
            #yearTabs QTabBar::tab:selected {
                background: #374151;
                color: #ffffff;
                border-color: #4b5563;
            }

            /* ---------------------------------------------
               LOGBOOK DROP ZONE
               --------------------------------------------- */

            #logbookDropZone {
                background: #1f2937;
                border-color: #4b5563;
            }

            #logbookDropTitle,
            #logbookDropIcon {
                color: #f9fafb;
            }

            #logbookDropSubtitle {
                color: #9ca3af;
            }

            /* ---------------------------------------------
               PROGRESS BAR
               --------------------------------------------- */

            #progressBar {
                background: #374151;
            }

            /* ---------------------------------------------
               SCROLLBARS
               --------------------------------------------- */

            QScrollBar:vertical {
                background: #1f2937;
                width: 12px;
                margin: 0;
            }

            QScrollBar::handle:vertical {
                background: #6b7280;
                min-height: 30px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical:hover {
                background: #9ca3af;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: #1f2937;
                border: none;
                height: 0;
            }

            QScrollBar:horizontal {
                background: #1f2937;
                height: 12px;
                margin: 0;
            }

            QScrollBar::handle:horizontal {
                background: #6b7280;
                min-width: 30px;
                border-radius: 6px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #9ca3af;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                background: #1f2937;
                border: none;
                width: 0;
            }

            /* ---------------------------------------------
               TOOLTIP
               --------------------------------------------- */

            QToolTip {
                background: #1f2937;
                color: #f9fafb;
                border: 1px solid #4b5563;
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
