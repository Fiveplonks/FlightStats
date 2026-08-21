"""Unit preference dialog for FlightStats."""

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout

from gui_units import DISTANCE_UNITS, FUEL_UNITS, UnitSettings


class UnitSettingsDialog(QDialog):
    """Choose global presentation units."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Units")
        self.setModal(True)

        self.settings = UnitSettings()

        layout = QFormLayout(self)

        self.distance_combo = QComboBox()
        self.distance_combo.addItems(DISTANCE_UNITS)
        self.distance_combo.setCurrentText(self.settings.distance_unit)
        layout.addRow("Distance:", self.distance_combo)

        self.fuel_combo = QComboBox()
        self.fuel_combo.addItems(FUEL_UNITS)
        self.fuel_combo.setCurrentText(self.settings.fuel_unit)
        layout.addRow("Fuel flow:", self.fuel_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept(self):
        self.settings.save(
            self.distance_combo.currentText(),
            self.fuel_combo.currentText(),
        )
        super().accept()
