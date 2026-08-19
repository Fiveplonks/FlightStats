"""Flight map page for FlightStats."""

from datetime import datetime

from PySide6.QtCore import (
    QTimer,
    Qt,
)

from PySide6.QtGui import QColor

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from gui_world_map import WorldMapWidget

from parser.airports import AirportDatabase
from parser.fuel import FuelDatabase


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
        """Display current and cumulative flights in one map update."""

        if self.data is None:
            self.map.set_map_data(
                [],
                [],
                self.database,
            )
            self.flight_count_label.setText("0 flights")
            return

        selected_year = self.selected_calendar_year()
        selected_aircraft = self.aircraft_combo.currentData()
        selected_month = self.month_slider.value() + 1

        flights = []
        cumulative_flights = []

        for flight in self.data.flights:
            if flight.date.year != selected_year:
                continue

            aircraft = FuelDatabase.normalize_type(
                flight.aircraft
            )

            if (
                selected_aircraft is not None
                and aircraft != selected_aircraft
            ):
                continue

            if flight.date.month == selected_month:
                flights.append(flight)

            elif flight.date.month < selected_month:
                cumulative_flights.append(flight)

        self.map.set_map_data(
            flights,
            cumulative_flights,
            self.database,
        )

        self.flight_count_label.setText(
            f"{len(flights):,} flights"
        )
