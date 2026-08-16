from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
)

from gui_fuel_dialog import show_missing_fuel_profile_dialog


def get_app():
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def find_new_fuel_dialog(app, existing):
    for widget in app.topLevelWidgets():
        if (
            widget not in existing
            and isinstance(widget, QDialog)
            and widget.windowTitle()
            == "Aircraft Fuel Profile Required"
        ):
            return widget

    raise AssertionError(
        "New fuel profile dialog was not found."
    )


def test_cancel_returns_none():
    app = get_app()

    diagnosis = {
        "canonical": None,
        "icao": None,
        "aircraft_status": "unknown",
    }

    existing = set(
        app.topLevelWidgets()
    )

    def cancel_dialog():
        dialog = find_new_fuel_dialog(
            app,
            existing,
        )

        dialog.reject()

    QTimer.singleShot(
        0,
        cancel_dialog,
    )

    result = show_missing_fuel_profile_dialog(
        None,
        "UNKNOWN",
        diagnosis,
    )

    assert result is None


def test_valid_submission_returns_profile():
    app = get_app()

    diagnosis = {
        "canonical": "CRJ900",
        "icao": "CRJ9",
        "aircraft_status": "resolved",
    }

    existing = set(
        app.topLevelWidgets()
    )

    def submit_dialog():
        dialog = find_new_fuel_dialog(
            app,
            existing,
        )

        fuel_edit = dialog.findChild(
            QLineEdit,
            "fuelBurnEdit",
        )

        notes_edit = dialog.findChild(
            QLineEdit,
            "fuelNotesEdit",
        )

        unit_combo = dialog.findChild(
            QComboBox,
            "fuelUnitCombo",
        )

        buttons = dialog.findChild(
            QDialogButtonBox,
            "fuelProfileButtons",
        )

        assert fuel_edit is not None
        assert notes_edit is not None
        assert unit_combo is not None
        assert buttons is not None

        fuel_edit.setText(
            "2500"
        )

        notes_edit.setText(
            "Test profile"
        )

        unit_combo.setCurrentText(
            "kg/h"
        )

        buttons.accepted.emit()

    QTimer.singleShot(
        0,
        submit_dialog,
    )

    result = show_missing_fuel_profile_dialog(
        None,
        "CRJ900",
        diagnosis,
    )

    assert result == {
        "average_burn": 2500.0,
        "unit": "kg/h",
        "notes": "Test profile",
    }
