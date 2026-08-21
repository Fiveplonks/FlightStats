"""Logbook page for FlightStats."""

from calendar import monthrange
from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from gui_components import SortableTableWidgetItem
from gui_flight_time_chart import FlightTimeChart, monthly_cumulative_flight_time
from gui_units import UnitSettings, format_distance, format_fuel_quantity
from gui_utils import format_hours
from parser.fuel import FuelDatabase


class LogbookPage(QWidget):
    """Searchable, sortable and analytically filterable logbook."""

    def __init__(self):
        super().__init__()
        self.data = None
        self.selected_year = None
        self.database = FuelDatabase()
        self.units = UnitSettings()
        self._table_populated = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 35, 40, 35)
        layout.setSpacing(15)

        title = QLabel("Logbook")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Browse and analyse your flight history")
        subtitle.setObjectName("pageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.year_tabs = QTabWidget()
        self.year_tabs.setObjectName("yearTabs")
        year_bar = self.year_tabs.tabBar()
        year_bar.setUsesScrollButtons(True)
        year_bar.setExpanding(False)
        self.year_tabs.currentChanged.connect(self.year_tab_changed)
        layout.addWidget(self.year_tabs)

        filter_bar = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search date, airport, aircraft, registration...")
        self.search_box.setObjectName("searchBox")
        filter_bar.addWidget(self.search_box, 1)

        self.aircraft_filter = QComboBox()
        self.aircraft_filter.setObjectName("filterBox")
        self.aircraft_filter.addItem("All aircraft")
        filter_bar.addWidget(self.aircraft_filter)
        layout.addLayout(filter_bar)

        analysis_frame = QWidget()
        analysis_layout = QGridLayout(analysis_frame)
        analysis_layout.setContentsMargins(0, 0, 0, 0)
        analysis_layout.setHorizontalSpacing(10)
        analysis_layout.setVerticalSpacing(6)

        analysis_layout.addWidget(QLabel("From"), 0, 0)
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd-MM-yyyy")
        analysis_layout.addWidget(self.start_date, 0, 1)

        analysis_layout.addWidget(QLabel("To"), 0, 2)
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd-MM-yyyy")
        analysis_layout.addWidget(self.end_date, 0, 3)

        analysis_layout.addWidget(QLabel("Chart"), 0, 4)
        self.analysis_metric = QComboBox()
        self.analysis_metric.addItems(("Cumulative flight time", "Monthly flight time"))
        analysis_layout.addWidget(self.analysis_metric, 0, 5)

        self.analysis_total_label = QLabel("Selected flight time: —")
        self.analysis_total_label.setObjectName("statusLabel")
        analysis_layout.addWidget(self.analysis_total_label, 1, 0, 1, 4)

        self.analysis_chart = FlightTimeChart(export_title="FlightStats Logbook Analysis")
        analysis_layout.addWidget(self.analysis_chart, 1, 4, 1, 2)
        layout.addWidget(analysis_frame)

        self.result_label = QLabel("0 flights")
        self.result_label.setObjectName("statusLabel")
        layout.addWidget(self.result_label)

        self.table = QTableWidget()
        self.table.setObjectName("logbookTable")
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "Date", "Departure", "Dep.", "Arrival", "Arr.",
            "Aircraft", "Registration", "Flight Time", "Distance", "Fuel",
        ])
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        widths = (95, 85, 60, 85, 60, 105, 105, 90, 110, 110)
        for column, width in enumerate(widths):
            header.setSectionResizeMode(column, QHeaderView.Fixed)
            header.resizeSection(column, width)
        layout.addWidget(self.table, 1)

        self.search_box.textChanged.connect(self.apply_filters)
        self.aircraft_filter.currentTextChanged.connect(self.apply_filters)
        self.start_date.dateChanged.connect(self.apply_filters)
        self.end_date.dateChanged.connect(self.apply_filters)
        self.analysis_metric.currentTextChanged.connect(self.update_analysis)

    def showEvent(self, event):
        """Refresh presentation units without rebuilding the 1500+ row table."""
        self.units.load()
        super().showEvent(event)
        # set_data() already builds the table. Rebuilding it every time the
        # page becomes visible makes navigation unnecessarily expensive.

    def set_data(self, data):
        self.data = data
        self.units.load()
        self._table_populated = False

        self.aircraft_filter.blockSignals(True)
        self.aircraft_filter.clear()
        self.aircraft_filter.addItem("All aircraft")
        aircraft_types = {
            self.database.normalize_type(flight.aircraft)
            for flight in data.flights
        }
        for aircraft in sorted(aircraft_types):
            if aircraft:
                self.aircraft_filter.addItem(aircraft)
        self.aircraft_filter.blockSignals(False)
        self.build_year_tabs()

    def set_units(self):
        self.units.load()
        self.apply_filters()

    def build_year_tabs(self):
        self.year_tabs.blockSignals(True)
        self.year_tabs.clear()
        years = sorted({flight.date.year for flight in self.data.flights}, reverse=True)
        self.year_tabs.addTab(QWidget(), "ALL")
        for year in years:
            self.year_tabs.addTab(QWidget(), str(year))
        self.selected_year = None
        self.year_tabs.blockSignals(False)
        self.year_tabs.setCurrentIndex(0)
        self._set_date_bounds()
        self.apply_filters()

    def _set_date_bounds(self):
        dates = [flight.date for flight in self.data.flights if flight.date]
        if not dates:
            return
        minimum = min(dates)
        maximum = max(dates)
        minimum_qdate = QDate(minimum.year, minimum.month, minimum.day)
        maximum_qdate = QDate(maximum.year, maximum.month, maximum.day)
        self.start_date.setMinimumDate(minimum_qdate)
        self.start_date.setMaximumDate(maximum_qdate)
        self.end_date.setMinimumDate(minimum_qdate)
        self.end_date.setMaximumDate(maximum_qdate)
        self.start_date.setDate(minimum_qdate)
        self.end_date.setDate(maximum_qdate)

    def year_tab_changed(self, index):
        if self.data is None or index < 0:
            return
        text = self.year_tabs.tabText(index)
        self.selected_year = None if text == "ALL" else int(text)

        if self.selected_year is not None:
            all_dates = [flight.date for flight in self.data.flights if flight.date]
            minimum = min(all_dates)
            maximum = max(all_dates)
            start = max(date(self.selected_year, 1, 1), minimum)
            end = min(date(self.selected_year, 12, 31), maximum)
            self.start_date.setDate(QDate(start.year, start.month, start.day))
            self.end_date.setDate(QDate(end.year, end.month, end.day))
        else:
            self._set_date_bounds()
        self.apply_filters()

    def _date_range(self):
        return self.start_date.date().toPython(), self.end_date.date().toPython()

    def _matches(self, flight):
        if self.selected_year is not None and flight.date.year != self.selected_year:
            return False

        start_date, end_date = self._date_range()
        if flight.date < start_date or flight.date > end_date:
            return False

        selected_aircraft = self.aircraft_filter.currentText()
        aircraft = self.database.normalize_type(flight.aircraft)
        if selected_aircraft != "All aircraft" and aircraft != selected_aircraft:
            return False

        search_text = self.search_box.text().strip().lower()
        searchable = " ".join([
            str(flight.date), flight.departure, flight.arrival,
            aircraft or "", flight.registration,
        ]).lower()
        return not search_text or search_text in searchable

    def apply_filters(self):
        if self.data is None:
            return

        matches = [
            (index, flight)
            for index, flight in enumerate(self.data.flights)
            if self._matches(flight)
        ]
        self.populate_table(matches)
        self.result_label.setText(f"{len(matches):,} flights")
        self.update_analysis([flight for _, flight in matches])

    def update_analysis(self, flights=None):
        if self.data is None:
            return
        if flights is None:
            flights = [flight for flight in self.data.flights if self._matches(flight)]

        total_minutes = sum(flight.flight_minutes or 0 for flight in flights)
        self.analysis_total_label.setText(f"Selected flight time: {format_hours(total_minutes)}")

        if self.analysis_metric.currentText() == "Monthly flight time":
            points = self._monthly_totals(flights)
        else:
            points = monthly_cumulative_flight_time(flights)
        self.analysis_chart.set_points(points)

    @staticmethod
    def _monthly_totals(flights):
        monthly = {}
        for flight in flights:
            if flight.date is None or not flight.flight_minutes:
                continue
            key = (flight.date.year, flight.date.month)
            monthly[key] = monthly.get(key, 0) + flight.flight_minutes
        if not monthly:
            return []

        return [
            (date(year, month, monthrange(year, month)[1]), minutes)
            for (year, month), minutes in sorted(monthly.items())
        ]

    def populate_table(self, matches):
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)
        try:
            self.table.clearContents()
            self.table.setRowCount(len(matches))

            for row, (original_index, flight) in enumerate(matches):
                distance_result = self.data.flight_distances[original_index]
                distance = distance_result.get("distance_km") if isinstance(distance_result, dict) else None
                fuel_result = self.data.fuel_results[original_index]
                fuel = fuel_result.get("fuel") if isinstance(fuel_result, dict) else None
                fuel_unit = fuel_result.get("unit") if isinstance(fuel_result, dict) else None

                self.set_item(row, 0, flight.date.strftime("%d-%m-%Y"), flight.date)
                self.set_item(row, 1, flight.departure)

                departure_time = flight.departure_time
                departure_sort = (
                    departure_time.hour * 60 + departure_time.minute
                    if departure_time else None
                )
                self.set_item(
                    row, 2,
                    departure_time.strftime("%H:%M") if departure_time else "—",
                    departure_sort,
                )

                self.set_item(row, 3, flight.arrival)
                arrival_time = flight.arrival_time
                arrival_sort = (
                    arrival_time.hour * 60 + arrival_time.minute
                    if arrival_time else None
                )
                self.set_item(
                    row, 4,
                    arrival_time.strftime("%H:%M") if arrival_time else "—",
                    arrival_sort,
                )

                aircraft = self.database.normalize_type(flight.aircraft)
                self.set_item(row, 5, aircraft)
                self.set_item(row, 6, flight.registration)
                self.set_item(row, 7, format_hours(flight.flight_minutes), flight.flight_minutes)
                self.set_item(row, 8, format_distance(distance, self.units.distance_unit), distance)
                self.set_item(
                    row, 9,
                    format_fuel_quantity(fuel, fuel_unit, self.units.fuel_unit),
                    fuel,
                )
        finally:
            self.table.setUpdatesEnabled(True)
            self.table.setSortingEnabled(True)
        self._table_populated = True

    def set_item(self, row, column, text, sort_value=None):
        item = SortableTableWidgetItem(str(text), sort_value)
        self.table.setItem(row, column, item)
