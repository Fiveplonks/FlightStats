"""Fuel statistics page for FlightStats."""

from PySide6.QtWidgets import (
    QGridLayout,
    QHeaderView,
    QLabel,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from gui_components import (
    MetricCard,
    SortableTableWidgetItem,
)

from gui_utils import (
    display_fuel_unit,
    format_hours,
)

from parser.fuel import FuelDatabase


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

