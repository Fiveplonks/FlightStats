"""Reusable GUI components for FlightStats."""

import random
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTableWidgetItem,
    QVBoxLayout,
)


class MetricCard(QFrame):
    """Reusable dashboard metric card with split-flap-style values."""

    FLAP_CHARACTERS = (
        " 0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        ":.,-/"
    )

    def __init__(self, title, value="—", unit=None):
        super().__init__()
        self.setObjectName("card")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardLabel")
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        title_row.addWidget(self.title_label)

        self.unit_label = QLabel(unit or "")
        self.unit_label.setObjectName("cardUnitLabel")
        self.unit_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.unit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.unit_label.setVisible(bool(unit))
        title_row.addWidget(self.unit_label)
        layout.addLayout(title_row)

        self.flap_container = QFrame()
        self.flap_container.setObjectName("flapBoard")
        self.flap_container.setStyleSheet(
            """
            QFrame#flapBoard {
                background-color: #59636f;
                border-radius: 5px;
            }
            """
        )
        self.flap_container.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.flap_container.setFixedHeight(44)

        self.flap_layout = QHBoxLayout(self.flap_container)
        self.flap_layout.setContentsMargins(5, 5, 5, 5)
        self.flap_layout.setSpacing(2)
        self.flap_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        layout.addWidget(self.flap_container, 0, Qt.AlignLeft)
        layout.setStretch(0, 0)
        layout.setStretch(1, 0)

        self.flap_labels = []
        self._flap_timer = QTimer(self)
        self._flap_timer.setInterval(60)
        self._flap_timer.timeout.connect(self._advance_flap)
        self._flap_target = str(value)
        self._flap_tick = 0
        self._flap_settle_ticks = []
        self._create_flaps(self._flap_target)

    def set_unit(self, unit):
        """Set the small unit label displayed outside the split-flap board."""
        self.unit_label.setText(unit or "")
        self.unit_label.setVisible(bool(unit))

    def _create_flaps(self, value):
        while self.flap_layout.count():
            item = self.flap_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.flap_labels = []
        for character in str(value):
            label = QLabel(character)
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(22, 34)
            label.setStyleSheet(
                """
                QLabel {
                    color: #f5f5f5;
                    background: #090909;
                    border: 1px solid #292929;
                    border-radius: 2px;
                    font-family: "Courier New";
                    font-size: 18px;
                    font-weight: 700;
                    padding: 0px;
                }
                """
            )
            self.flap_layout.addWidget(label)
            self.flap_labels.append(label)

    def set_value(self, value, animate=True):
        value = str(value)
        if not animate:
            self._flap_timer.stop()
            self._flap_target = value
            self._create_flaps(value)
            return

        if value == self._flap_target:
            return

        self._flap_target = value
        self._create_flaps(
            "".join(random.choice(self.FLAP_CHARACTERS) for _ in value)
        )
        self._flap_settle_ticks = [7 + index * 2 for index in range(len(value))]
        self._flap_tick = 0
        self._flap_timer.start()

    def _advance_flap(self):
        target = self._flap_target
        if not target:
            self._flap_timer.stop()
            self._create_flaps("")
            return

        if len(self.flap_labels) != len(target):
            self._create_flaps(target)

        for index, character in enumerate(target):
            settle_tick = (
                self._flap_settle_ticks[index]
                if index < len(self._flap_settle_ticks)
                else 7
            )
            displayed = (
                character
                if self._flap_tick >= settle_tick
                else random.choice(self.FLAP_CHARACTERS)
            )
            self.flap_labels[index].setText(displayed)

        self._flap_tick += 1
        if self._flap_tick >= max(self._flap_settle_ticks, default=0) + 1:
            self._flap_timer.stop()
            for label, character in zip(self.flap_labels, target):
                label.setText(character)


class LogbookDropZone(QFrame):
    """Dashboard drop zone for selecting a logbook PDF or CSV."""

    logbook_selected = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("logbookDropZone")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(10)

        self.icon_label = QLabel("✈")
        self.icon_label.setObjectName("logbookDropIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        self.title_label = QLabel("Drop your logbook PDF or CSV here")
        self.title_label.setObjectName("logbookDropTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("or click to browse for a PDF or CSV")
        self.subtitle_label.setObjectName("logbookDropSubtitle")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle_label)

        self.browse_button = QPushButton("Choose Logbook")
        self.browse_button.setObjectName("logbookBrowseButton")
        self.browse_button.setCursor(Qt.PointingHandCursor)
        self.browse_button.clicked.connect(self.browse_for_logbook)
        layout.addWidget(self.browse_button, 0, Qt.AlignCenter)

    def browse_for_logbook(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Flight Logbook",
            "",
            "Logbook files (*.pdf *.csv)",
        )
        if path:
            self._select_path(path)

    def _select_path(self, path):
        path = Path(path)
        if not path.exists() or not path.is_file() or path.suffix.lower() not in {".pdf", ".csv"}:
            QMessageBox.warning(self, "Invalid Logbook", "Please select a valid PDF or CSV logbook.")
            return
        self.logbook_selected.emit(str(path.resolve()))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.browse_for_logbook()
            return
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if not event.mimeData().hasUrls():
            event.ignore()
            return
        urls = event.mimeData().urls()
        if any(
            url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() == ".pdf"
            for url in urls
        ):
            event.acceptProposedAction()
            self.setProperty("dragActive", True)
            self.style().unpolish(self)
            self.style().polish(self)
            return
        event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        event.accept()

    def dropEvent(self, event):
        self.setProperty("dragActive", False)
        self.style().unpolish(self)
        self.style().polish(self)
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = Path(url.toLocalFile())
            if path.suffix.lower() == ".pdf":
                self._select_path(str(path))
                event.acceptProposedAction()
                return
        event.ignore()


class SortableTableWidgetItem(QTableWidgetItem):
    """Table item that sorts using a hidden numeric value when supplied."""

    def __init__(self, text, sort_value=None):
        super().__init__(str(text))
        self.sort_value = sort_value

    def __lt__(self, other):
        if isinstance(other, SortableTableWidgetItem):
            if self.sort_value is not None and other.sort_value is not None:
                return self.sort_value < other.sort_value
        return str(self.text()).casefold() < str(other.text()).casefold()
