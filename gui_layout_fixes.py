"""Runtime layout safeguards for the cross-platform FlightStats dashboard."""

from PySide6.QtCore import QTimer, QSize
from PySide6.QtWidgets import QSizePolicy


def apply_dashboard_layout_fixes():
    """Apply dashboard sizing safeguards before the main window is created."""
    from gui_dashboard import DashboardPage

    if getattr(DashboardPage, "_layout_fixes_applied", False):
        return

    original_init = DashboardPage.__init__
    original_year_tab_changed = DashboardPage.year_tab_changed

    def patched_init(self):
        original_init(self)

        # Keep KPI cards readable when the dashboard also contains the graph.
        for card in (
            self.flights_card,
            self.time_card,
            self.previous_experience_card,
            self.validated_logbook_card,
            self.total_experience_card,
            self.distance_card,
            self.jet_fuel_card,
            self.piston_fuel_card,
            self.airports_card,
        ):
            card.setMinimumHeight(82)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Give the graph a predictable footprint so it cannot consume the
        # vertical space required by the KPI cards and career summary.
        self.graph_frame.setMinimumHeight(255)
        self.graph_frame.setMaximumHeight(275)
        self.flight_time_chart.setMinimumHeight(210)
        self.flight_time_chart.setMaximumHeight(230)

        # The Dashboard itself should expand with the application window,
        # rather than changing its size hint when a year tab is selected.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def patched_year_tab_changed(self, index):
        window = self.window()
        preserve_geometry = (
            not window.isMaximized()
            and not window.isFullScreen()
        )
        previous_size = window.size() if preserve_geometry else QSize()

        original_year_tab_changed(self, index)

        if preserve_geometry:
            # Qt/macOS can recalculate the top-level size from the changed
            # dashboard size hint. Restore the user's window size after the
            # layout pass has completed.
            QTimer.singleShot(
                0,
                lambda: window.resize(previous_size),
            )

    DashboardPage.__init__ = patched_init
    DashboardPage.year_tab_changed = patched_year_tab_changed
    DashboardPage._layout_fixes_applied = True
