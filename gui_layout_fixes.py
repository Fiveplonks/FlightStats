"""Runtime layout safeguards for the cross-platform FlightStats dashboard."""

from PySide6.QtCore import QTimer, QSize
from PySide6.QtWidgets import QSizePolicy, QApplication


def apply_dashboard_layout_fixes():
    """Apply stable sizing safeguards before the main window is created."""
    from gui_dashboard import DashboardPage
    from gui_components import MetricCard
    from gui import MainWindow

    if getattr(DashboardPage, "_layout_fixes_applied", False):
        return

    # -------------------------------------------------------------
    # Metric cards
    # -------------------------------------------------------------
    # The split-flap board changes its width whenever the displayed value
    # changes (for example km -> NM). If that width contributes to the
    # card's sizeHint, Qt/macOS can resize the top-level window every time
    # a value changes. Give the card a stable sizeHint instead.
    def metric_size_hint(self):
        return QSize(320, 105)

    def metric_minimum_size_hint(self):
        return QSize(0, 105)

    MetricCard.sizeHint = metric_size_hint
    MetricCard.minimumSizeHint = metric_minimum_size_hint

    # -------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------
    original_dashboard_init = DashboardPage.__init__
    original_year_tab_changed = DashboardPage.year_tab_changed

    def patched_dashboard_init(self):
        original_dashboard_init(self)

        # The split-flap cards need enough vertical room for their title,
        # margins and 34px flap labels. Keep their height stable so the
        # numbers can never be vertically clipped.
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
            card.setMinimumHeight(105)
            card.setMaximumHeight(105)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Keep the graph footprint predictable. Career Stats has been
        # removed, so the graph can use the space directly below the KPI
        # cards without squeezing them.
        self.graph_frame.setMinimumHeight(255)
        self.graph_frame.setMaximumHeight(275)
        self.flight_time_chart.setMinimumHeight(210)
        self.flight_time_chart.setMaximumHeight(230)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(0, 0)

    def patched_year_tab_changed(self, index):
        window = self.window()
        preserve_geometry = (
            not window.isMaximized()
            and not window.isFullScreen()
        )
        previous_geometry = window.geometry() if preserve_geometry else None

        original_year_tab_changed(self, index)

        if preserve_geometry and previous_geometry is not None:
            # Qt/macOS may recalculate the top-level geometry after a tab
            # changes the page's size hint. Restore the complete geometry,
            # not only the size, on the next event-loop turn.
            QTimer.singleShot(
                0,
                lambda: window.setGeometry(previous_geometry),
            )

    DashboardPage.__init__ = patched_dashboard_init
    DashboardPage.year_tab_changed = patched_year_tab_changed
    DashboardPage._layout_fixes_applied = True

    # -------------------------------------------------------------
    # Main window
    # -------------------------------------------------------------
    original_main_window_init = MainWindow.__init__

    def patched_main_window_init(self):
        original_main_window_init(self)

        # Every page must be allowed to shrink to the size of the window.
        # Otherwise switching pages can increase QStackedWidget's minimum
        # size and cause QMainWindow to grow unexpectedly.
        pages = (
            self.dashboard_page,
            self.logbook_page,
            self.aircraft_page,
            self.airports_page,
            self.fuel_page,
            self.map_page,
            self.performance_page,
        )
        for page in pages:
            page.setMinimumSize(0, 0)
            page.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pages.setMinimumSize(0, 0)
        self.pages.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.centralWidget().setMinimumSize(0, 0)

        # Start using the entire usable screen area. QScreen.availableGeometry
        # excludes reserved areas such as the macOS Dock/menu area.
        screen = QApplication.primaryScreen()
        if screen is not None:
            available = screen.availableGeometry()
            self.setGeometry(available)

            # Re-apply once after the window has been shown/layouted. This
            # prevents macOS/Qt from replacing the requested geometry with a
            # sizeHint-derived geometry during startup.
            QTimer.singleShot(
                0,
                lambda: self.setGeometry(available),
            )

    MainWindow.__init__ = patched_main_window_init
    MainWindow._layout_fixes_applied = True
