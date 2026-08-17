"""Logbook page for FlightStats."""

from PySide6.QtWidgets import (
    QComboBox,
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

from gui_utils import (
    display_fuel_unit,
    format_hours,
)

from parser.fuel import FuelDatabase


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
                flight.date,
            )

            self.set_item(
                row,
                1,
                flight.departure,
            )

            departure_time = (
                flight.departure_time
            )

            departure_sort = (
                departure_time.hour * 60
                + departure_time.minute
                if departure_time
                else None
            )

            self.set_item(
                row,
                2,
                departure_time.strftime(
                    "%H:%M"
                )
                if departure_time
                else "—",
                departure_sort,
            )

            self.set_item(
                row,
                3,
                flight.arrival,
            )

            arrival_time = (
                flight.arrival_time
            )

            arrival_sort = (
                arrival_time.hour * 60
                + arrival_time.minute
                if arrival_time
                else None
            )

            self.set_item(
                row,
                4,
                arrival_time.strftime(
                    "%H:%M"
                )
                if arrival_time
                else "—",
                arrival_sort,
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
                flight.flight_minutes,
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
                distance,
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
                fuel,
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
        """Set table item with optional sorting value."""

        item = SortableTableWidgetItem(
            str(text),
            sort_value,
        )

        self.table.setItem(
            row,
            column,
            item,
        )

