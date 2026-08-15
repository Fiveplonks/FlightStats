"""Dispatch supported FlightStats input files to the correct parser."""

from pathlib import Path

from parser.csv import parse_csv
from parser.easa_pdf import parse_logbook

SUPPORTED_EXTENSIONS = {".pdf", ".csv"}


def parse_flight_file(
    path,
    progress_callback=None,
    discrepancy_callback=None,
    previous_experience_callback=None,
):
    """Parse a supported FlightStats input file."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return parse_logbook(
            path,
            progress_callback=progress_callback,
            discrepancy_callback=discrepancy_callback,
            previous_experience_callback=(
                previous_experience_callback
            ),
        )

    if suffix == ".csv":
        return parse_csv(path)

    raise ValueError(
        f"Unsupported logbook format: {suffix or '(no extension)'}"
    )
