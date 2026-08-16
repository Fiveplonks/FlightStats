import sys
import json
import random
from pathlib import Path
from datetime import datetime, timedelta

from PySide6.QtCore import (
    Qt,
    QThread,
    Signal,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtGui import QColor

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSlider,
    QStackedWidget,
    QGraphicsOpacityEffect,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
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
from gui_components import (
    LogbookDropZone,
    MetricCard,
    SortableTableWidgetItem,
)
from gui_aircraft import AircraftPage
from gui_airports import AirportsPage
from gui_fuel import FuelPage
from gui_dashboard import DashboardPage
from gui_logbook import LogbookPage
from gui_data_loader import DataLoaderWorker
from gui_utils import (
    display_fuel_unit,
    format_hours,
    load_home_bases,
    save_home_bases,
)
from gui_fuel_dialog import show_missing_fuel_profile_dialog
from gui_discrepancy_dialog import show_discrepancies
from gui_style import apply_style
from parser.airports import AirportDatabase
from parser.fuel import FuelDatabase
from parser.fuel_analysis import calculate_all_fuel, summarize_fuel


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






# =========================================================
# METRIC CARD
# =========================================================





# =========================================================
# DASHBOARD
# =========================================================













# =========================================================
# AIRCRAFT PAGE
# =========================================================




# =========================================================
# AIRPORTS PAGE
# =========================================================


# =========================================================
# USER SETTINGS
# =========================================================






# =========================================================
# FUEL PAGE
# =========================================================



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

function fitRouteBounds() {
    const bounds = L.latLngBounds([]);

    const routes = [
        ...cumulativeRoutes,
        ...currentRoutes
    ];

    for (const route of routes) {
        const points = routePoints(route);

        if (!points) continue;

        for (const point of points) {
            bounds.extend(point);
        }
    }

    // If there are no routes, keep the existing world view.
    if (!bounds.isValid()) {
        setViewWorld();
        return;
    }

    map.fitBounds(
        bounds,
        {
            padding: [40, 40],
            maxZoom: 7,
            animate: false
        }
    );

    // Give the default view three additional zoom levels of context.
    const fittedZoom = map.getZoom();

    if (fittedZoom > 3) {
        map.setZoom(fittedZoom - 3, {
            animate: false
        });
    }
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

    fitRouteBounds();

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

    if (points.length === 1) {
        return {
            lat: points[0][0],
            lon: points[0][1],
            angle: 0
        };
    }

    const scaled = t * (points.length - 1);
    const index = Math.min(
        points.length - 2,
        Math.floor(scaled)
    );
    const local = scaled - index;

    const a = points[index];
    const b = points[index + 1];

    const lat = a[0] + (b[0] - a[0]) * local;
    const lon = a[1] + (b[1] - a[1]) * local;

    // Calculate the geographic bearing from point A to point B.
    //
    // The aircraft SVG points north/up at rotation 0 degrees,
    // so the geographic bearing can be used directly as the
    // SVG rotation angle.
    const lat1 = a[0] * Math.PI / 180;
    const lat2 = b[0] * Math.PI / 180;
    const deltaLon = (b[1] - a[1]) * Math.PI / 180;

    const y = Math.sin(deltaLon) * Math.cos(lat2);

    const x =
        Math.cos(lat1) * Math.sin(lat2) -
        Math.sin(lat1) * Math.cos(lat2) *
        Math.cos(deltaLon);

    let angle = Math.atan2(y, x) * 180 / Math.PI;

    // Normalize to 0..360 degrees.
    angle = (angle + 360) % 360;

    return {
        lat,
        lon,
        angle
    };
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

        from parser.aircraft import AircraftResolver

        aircraft_resolver = AircraftResolver()

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

            resolution = aircraft_resolver.resolve(
                flight.aircraft
            )

            # General-aviation training flights often operate
            # non-directly between nearby airports. Their
            # airport-to-airport distance therefore does not
            # represent a meaningful cruise/air speed.
            #
            # Keep their flight time and distance statistics,
            # but exclude them from average-speed calculation.
            if (
                resolution.category != "general_aviation"
                and speed is not None
            ):
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

        # -------------------------------------------------
        # PAGE TRANSITIONS
        # -------------------------------------------------
        #
        # Apply opacity effects to the individual Qt pages
        # rather than to the QStackedWidget itself.
        #
        # The Map page contains QWebEngineView and must remain
        # free of graphics effects because WebEngine uses its
        # own composited rendering surface.
        # -------------------------------------------------

        self.page_effects = {}

        for page in (
            self.dashboard_page,
            self.logbook_page,
            self.aircraft_page,
            self.airports_page,
            self.performance_page,
        ):
            effect = QGraphicsOpacityEffect(
                page
            )

            effect.setOpacity(
                1.0
            )

            page.setGraphicsEffect(
                effect
            )

            self.page_effects[page] = effect

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
                i=index: self.switch_page(i)
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

    def switch_page(
        self,
        index,
    ):
        """Switch pages with a short fade-in transition."""

        current_index = self.pages.currentIndex()

        if index == current_index:
            return

        current_page = self.pages.widget(
            current_index
        )

        target_page = self.pages.widget(
            index
        )

        # -------------------------------------------------
        # MAP PAGE
        # -------------------------------------------------
        #
        # QWebEngineView uses a native composited rendering
        # surface. Do not combine it with page opacity
        # transitions in either direction.
        #
        # This means:
        #
        #   Map -> normal page   = immediate switch
        #   normal page -> Map   = immediate switch
        #
        # Normal Qt pages retain the fade transition below.
        # -------------------------------------------------

        if (
            current_page is self.map_page
            or target_page is self.map_page
            or current_page is self.fuel_page
            or target_page is self.fuel_page
        ):
            if hasattr(
                self,
                "_page_effect_animation",
            ):
                self._page_effect_animation.stop()

            self.pages.setCurrentIndex(
                index
            )

            return

        effect = self.page_effects.get(
            target_page
        )

        self.pages.setCurrentIndex(
            index
        )

        if effect is None:
            return

        if hasattr(
            self,
            "_page_effect_animation",
        ):
            self._page_effect_animation.stop()

        self._page_effect_animation = (
            QPropertyAnimation(
                effect,
                b"opacity",
                self,
            )
        )

        self._page_effect_animation.setDuration(
            180
        )

        self._page_effect_animation.setEasingCurve(
            QEasingCurve.OutCubic
        )

        effect.setOpacity(
            0.0
        )

        self._page_effect_animation.setStartValue(
            0.0
        )

        self._page_effect_animation.setEndValue(
            1.0
        )

        self._page_effect_animation.start()

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

    def request_missing_fuel_profile(
        self,
        aircraft_type,
    ):
        """Ask the user for a fuel profile for an unresolved aircraft."""

        database = FuelDatabase()

        diagnosis = database.diagnose_resolution(
            aircraft_type
        )

        profile = show_missing_fuel_profile_dialog(
            self,
            aircraft_type,
            diagnosis,
        )

        if profile is None:
            return False

        database.add(
            aircraft_type=aircraft_type,
            average_burn=profile["average_burn"],
            unit=profile["unit"],
            method="User supplied",
            source="User",
            notes=profile["notes"],
        )

        return True


    def resolve_missing_fuel_profiles(
        self,
    ):
        """Ask for fuel profiles for all unresolved aircraft types."""

        if self.data is None:
            return False

        # -------------------------------------------------
        # GROUP BY RESOLVED AIRCRAFT IDENTITY
        # -------------------------------------------------
        #
        # Multiple logbook representations can refer to the
        # same aircraft:
        #
        #   789 / 787-9 / 787-900 / B787-9
        #       -> B787-9
        #
        #   8200 / 737-8200 / B38M
        #       -> B737-8200
        #
        # Ask the user only once for each actual aircraft
        # identity.
        #
        database = FuelDatabase()

        unresolved = {}

        for result in self.data.fuel_results:

            if result.get("fuel") is not None:
                continue

            flight = result.get("flight")

            if flight is None or not flight.aircraft:
                continue

            raw_type = flight.aircraft

            normalized_type = database.normalize_type(
                raw_type
            )

            if not normalized_type:
                normalized_type = raw_type

            unresolved.setdefault(
                normalized_type,
                raw_type,
            )

        if not unresolved:
            return False

        changed = False

        for normalized_type in sorted(
            unresolved,
            key=str.upper,
        ):
            # Use the stable FlightStats aircraft name in
            # the dialog whenever possible.
            aircraft_type = normalized_type

            if self.request_missing_fuel_profile(
                aircraft_type
            ):
                changed = True

        if not changed:
            return False

        # -------------------------------------------------
        # RECALCULATE FUEL
        # -------------------------------------------------

        database = FuelDatabase()

        self.data.fuel_database = database

        self.data.fuel_results = (
            calculate_all_fuel(
                self.data.flights,
                database,
            )
        )

        self.data.fuel_summary = (
            summarize_fuel(
                self.data.fuel_results
            )
        )

        return True

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

        # -------------------------------------------------
        # MISSING FUEL PROFILES
        # -------------------------------------------------
        #
        # Data loading happens in a worker thread, so the
        # dialog is deliberately opened here, after the
        # finished signal has returned execution to the GUI
        # thread.
        #
        if self.resolve_missing_fuel_profiles():

            # Refresh every page that displays fuel data.
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

            self.fuel_page.set_data(
                self.data
            )

            self.performance_page.set_data(
                self.data
            )

        show_discrepancies(
            self,
            getattr(
                self.data,
                "discrepancies",
                [],
            ),
            format_hours,
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

    def closeEvent(self, event):
        """Stop background loading before closing the application."""

        thread = self.loader_thread

        if (
            thread is not None
            and thread.isRunning()
        ):
            thread.quit()
            thread.wait()

        event.accept()

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
