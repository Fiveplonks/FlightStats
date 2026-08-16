"""Airport statistics page for FlightStats."""

from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from gui_components import SortableTableWidgetItem

from gui_utils import (
    format_hours,
    load_home_bases,
    save_home_bases,
)

from parser.airports import AirportDatabase


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

        self.home_base_list.itemDoubleClicked.connect(
            self.remove_home_base
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

    def captain_identity(self, captain):
        """
        Return a normalized identity key for Captain comparisons.

        EASA logbooks may represent the same person's name in
        different orders, for example:

            SCHOLLAERT Michel
            Michel Schollaert

        The original Captain value is preserved. This normalized
        value is used only to determine duty continuity.
        """

        if not captain:
            return None

        parts = (
            str(captain)
            .strip()
            .casefold()
            .split()
        )

        if not parts:
            return None

        return tuple(sorted(parts))


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

            # A layover/turnaround is considered part of the same
            # duty only when the Captain remains the same.
            #
            # Missing Captain information is deliberately treated
            # as unknown rather than assuming duty continuity.
            if (
                not flight.captain
                or not next_flight.captain
                or self.captain_identity(flight.captain)
                != self.captain_identity(next_flight.captain)
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

