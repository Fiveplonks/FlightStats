from PySide6.QtCore import QObject, Signal

from data_manager import FlightStatsData


class DataLoaderWorker(QObject):
    """
    Worker responsible for loading FlightStats data
    outside the GUI thread.
    """

    progress = Signal(int, str)

    finished = Signal(object)

    error = Signal(str)

    def __init__(self, logbook_path):
        super().__init__()

        self.logbook_path = logbook_path

    def run(self):
        """Load all FlightStats data."""

        try:

            data = FlightStatsData(
                self.logbook_path,
                progress_callback=(
                    self.report_progress
                ),
            )

            self.finished.emit(
                data
            )

        except Exception as error:

            self.error.emit(
                str(error)
            )

    def report_progress(
        self,
        percent,
        message,
    ):
        """Forward backend progress to the GUI."""

        self.progress.emit(
            percent,
            message,
        )
