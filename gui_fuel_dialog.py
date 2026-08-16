"""Manual fuel-profile dialog for FlightStats."""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)


def show_missing_fuel_profile_dialog(
    parent,
    aircraft_type,
    diagnosis,
):
    """Collect a manual fuel profile from the user."""

    canonical = diagnosis.get(
        "canonical"
    )

    icao = diagnosis.get(
        "icao"
    )

    aircraft_status = diagnosis.get(
        "aircraft_status"
    )

    dialog = QDialog(parent)

    dialog.setWindowTitle(
        "Aircraft Fuel Profile Required"
    )

    dialog.setModal(True)

    layout = QVBoxLayout(
        dialog
    )

    title = QLabel(
        "No automatic fuel profile is available."
    )

    title.setObjectName(
        "pageTitle"
    )

    layout.addWidget(
        title
    )

    details = QLabel()

    details_text = (
        f"<b>Logbook aircraft:</b> "
        f"{aircraft_type}"
    )

    if canonical:
        details_text += (
            f"<br><b>Recognized as:</b> "
            f"{canonical}"
        )

    if icao:
        details_text += (
            f"<br><b>ICAO:</b> "
            f"{icao}"
        )

    if aircraft_status:
        details_text += (
            f"<br><b>Status:</b> "
            f"{aircraft_status.replace('_', ' ')}"
        )

    details.setText(
        details_text
    )

    details.setWordWrap(
        True
    )

    layout.addWidget(
        details
    )

    explanation = QLabel(
        "Enter an average fuel burn figure for this aircraft. "
        "The value will be saved and used for all flights of "
        "this aircraft type."
    )

    explanation.setWordWrap(
        True
    )

    layout.addWidget(
        explanation
    )

    form_layout = QGridLayout()

    form_layout.addWidget(
        QLabel("Average fuel burn:"),
        0,
        0,
    )

    fuel_edit = QLineEdit()

    fuel_edit.setObjectName(
        "fuelBurnEdit"
    )

    fuel_edit.setPlaceholderText(
        "e.g. 2500"
    )

    form_layout.addWidget(
        fuel_edit,
        0,
        1,
    )

    form_layout.addWidget(
        QLabel("Unit:"),
        1,
        0,
    )

    unit_combo = QComboBox()

    unit_combo.setObjectName(
        "fuelUnitCombo"
    )

    unit_combo.addItems(
        [
            "kg/h",
            "L/h",
        ]
    )

    form_layout.addWidget(
        unit_combo,
        1,
        1,
    )

    form_layout.addWidget(
        QLabel("Notes:"),
        2,
        0,
    )

    notes_edit = QLineEdit()

    notes_edit.setObjectName(
        "fuelNotesEdit"
    )

    notes_edit.setPlaceholderText(
        "Optional"
    )

    form_layout.addWidget(
        notes_edit,
        2,
        1,
    )

    layout.addLayout(
        form_layout
    )

    buttons = QDialogButtonBox(
        QDialogButtonBox.Save
        | QDialogButtonBox.Cancel
    )

    buttons.setObjectName(
        "fuelProfileButtons"
    )

    layout.addWidget(
        buttons
    )

    buttons.rejected.connect(
        dialog.reject
    )

    profile = None

    def accept_profile():
        nonlocal profile

        try:
            average_burn = float(
                fuel_edit.text().strip()
            )
        except ValueError:
            QMessageBox.warning(
                dialog,
                "Invalid Fuel Figure",
                "Please enter a valid numerical fuel-burn value.",
            )
            fuel_edit.setFocus()
            return

        if average_burn <= 0:
            QMessageBox.warning(
                dialog,
                "Invalid Fuel Figure",
                "Fuel burn must be greater than zero.",
            )
            fuel_edit.setFocus()
            return

        profile = {
            "average_burn": average_burn,
            "unit": unit_combo.currentText(),
            "notes": notes_edit.text().strip(),
        }

        dialog.accept()

    buttons.accepted.connect(
        accept_profile
    )

    if dialog.exec() != QDialog.Accepted:
        return None

    return profile
