from parser.easa_pdf import parse_flight_row


def test_invalid_flight_date_is_rejected():
    flight, discrepancy = parse_flight_row(
        "31-02-2026 EHAM 10:00 LFPG 11:00 B738 PH-ABC 1 00"
    )

    assert flight is None
    assert discrepancy is None


def test_invalid_departure_time_is_rejected():
    flight, discrepancy = parse_flight_row(
        "01-02-2026 EHAM 25:00 LFPG 11:00 B738 PH-ABC 1 00"
    )

    assert flight is None
    assert discrepancy is None


def test_invalid_arrival_time_is_rejected():
    flight, discrepancy = parse_flight_row(
        "01-02-2026 EHAM 10:00 LFPG 25:00 B738 PH-ABC 1 00"
    )

    assert flight is None
    assert discrepancy is None


def test_valid_row_survives_after_malformed_input():
    malformed, _ = parse_flight_row(
        "31-02-2026 EHAM 10:00 LFPG 11:00 B738 PH-ABC 1 00"
    )

    valid, _ = parse_flight_row(
        "01-02-2026 EHAM 10:00 LFPG 11:00 B738 PH-ABC 1 00"
    )

    assert malformed is None
    assert valid is not None
    assert valid.departure == "EHAM"
    assert valid.arrival == "LFPG"
