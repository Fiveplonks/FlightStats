"""FlightStats application styling."""


def apply_style(app):
    """Apply FlightStats visual style."""

    app.setStyleSheet(
        """
        QMainWindow {
            background: #f4f6f8;
        }

        QWidget {
            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;

            color: #1f2937;
        }

        #sidebar {
            background: #111827;
        }

        #logo {
            color: white;
            font-size: 22px;
            font-weight: 700;
            padding-left: 10px;
        }

        #navigationButton {
            background: transparent;
            color: #d1d5db;
            border: none;
            border-radius: 8px;
            padding: 12px 15px;
            text-align: left;
            font-size: 14px;
        }

        #navigationButton:hover {
            background: #1f2937;
            color: white;
        }

        #navigationButton:pressed {
            background: #374151;
        }

        #content {
            background: #f4f6f8;
        }

        #pageTitle {
            font-size: 30px;
            font-weight: 700;
            color: #111827;
        }

        #pageSubtitle {
            font-size: 15px;
            color: #6b7280;
        }

        #sectionTitle {
            font-size: 20px;
            font-weight: 700;
            color: #111827;
        }

        #card {
            background: white;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
        }

        #cardLabel {
            color: #6b7280;
            font-size: 13px;
        }

        #cardValue {
            color: #111827;
            font-size: 26px;
            font-weight: 700;
        }

        #refreshButton {
            background: #111827;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
        }

        #refreshButton:hover {
            background: #1f2937;
        }

        #refreshButton:pressed {
            background: #374151;
        }

        #refreshButton:disabled {
            background: #9ca3af;
        }

        #statusLabel {
            color: #6b7280;
            font-size: 12px;
        }

        #progressBar {
            height: 8px;
            border: none;
            border-radius: 4px;
            background: #e5e7eb;
        }

        #progressBar::chunk {
            border-radius: 4px;
            background: #111827;
        }

        #loadingFrame {
            background: transparent;
        }

        #aircraftName {
            font-size: 14px;
            font-weight: 600;
        }

        #aircraftCount {
            color: #6b7280;
            font-size: 13px;
        }

        #aircraftTime {
            color: #374151;
            font-size: 13px;
            font-weight: 600;
            min-width: 70px;
        }

        #searchBox {
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 10px 12px;
            font-size: 13px;
        }

        #searchBox:focus {
            border: 1px solid #6b7280;
        }

        #filterBox {
            background: white;
            border: 1px solid #d1d5db;
            border-radius: 8px;
            padding: 8px 12px;
            min-width: 150px;
        }

        #logbookTable {
            background: #ffffff;
            border: 1px solid #dbe1e8;
            border-radius: 10px;
            gridline-color: #edf1f5;
            selection-background-color: #e8edf3;
            selection-color: #0f172a;
            alternate-background-color: #f8fafc;
        }

        #logbookTable QHeaderView::section {
            background: #eef2f6;
            color: #334155;
            border: none;
            border-bottom: 1px solid #d6dde6;
            padding: 11px 9px;
            font-size: 11px;
            font-weight: 750;
        }

        #logbookTable QTableWidgetItem {
            padding: 9px;
        }

        #logbookTable::item:hover {
            background: #f1f5f9;
        }

        /* ---------------------------------------------
           AIRCRAFT OPERATIONS PANEL
           --------------------------------------------- */

        #aircraftTable {
            background: white;
            border: 1px solid #dbe1e8;
            border-radius: 12px;
            gridline-color: #eef1f4;
            selection-background-color: #e8edf3;
            selection-color: #111827;
            alternate-background-color: #f8fafc;
        }

        #aircraftTable QHeaderView {
            background: #111827;
        }

        #aircraftTable QHeaderView::section {
            background: #111827;
            color: #f9fafb;
            border: none;
            border-right: 1px solid #293241;
            padding: 11px 10px;
            font-size: 12px;
            font-weight: 700;
        }

        #aircraftTable QHeaderView::section:last {
            border-right: none;
        }

        #aircraftTable QTableWidgetItem {
            padding: 9px 10px;
        }

        #aircraftName {
            color: #111827;
            font-size: 14px;
            font-weight: 700;
        }

        #aircraftCount {
            color: #6b7280;
            font-size: 13px;
            font-weight: 500;
        }

        #aircraftTime {
            color: #111827;
            font-size: 13px;
            font-weight: 700;
            min-width: 70px;
        }

        #performanceTable {
            background: #ffffff;
            border: 1px solid #dbe1e8;
            border-radius: 10px;
            gridline-color: #edf1f5;
            selection-background-color: #e8edf3;
            selection-color: #0f172a;
            alternate-background-color: #f8fafc;
        }

        #performanceTable QHeaderView::section {
            background: #eef2f6;
            color: #334155;
            border: none;
            border-bottom: 1px solid #d6dde6;
            padding: 11px 9px;
            font-size: 11px;
            font-weight: 750;
        }

        #performanceTable QTableWidgetItem {
            padding: 9px;
        }

        #performanceTable::item:hover {
            background: #f1f5f9;
        }

        #homeBaseList {
            background: transparent;
            border: none;
            padding: 0;
        }

        #homeBaseList::item {
            background: #111827;
            color: white;
            border-radius: 7px;
            padding: 7px 12px;
            margin-right: 5px;
            font-weight: 600;
        }

        #homeBaseList::item:selected {
            background: #374151;
        }

        #airportsTable {
            background: #ffffff;
            border: 1px solid #dbe1e8;
            border-radius: 10px;
            gridline-color: #edf1f5;
            selection-background-color: #e8edf3;
            selection-color: #0f172a;
            alternate-background-color: #f8fafc;
        }

        #airportsTable QHeaderView::section {
            background: #eef2f6;
            color: #334155;
            border: none;
            border-bottom: 1px solid #d6dde6;
            padding: 11px 9px;
            font-size: 11px;
            font-weight: 750;
        }

        #airportsTable QTableWidgetItem {
            padding: 9px;
        }

        #airportsTable::item:hover {
            background: #f1f5f9;
        }

        /* ---------------------------------------------
           PHASE 1 DASHBOARD POLISH
           --------------------------------------------- */

        #pageTitle {
            font-size: 32px;
            font-weight: 750;
            letter-spacing: -0.5px;
            color: #0f172a;
        }

        #pageSubtitle {
            font-size: 15px;
            color: #64748b;
        }

        #sidebar {
            background: #0f172a;
        }

        #logo {
            color: #f8fafc;
            font-size: 22px;
            font-weight: 750;
            padding-left: 10px;
        }

        #navigationButton {
            background: transparent;
            color: #94a3b8;
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 11px 15px;
            text-align: left;
            font-size: 14px;
            font-weight: 550;
        }

        #navigationButton:hover {
            background: #1e293b;
            color: #f8fafc;
            border-color: #334155;
        }

        #navigationButton:pressed {
            background: #334155;
            color: #ffffff;
        }

        #content {
            background: #f4f6f8;
        }

        #card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
        }

        #cardLabel {
            color: #64748b;
            font-size: 14px;
            font-weight: 550;
        }

        /* ---------------------------------------------
           YEAR / LOGBOOK HISTORY SELECTOR
           --------------------------------------------- */

        #yearTabs {
            background: transparent;
            border: none;
        }

        #yearTabs::pane {
            border: none;
            background: transparent;
        }

        #yearTabs QTabBar {
            background: transparent;
        }

        #yearTabs QTabBar::tab {
            background: #ffffff;
            color: #64748b;
            border: 1px solid #dbe1e8;
            border-radius: 7px;
            padding: 8px 17px;
            margin-right: 5px;
            min-width: 54px;
            font-size: 13px;
            font-weight: 600;
        }

        #yearTabs QTabBar::tab:hover {
            background: #f1f5f9;
            border-color: #94a3b8;
            color: #334155;
        }

        #yearTabs QTabBar::tab:selected {
            background: #475569;
            border-color: #475569;
            color: #ffffff;
            font-weight: 750;
        }

        #yearTabs QTabBar::tab:selected:hover {
            background: #334155;
            border-color: #334155;
            color: #ffffff;
        }

        #yearTabs QTabBar::tab {
            min-height: 18px;
        }

        #yearTabs QTabBar::tab:first {
            margin-left: 0px;
        }

        #yearTabs QTabBar::tab:selected {
            padding-left: 19px;
            padding-right: 19px;
        }

        #yearTabs QTabBar::tab:pressed {
            background: #334155;
            border-color: #334155;
            color: #ffffff;
        }

        #logbookDropZone {
            background: white;
            border: 2px dashed #d1d5db;
            border-radius: 14px;
            min-height: 210px;
        }

        #logbookDropZone:hover {
            border: 2px dashed #6b7280;
            background: #f9fafb;
        }

        #logbookDropZone[dragActive="true"] {
            border: 2px dashed #111827;
            background: #f3f4f6;
        }

        #logbookDropIcon {
            color: #374151;
            font-size: 30px;
            font-weight: 700;
        }

        #logbookDropTitle {
            color: #111827;
            font-size: 20px;
            font-weight: 700;
        }

        #logbookDropSubtitle {
            color: #6b7280;
            font-size: 13px;
        }

        #logbookBrowseButton {
            background: #111827;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 13px;
            font-weight: 600;
        }

        #logbookBrowseButton:hover {
            background: #1f2937;
        }

        #logbookBrowseButton:pressed {
            background: #374151;
        }

        #logbookStatusLabel {
            color: #6b7280;
            font-size: 12px;
        }

        #versionLabel {
            color: #6b7280;
            font-size: 11px;
            padding-left: 10px;
        }
        """
    )

    # -------------------------------------------------
    # DARK MODE SUPPORT
    # -------------------------------------------------
    # macOS can switch between Light and Dark appearance.
    # The base stylesheet defines the FlightStats light theme.
    # When Qt reports a dark system palette, apply a general
    # dark-mode layer so all Qt controls remain readable.

    if app.palette().window().color().lightness() < 128:
        app.setStyleSheet(
            app.styleSheet()
            + """

            /* ---------------------------------------------
               APPLICATION BACKGROUND
               --------------------------------------------- */

            QMainWindow {
                background: #111827;
            }

            QWidget {
                color: #f9fafb;
            }

            #content {
                background: #111827;
            }

            /* ---------------------------------------------
               TEXT
               --------------------------------------------- */

            QLabel {
                color: #f9fafb;
            }

            #pageTitle,
            #sectionTitle {
                color: #f9fafb;
            }

            #pageSubtitle,
            #statusLabel,
            #cardLabel,
            #aircraftCount {
                color: #9ca3af;
            }

            #aircraftName {
                color: #f9fafb;
            }

            #aircraftTime {
                color: #d1d5db;
            }

            #cardValue {
                color: #f9fafb;
            }

            #logbookStatusLabel,
            #versionLabel {
                color: #9ca3af;
            }

            /* ---------------------------------------------
               CARDS
               --------------------------------------------- */

            #card {
                background: #1f2937;
                border: 1px solid #374151;
            }

            /* ---------------------------------------------
               TEXT INPUTS
               --------------------------------------------- */

            QLineEdit {
                background: #1f2937;
                color: #f9fafb;
                border: 1px solid #4b5563;
            }

            QLineEdit:focus {
                border: 1px solid #9ca3af;
            }

            QLineEdit:disabled {
                background: #374151;
                color: #9ca3af;
            }

            QLineEdit::placeholder {
                color: #9ca3af;
            }

            #searchBox,
            #filterBox {
                background: #1f2937;
                color: #f9fafb;
                border: 1px solid #4b5563;
            }

            /* ---------------------------------------------
               COMBO BOXES
               --------------------------------------------- */

            QComboBox {
                background: #1f2937;
                color: #f9fafb;
                border: 1px solid #4b5563;
            }

            QComboBox:hover {
                border: 1px solid #6b7280;
            }

            QComboBox:focus {
                border: 1px solid #9ca3af;
            }

            QComboBox:disabled {
                background: #374151;
                color: #9ca3af;
                border-color: #4b5563;
            }

            QComboBox QAbstractItemView {
                background: #1f2937;
                color: #f9fafb;
                selection-background-color: #374151;
                selection-color: #ffffff;
                border: 1px solid #4b5563;
            }

            /* ---------------------------------------------
               BUTTONS
               --------------------------------------------- */

            QPushButton {
                color: #f9fafb;
            }

            QPushButton:disabled {
                color: #9ca3af;
            }

            #refreshButton {
                color: #ffffff;
            }

            #navigationButton {
                color: #d1d5db;
            }

            #navigationButton:hover,
            #navigationButton:pressed {
                color: #ffffff;
            }

            /* ---------------------------------------------
               TABLES
               --------------------------------------------- */

            QTableWidget {
                background: #1f2937;
                color: #f9fafb;
                alternate-background-color: #1f2937;
                border: 1px solid #4b5563;
                gridline-color: #9ca3af;
                selection-background-color: #4b5563;
                selection-color: #ffffff;
            }

            QTableWidget::item {
                color: #f9fafb;
                background: #1f2937;
            }

            QTableWidget::item:selected {
                color: #ffffff;
                background: #4b5563;
            }

            QHeaderView::section {
                background: #111827;
                color: #f9fafb;
                border: 1px solid #4b5563;
                border-bottom: 1px solid #9ca3af;
            }

            /* Explicitly cover all current application tables.
               This also preserves their existing object-specific
               styling while guaranteeing dark-mode readability. */

            #logbookTable,
            #aircraftTable,
            #airportsTable,
            #performanceTable,
            #fuelTable,
            #fuelYearTable {
                background: #1f2937;
                color: #f9fafb;
                gridline-color: #9ca3af;
            }

            #logbookTable::item,
            #aircraftTable::item,
            #airportsTable::item,
            #performanceTable::item,
            #fuelTable::item,
            #fuelYearTable::item {
                color: #f9fafb;
                background: #1f2937;
            }

            #logbookTable QHeaderView::section,
            #aircraftTable QHeaderView::section,
            #airportsTable QHeaderView::section,
            #performanceTable QHeaderView::section,
            #fuelTable QHeaderView::section,
            #fuelYearTable QHeaderView::section {
                background: #111827;
                color: #f9fafb;
                border: 1px solid #4b5563;
                border-bottom: 1px solid #9ca3af;
            }

            /* ---------------------------------------------
               TABS
               --------------------------------------------- */

            QTabBar::tab {
                color: #d1d5db;
            }

            QTabBar::tab:selected {
                color: #ffffff;
            }

            #yearTabs QTabBar::tab {
                background: #1f2937;
                border-color: #374151;
                color: #d1d5db;
            }

            #yearTabs QTabBar::tab:hover,
            #yearTabs QTabBar::tab:selected {
                background: #374151;
                color: #ffffff;
                border-color: #4b5563;
            }

            /* ---------------------------------------------
               LOGBOOK DROP ZONE
               --------------------------------------------- */

            #logbookDropZone {
                background: #1f2937;
                border-color: #4b5563;
            }

            #logbookDropTitle,
            #logbookDropIcon {
                color: #f9fafb;
            }

            #logbookDropSubtitle {
                color: #9ca3af;
            }

            /* ---------------------------------------------
               PROGRESS BAR
               --------------------------------------------- */

            #progressBar {
                background: #374151;
            }

            /* ---------------------------------------------
               SCROLLBARS
               --------------------------------------------- */

            QScrollBar:vertical {
                background: #1f2937;
                width: 12px;
                margin: 0;
            }

            QScrollBar::handle:vertical {
                background: #6b7280;
                min-height: 30px;
                border-radius: 6px;
            }

            QScrollBar::handle:vertical:hover {
                background: #9ca3af;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                background: #1f2937;
                border: none;
                height: 0;
            }

            QScrollBar:horizontal {
                background: #1f2937;
                height: 12px;
                margin: 0;
            }

            QScrollBar::handle:horizontal {
                background: #6b7280;
                min-width: 30px;
                border-radius: 6px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #9ca3af;
            }

            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                background: #1f2937;
                border: none;
                width: 0;
            }

            /* ---------------------------------------------
               TOOLTIP
               --------------------------------------------- */

            QToolTip {
                background: #1f2937;
                color: #f9fafb;
                border: 1px solid #4b5563;
            }

            """
        )
