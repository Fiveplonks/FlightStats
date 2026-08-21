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

    def metric_size_hint(self):
        return QSize(320, 96)

    def metric_minimum_size_hint(self):
        return QSize(0, 88)

    MetricCard.sizeHint = metric_size_hint
    MetricCard.minimumSizeHint = metric_minimum_size_hint

    original_dashboard_init = DashboardPage.__init__
    original_year_tab_changed = DashboardPage.year_tab_changed

    def patched_dashboard_init(self):
        original_dashboard_init(self)

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
            card.setMinimumHeight(88)
            card.setMaximumHeight(105)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.graph_frame.setMinimumHeight(220)
        self.graph_frame.setMaximumHeight(275)
        self.flight_time_chart.setMinimumHeight(180)
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
            QTimer.singleShot(
                0,
                lambda: window.setGeometry(previous_geometry),
            )

    DashboardPage.__init__ = patched_dashboard_init
    DashboardPage.year_tab_changed = patched_year_tab_changed
    DashboardPage._layout_fixes_applied = True

    original_main_window_init = MainWindow.__init__
    original_switch_page = MainWindow.switch_page

    def patched_main_window_init(self):
        original_main_window_init(self)

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

        screen = QApplication.primaryScreen()
        self._startup_available_geometry = (
            screen.availableGeometry() if screen is not None else None
        )

        if self._startup_available_geometry is not None:
            available = self._startup_available_geometry
            self.setGeometry(available)
            self.setMaximumSize(available.size())
            QTimer.singleShot(
                0,
                lambda: self.setGeometry(available),
            )

    def patched_switch_page(self, index):
        """Switch pages without allowing page size hints to resize the window."""
        if index == self.pages.currentIndex():
            return

        preserve_geometry = (
            not self.isMaximized()
            and not self.isFullScreen()
        )
        previous_geometry = self.geometry() if preserve_geometry else None

        original_switch_page(self, index)

        if previous_geometry is not None:
            # Changing the stacked page can cause Qt to recalculate the
            # top-level window size from the new page's size hint. Restore
            # the user's chosen geometry after that layout pass. This is
            # particularly important on macOS, where the available screen
            # geometry excludes the Dock.
            QTimer.singleShot(
                0,
                lambda: self.setGeometry(previous_geometry),
            )
            QTimer.singleShot(
                50,
                lambda: self.setGeometry(previous_geometry),
            )

    MainWindow.__init__ = patched_main_window_init
    MainWindow.switch_page = patched_switch_page
    MainWindow._layout_fixes_applied = True
