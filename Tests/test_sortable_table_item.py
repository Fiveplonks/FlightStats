from PySide6.QtWidgets import QApplication

from gui_components import SortableTableWidgetItem


def app():
    instance = QApplication.instance()
    if instance is None:
        instance = QApplication([])
    return instance


def test_numeric_sorting():
    app()

    low = SortableTableWidgetItem("9,000 km", 9000)
    high = SortableTableWidgetItem("10,000 km", 10000)

    assert low < high
    assert not high < low


def test_alphabetical_sorting_without_sort_value():
    app()

    ams = SortableTableWidgetItem("AMS")
    eham = SortableTableWidgetItem("EHAM")

    assert ams < eham
    assert not eham < ams


def test_time_sorting_uses_numeric_value():
    app()

    early = SortableTableWidgetItem("09:30", 570)
    late = SortableTableWidgetItem("10:15", 615)

    assert early < late
    assert not late < early


def test_date_sorting_uses_chronological_value():
    app()

    older = SortableTableWidgetItem(
        "31-12-2024",
        __import__("datetime").date(2024, 12, 31),
    )
    newer = SortableTableWidgetItem(
        "01-01-2025",
        __import__("datetime").date(2025, 1, 1),
    )

    assert older < newer
    assert not newer < older

