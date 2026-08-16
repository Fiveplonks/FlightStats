"""Flight-time discrepancy dialog for FlightStats."""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QPlainTextEdit,
    QVBoxLayout,
    QLabel,
)


def show_discrepancies(
    parent,
    discrepancies,
    format_hours,
):
    """Show flight-time discrepancies in a resizable dialog."""

    if not discrepancies:
        return

    dialog = QDialog(parent)

    dialog.setWindowTitle(
        "Flight Time Discrepancies"
    )

    dialog.setMinimumSize(
        600,
        400,
    )

    dialog.resize(
        900,
        650,
    )

    layout = QVBoxLayout(dialog)

    title = QLabel(
        f"{len(discrepancies)} flight-time discrepancy"
        + ("" if len(discrepancies) == 1 else "ies")
        + " found."
    )

    title.setWordWrap(True)

    layout.addWidget(title)

    text_edit = QPlainTextEdit()

    text_edit.setReadOnly(True)

    text_edit.setLineWrapMode(
        QPlainTextEdit.NoWrap
    )

    lines = []

    for index, discrepancy in enumerate(
        discrepancies,
        start=1,
    ):
        flight_date = discrepancy.get(
            "date",
            "Unknown date",
        )

        departure = discrepancy.get(
            "departure",
            "?",
        )

        arrival = discrepancy.get(
            "arrival",
            "?",
        )

        departure_time = discrepancy.get(
            "departure_time",
            "?",
        )

        arrival_time = discrepancy.get(
            "arrival_time",
            "?",
        )

        calculated = discrepancy.get(
            "calculated_minutes"
        )

        logged = discrepancy.get(
            "logged_minutes"
        )

        difference = discrepancy.get(
            "difference_minutes"
        )

        lines.append(
            f"Discrepancy {index}  |  {flight_date}"
        )

        lines.append(
            f"{departure} → {arrival}"
        )

        lines.append(
            f"Departure: {departure_time}    "
            f"Arrival: {arrival_time}"
        )

        lines.append("")

        lines.append(
            "Calculated flight time: "
            f"{format_hours(calculated)}"
        )

        lines.append(
            "Logged flight time:     "
            f"{format_hours(logged)}"
        )

        lines.append(
            "Difference:             "
            f"{format_hours(difference)}"
        )

        lines.append("")

        lines.append("-" * 70)

        lines.append("")

    text_edit.setPlainText(
        "\n".join(lines)
    )

    layout.addWidget(
        text_edit,
        1,
    )

    buttons = QDialogButtonBox(
        QDialogButtonBox.Ok
    )

    buttons.accepted.connect(
        dialog.accept
    )

    layout.addWidget(buttons)

    dialog.exec()
