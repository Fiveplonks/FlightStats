"""Operational performance page for FlightStats."""

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

from gui_utils import format_hours

from parser.fuel import FuelDatabase


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

        self.year_tabs = QTabWidget()
        self.year_tabs.setObjectName("yearTabs")

        year_bar = self.year_tabs.tabBar()
        year_bar.setUsesScrollButtons(True)
        year_bar.setExpanding(False)

        self.year_tabs.currentChanged.connect(self.year_tab_changed)
        layout.addWidget(self.year_tabs)

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
                "Distance",
                "Avg. Speed",
                "Longest",
            ]
        )
        self._configure_table(self.route_table)
        layout.addWidget(self.route_table, 1)

    def _configure_table(self, table):
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.verticalHeader().setVisible(False)

        header = table.horizontalHeader()
        proportions = [1.30, 0.75, 1.10, 1.25, 1.10, 1.15, 0.95]
        total = sum(proportions)

        for column, proportion in enumerate(proportions):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
            header.resizeSection(column, int(1000 * proportion / total))

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
            {flight.date.year for flight in self.data.flights},
            reverse=True,
        )

        self.year_tabs.addTab(QWidget(), "ALL")

        for year in years:
            self.year_tabs.addTab(QWidget(), str(year))

        self.selected_year = None
        self.year_tabs.blockSignals(False)
        self.year_tabs.setCurrentIndex(0)
        self.update_page()

    def year_tab_changed(self, index):
        """Update performance statistics for the selected year."""
        if self.data is None or index < 0:
            return

        text = self.year_tabs.tabText(index)
        self.selected_year = None if text == "ALL" else int(text)
        self.update_page()

    def _selected_flights(self):
        if self.data is None:
            return []

        return [
            (index, flight)
            for index, flight in enumerate(self.data.flights)
            if self.selected_year is None or flight.date.year == self.selected_year
        ]

    def _distance_for(self, index):
        if index >= len(self.data.flight_distances):
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
            minutes, distance, speed = self._flight_metrics(index, flight)
            total_minutes += minutes

            if distance is not None:
                total_distance += distance
                distance_count += 1

            if speed is not None:
                speed_total += speed
                speed_count += 1

            if minutes > 0:
                longest = minutes if longest is None else max(longest, minutes)

        average_minutes = total_minutes / total_flights if total_flights else 0
        average_speed = speed_total / speed_count if speed_count else None

        self.flights_card.set_value(f"{total_flights:,}")
        self.time_card.set_value(format_hours(total_minutes))
        self.distance_card.set_value(
            f"{total_distance:,.1f} km" if distance_count else "—"
        )
        self.average_card.set_value(
            format_hours(round(average_minutes)) if total_flights else "—"
        )
        self.speed_card.set_value(
            f"{average_speed:,.1f} km/h" if average_speed is not None else "—"
        )
        self.longest_card.set_value(
            format_hours(longest) if longest is not None else "—"
        )

        self._update_aircraft_table(selected, total_flights)
        self._update_route_table(selected)

    def _update_aircraft_table(self, selected, total_flights):
        """Build aircraft-level operational performance."""
        database = FuelDatabase()

        from parser.aircraft import AircraftResolver

        aircraft_resolver = AircraftResolver()
        stats = {}

        for index, flight in selected:
            aircraft = database.normalize_type(flight.aircraft)

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

            minutes, distance, speed = self._flight_metrics(index, flight)
            item["flights"] += 1
            item["minutes"] += minutes

            if distance is not None:
                item["distance"] += distance
                item["distance_count"] += 1

            resolution = aircraft_resolver.resolve(flight.aircraft)
            if resolution.category != "general_aviation" and speed is not None:
                item["speed_total"] += speed
                item["speed_count"] += 1

            if minutes > 0:
                item["longest"] = (
                    minutes if item["longest"] is None
                    else max(item["longest"], minutes)
                )

        self.aircraft_table.setSortingEnabled(False)
        self.aircraft_table.setRowCount(len(stats))

        for row, aircraft in enumerate(
            sorted(stats, key=lambda name: (-stats[name]["flights"], name))
        ):
            item = stats[aircraft]
            flights = item["flights"]
            average_minutes = item["minutes"] / flights if flights else 0
            average_speed = (
                item["speed_total"] / item["speed_count"]
                if item["speed_count"] else None
            )

            values = [
                (aircraft, aircraft),
                (f"{flights:,}", flights),
                (format_hours(item["minutes"]), item["minutes"]),
                (
                    f'{item["distance"]:,.1f} km' if item["distance_count"] else "—",
                    item["distance"],
                ),
                (format_hours(round(average_minutes)), average_minutes),
                (
                    f"{average_speed:,.1f} km/h" if average_speed is not None else "—",
                    average_speed,
                ),
                (
                    format_hours(item["longest"]) if item["longest"] is not None else "—",
                    item["longest"] or 0,
                ),
            ]

            for column, (value, sort_value) in enumerate(values):
                self.set_item(self.aircraft_table, row, column, value, sort_value)

        self.aircraft_table.setSortingEnabled(True)

    def _update_route_table(self, selected):
        """Build route-level operational performance."""
        routes = {}

        for index, flight in selected:
            route = f"{flight.departure} → {flight.arrival}"
            item = routes.setdefault(
                route,
                {
                    "flights": 0,
                    "minutes": 0,
                    "distance": None,
                    "speed_total": 0.0,
                    "speed_count": 0,
                    "longest": None,
                },
            )

            minutes, distance, speed = self._flight_metrics(index, flight)
            item["flights"] += 1
            item["minutes"] += minutes

            # Coordinate-derived distance is a property of the route,
            # so display it once instead of averaging identical route entries.
            if item["distance"] is None and distance is not None:
                item["distance"] = distance

            if speed is not None:
                item["speed_total"] += speed
                item["speed_count"] += 1

            if minutes > 0:
                item["longest"] = (
                    minutes if item["longest"] is None
                    else max(item["longest"], minutes)
                )

        self.route_table.setSortingEnabled(False)
        self.route_table.setRowCount(len(routes))

        for row, route in enumerate(
            sorted(routes, key=lambda name: (-routes[name]["flights"], name))
        ):
            item = routes[route]
            flights = item["flights"]
            average_minutes = item["minutes"] / flights if flights else 0
            average_speed = (
                item["speed_total"] / item["speed_count"]
                if item["speed_count"] else None
            )

            values = [
                (route, route),
                (f"{flights:,}", flights),
                (format_hours(item["minutes"]), item["minutes"]),
                (format_hours(round(average_minutes)), average_minutes),
                (
                    f'{item["distance"]:,.1f} km' if item["distance"] is not None else "—",
                    item["distance"] if item["distance"] is not None else 0,
                ),
                (
                    f"{average_speed:,.1f} km/h" if average_speed is not None else "—",
                    average_speed,
                ),
                (
                    format_hours(item["longest"]) if item["longest"] is not None else "—",
                    item["longest"] or 0,
                ),
            ]

            for column, (value, sort_value) in enumerate(values):
                self.set_item(self.route_table, row, column, value, sort_value)

        self.route_table.setSortingEnabled(True)

    def set_item(self, table, row, column, text, sort_value=None):
        item = SortableTableWidgetItem(text, sort_value)
        table.setItem(row, column, item)
