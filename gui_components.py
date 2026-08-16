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
    QVBoxLayout,
)

class MetricCard(QFrame):
    """Reusable dashboard metric card with split-flap-style values."""

    FLAP_CHARACTERS = (
        " 0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        ":.,-/"
    )

    def __init__(
        self,
        title,
        value="—",
    ):
        super().__init__()

        self.setObjectName(
            "card"
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )

        layout.setSpacing(6)

        self.title_label = QLabel(
            title
        )

        self.title_label.setObjectName(
            "cardLabel"
        )

        layout.addWidget(
            self.title_label
        )

        # -------------------------------------------------
        # SPLIT-FLAP VALUE DISPLAY
        # -------------------------------------------------

        self.flap_container = QFrame()

        self.flap_container.setObjectName(
            "flapBoard"
        )

        self.flap_container.setStyleSheet(
            """
            QFrame#flapBoard {
                background-color: #59636f;
                border-radius: 5px;
            }
            """
        )

        # Keep the board only as wide as its flap contents.
        # Short values therefore get a short board instead
        # of stretching across the entire metric card.
        self.flap_container.setSizePolicy(
            QSizePolicy.Maximum,
            QSizePolicy.Preferred,
        )

        self.flap_layout = QHBoxLayout(
            self.flap_container
        )

        self.flap_layout.setContentsMargins(
            5,
            5,
            5,
            5,
        )

        self.flap_layout.setSpacing(2)

        self.flap_layout.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )

        layout.addWidget(
            self.flap_container,
            0,
            Qt.AlignLeft,
        )

        self.flap_labels = []

        self._flap_timer = QTimer(
            self
        )

        self._flap_timer.setInterval(
            60
        )

        self._flap_timer.timeout.connect(
            self._advance_flap
        )

        self._flap_target = str(
            value
        )

        self._flap_tick = 0
        self._flap_settle_ticks = []

        self._create_flaps(
            self._flap_target
        )

    def _create_flaps(self, value):
        """Create one physical-looking flap for every character."""

        while self.flap_layout.count():
            item = self.flap_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.flap_labels = []

        for character in str(value):
            label = QLabel(
                character
            )

            label.setAlignment(
                Qt.AlignCenter
            )

            label.setFixedSize(
                22,
                34,
            )

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

            self.flap_layout.addWidget(
                label
            )

            self.flap_labels.append(
                label
            )

    def set_value(
        self,
        value,
        animate=True,
    ):
        """Update the displayed metric."""

        value = str(
            value
        )

        if not animate:
            self._flap_timer.stop()
            self._flap_target = value
            self._create_flaps(value)
            return

        if value == self._flap_target:
            return

        self._flap_target = value

        self._create_flaps(
            "".join(
                random.choice(
                    self.FLAP_CHARACTERS
                )
                for _ in value
            )
        )

        # Characters settle progressively from left to right.
        self._flap_settle_ticks = [
            7 + index * 2
            for index in range(
                len(value)
            )
        ]

        self._flap_tick = 0

        self._flap_timer.start()

    def _advance_flap(self):
        """Advance one frame of the mechanical flap animation."""

        target = self._flap_target

        if not target:
            self._flap_timer.stop()
            self._create_flaps("")
            return

        # Rebuild if the target length changed.
        if len(self.flap_labels) != len(target):
            self._create_flaps(
                target
            )

        for index, character in enumerate(
            target
        ):
            settle_tick = (
                self._flap_settle_ticks[index]
                if index < len(
                    self._flap_settle_ticks
                )
                else 7
            )

            if self._flap_tick >= settle_tick:
                displayed = character
            else:
                displayed = random.choice(
                    self.FLAP_CHARACTERS
                )

            self.flap_labels[
                index
            ].setText(
                displayed
            )

        self._flap_tick += 1

        if self._flap_tick >= (
            max(
                self._flap_settle_ticks,
                default=0,
            ) + 1
        ):
            self._flap_timer.stop()

            for label, character in zip(
                self.flap_labels,
                target,
            ):
                label.setText(
                    character
                )


class LogbookDropZone(QFrame):
    """Dashboard drop zone for selecting a logbook PDF or CSV."""

    logbook_selected = Signal(str)

    def __init__(self):
        super().__init__()

        self.setObjectName(
            "logbookDropZone"
        )

        self.setAcceptDrops(
            True
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            30,
            30,
            30,
            30,
        )

        layout.setSpacing(
            10
        )

        self.icon_label = QLabel(
            "✈"
        )

        self.icon_label.setObjectName(
            "logbookDropIcon"
        )

        self.icon_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.icon_label
        )

        self.title_label = QLabel(
            "Drop your logbook PDF or CSV here"
        )

        self.title_label.setObjectName(
            "logbookDropTitle"
        )

        self.title_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.title_label
        )

        self.subtitle_label = QLabel(
            "or click to browse for a PDF or CSV"
        )

        self.subtitle_label.setObjectName(
            "logbookDropSubtitle"
        )

        self.subtitle_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(
            self.subtitle_label
        )

        self.browse_button = QPushButton(
            "Choose Logbook"
        )

        self.browse_button.setObjectName(
            "logbookBrowseButton"
        )

        self.browse_button.setCursor(
            Qt.PointingHandCursor
        )

        self.browse_button.clicked.connect(
            self.browse_for_logbook
        )

        layout.addWidget(
            self.browse_button,
            0,
            Qt.AlignCenter,
        )

    def browse_for_logbook(self):
        """Open the logbook file picker."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Flight Logbook",
            "",
            "Logbook files (*.pdf *.csv)",
        )

        if path:
            self._select_path(
                path
            )

    def _select_path(self, path):
        """Validate and emit a selected logbook path."""
        path = Path(path)

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

        self.logbook_selected.emit(
            str(path.resolve())
        )

    def mousePressEvent(self, event):
        """Allow clicking anywhere in the drop zone."""
        if event.button() == Qt.LeftButton:
            self.browse_for_logbook()
            return

        super().mousePressEvent(
            event
        )

    def dragEnterEvent(self, event):
        """Accept dragged PDF or CSV files."""
        if not event.mimeData().hasUrls():
            event.ignore()
            return

        urls = event.mimeData().urls()

        if any(
            url.isLocalFile()
            and Path(
                url.toLocalFile()
            ).suffix.lower() == ".pdf"
            for url in urls
        ):
            event.acceptProposedAction()
            self.setProperty(
                "dragActive",
                True,
            )
            self.style().unpolish(self)
            self.style().polish(self)
            return

        event.ignore()

    def dragLeaveEvent(self, event):
        """Restore the normal drop-zone appearance."""
        self.setProperty(
            "dragActive",
            False,
        )

        self.style().unpolish(self)
        self.style().polish(self)

        event.accept()

    def dropEvent(self, event):
        """Handle a dropped PDF or CSV logbook."""
        self.setProperty(
            "dragActive",
            False,
        )

        self.style().unpolish(self)
        self.style().polish(self)

        urls = event.mimeData().urls()

        for url in urls:
            if not url.isLocalFile():
                continue

            path = Path(
                url.toLocalFile()
            )

            if path.suffix.lower() == ".pdf":
                self._select_path(
                    str(path)
                )
                event.acceptProposedAction()
                return

        event.ignore()
