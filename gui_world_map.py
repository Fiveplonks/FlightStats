"""World map widget for FlightStats."""

import json

from PySide6.QtCore import (
    QUrl,
    Qt,
)

from PySide6.QtGui import QColor

from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from PySide6.QtWebEngineWidgets import QWebEngineView


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

