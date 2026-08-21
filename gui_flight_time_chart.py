"""Reusable FlightStats flight-time chart widget."""

from calendar import monthrange
from datetime import date

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QPainter, QPen
from PySide6.QtWidgets import QFileDialog, QPushButton, QVBoxLayout, QWidget

from gui_utils import format_hours


class FlightTimeChart(QWidget):
    """Cumulative or aggregated flight-time chart with PNG export."""

    def __init__(self, parent=None, export_title="FlightStats Flight Time"):
        super().__init__(parent)
        self.points = []
        self.export_title = export_title
        self.setMinimumHeight(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.export_button = QPushButton("Export graph as image")
        self.export_button.setObjectName("refreshButton")
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.clicked.connect(self.export_image)
        layout.addWidget(self.export_button, 0, Qt.AlignRight)

    def set_points(self, points):
        """Set chart points as ``[(date, value_minutes), ...]``."""
        self.points = list(points or [])
        self.update()

    def clear(self):
        self.set_points([])

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.palette().base())

        if not self.points:
            painter.setPen(self.palette().text().color())
            painter.drawText(self.rect(), Qt.AlignCenter, "No flight-time data available")
            return

        rect = self.rect().adjusted(58, 38, -18, -36)
        values = [point[1] for point in self.points]
        total = max(values)
        span = max(total, 1)

        # Use familiar 500-hour increments on the Y-axis. The selected
        # range's exact cumulative total is shown only at the top.
        total_hours = total / 60
        tick_hours = list(range(0, int(total_hours) + 1, 500))
        if not tick_hours:
            tick_hours = [0]
        if tick_hours[-1] * 60 != total:
            tick_hours.append(total_hours)

        grid_pen = QPen(self.palette().mid().color())
        grid_pen.setStyle(Qt.DotLine)
        grid_pen.setWidth(1)
        text_pen = QPen(self.palette().text().color())

        painter.setPen(text_pen)
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)

        for hours in tick_hours:
            minutes = hours * 60
            ratio = minutes / span
            y = rect.bottom() - ratio * rect.height()
            painter.setPen(grid_pen)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            painter.setPen(text_pen)

            if minutes == total:
                label = format_hours(int(minutes))
            else:
                label = f"{int(hours):,}"

            painter.drawText(
                QRectF(0, y - 10, 52, 20),
                Qt.AlignRight | Qt.AlignVCenter,
                label,
            )

        if len(self.points) == 1:
            x_values = [rect.center().x()]
        else:
            x_values = [
                rect.left() + index * rect.width() / (len(self.points) - 1)
                for index in range(len(self.points))
            ]

        def y_for(value):
            return rect.bottom() - (value / span) * rect.height()

        line_pen = QPen(self.palette().highlight().color())
        line_pen.setWidth(3)
        painter.setPen(line_pen)

        previous = None
        for x, (_, value) in zip(x_values, self.points):
            point = QPointF(x, y_for(value))
            if previous is not None:
                painter.drawLine(previous, point)
            previous = point

        painter.setBrush(QBrush(self.palette().highlight().color()))
        painter.setPen(Qt.NoPen)
        for x, (_, value) in zip(x_values, self.points):
            painter.drawEllipse(QPointF(x, y_for(value)), 3.5, 3.5)

        painter.setPen(text_pen)
        for index, label in enumerate(self._x_labels()):
            if label is None:
                continue
            x = x_values[index]
            painter.drawText(
                QRectF(x - 30, rect.bottom() + 8, 60, 24),
                Qt.AlignHCenter | Qt.AlignTop,
                label,
            )

        painter.drawText(
            QRectF(rect.left(), 18, rect.width(), 20),
            Qt.AlignLeft | Qt.AlignVCenter,
            f"{format_hours(values[-1])} total",
        )

    def _x_labels(self):
        """Return sparse year labels for the annual dashboard series."""
        if not self.points:
            return []
        count = len(self.points)
        target = 8
        step = max(1, (count - 1) // (target - 1))
        labels = [None] * count
        for index, (point_date, _) in enumerate(self.points):
            if index == 0 or index == count - 1 or index % step == 0:
                labels[index] = point_date.strftime("%Y")
        return labels

    def export_image(self):
        if not self.points:
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Flight Time Graph",
            "FlightStats_Total_Flying_Hours.png",
            "PNG image (*.png)",
        )
        if not path:
            return

        source = self.grab()
        image = source.scaled(1400, 760, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        image.save(path, "PNG")


def monthly_cumulative_flight_time(flights):
    """Aggregate flight time by calendar month and return cumulative points."""
    monthly = {}

    for flight in flights:
        if flight.date is None or not flight.flight_minutes:
            continue
        key = (flight.date.year, flight.date.month)
        monthly[key] = monthly.get(key, 0) + flight.flight_minutes

    if not monthly:
        return []

    first_year, first_month = min(monthly)
    last_year, last_month = max(monthly)

    points = []
    year, month = first_year, first_month
    cumulative = 0

    while (year, month) <= (last_year, last_month):
        cumulative += monthly.get((year, month), 0)
        points.append((date(year, month, monthrange(year, month)[1]), cumulative))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return points


def annual_cumulative_flight_time(flights, through_year=None):
    """Return one cumulative flight-time point per calendar year.

    When ``through_year`` is supplied, the series stops at that year while
    retaining all preceding years. This makes the Dashboard year selector
    behave as a cumulative career-time cutoff rather than a single-year filter.
    """
    annual = {}

    for flight in flights:
        if flight.date is None or not flight.flight_minutes:
            continue
        year = flight.date.year
        if through_year is not None and year > through_year:
            continue
        annual[year] = annual.get(year, 0) + flight.flight_minutes

    if not annual:
        return []

    first_year = min(annual)
    last_year = max(annual)
    points = []
    cumulative = 0

    for year in range(first_year, last_year + 1):
        cumulative += annual.get(year, 0)
        points.append((date(year, 12, 31), cumulative))

    return points
