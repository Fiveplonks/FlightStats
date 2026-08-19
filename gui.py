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
)
from PySide6.QtGui import QColor, QIcon

from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSlider,
    QStackedWidget,
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
from gui_map import MapPage
from gui_performance import PerformancePage
from gui_world_map import WorldMapWidget
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


LOGBOOK = get_logbook_path()


def find_unresolved_fuel_aircraft(fuel_results, database):
    """Return unresolved aircraft grouped by normalized identity."""

    unresolved = {}

    for result in fuel_results:
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

    return unresolved


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






# =========================================================
# PLACEHOLDER PAGE
# =========================================================




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

        buttons = [
            ("Dashboard", 0),
            ("Logbook", 1),
            ("Aircraft", 2),
            ("Airports", 3),
            ("Fuel", 4),
            ("Map", 5),
            ("Performance", 6),
        ]

        navigation_group = QButtonGroup(
            self
        )

        navigation_group.setExclusive(
            True
        )

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

            button.setCheckable(
                True
            )

            navigation_group.addButton(
                button,
                index,
            )

            button.clicked.connect(
                lambda checked=False,
                i=index: self.switch_page(i)
            )

            sidebar_layout.addWidget(
                button
            )

            if index == 0:
                button.setChecked(
                    True
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
        """Switch pages immediately without a transition effect."""

        if index == self.pages.currentIndex():
            return

        self.pages.setCurrentIndex(
            index
        )


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

        unresolved = find_unresolved_fuel_aircraft(
            self.data.fuel_results,
            database,
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

        self.data.refresh_fuel()

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

    # -------------------------------------------------
    # APPLICATION ICON
    # -------------------------------------------------
    # PyInstaller embeds the Windows icon into the EXE,
    # but Qt needs its own application icon for the
    # window title bar and taskbar.
    if sys.platform == "win32":
        icon_path = (
            Path(__file__).resolve().parent
            / "FlightStats.ico"
        )
    else:
        icon_path = (
            Path(__file__).resolve().parent
            / "FlightStats.icns"
        )

    if icon_path.exists():
        app.setWindowIcon(
            QIcon(str(icon_path))
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
