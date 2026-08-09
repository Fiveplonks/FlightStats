"""Dispatch supported FlightStats input files to the correct parser."""

from pathlib import Path

from parser.csv import parse_csv
from parser.easa_pdf import parse_logbook

SUPPORTED_EXTENSIONS = {".pdf", ".csv"}


def parse_flight_file(path):
    """Parse a supported FlightStats input file."""
    path = Path(path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return parse_logbook(path)

    if suffix == ".csv":
        return parse_csv(path)

    raise ValueError(
        f"Unsupported logbook format: {suffix or '(no extension)'}"
    )
