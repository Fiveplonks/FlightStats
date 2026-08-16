"""Aircraft statistics page for FlightStats."""

from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gui_components import SortableTableWidgetItem

from gui_utils import (
    display_fuel_unit,
    format_hours,
)

from parser.fuel import FuelDatabase
from parser.aircraft import AircraftResolver


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

        from parser.aircraft import AircraftResolver

        aircraft_resolver = AircraftResolver()

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

                        # Local flights (departure == arrival) do not
                        # provide a meaningful airport-to-airport
                        # distance, so exclude them from average speed.
                        resolution = (
                            aircraft_resolver.resolve(
                                flight.aircraft
                            )
                        )

                        if (
                            resolution.category
                            != "general_aviation"
                            and flight.flight_minutes
                            and flight.departure
                            != flight.arrival
                            and distance > 0
                        ):
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

