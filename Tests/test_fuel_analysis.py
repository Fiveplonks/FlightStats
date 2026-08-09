from parser.csv import parse_csv
from parser.fuel import FuelDatabase
from parser.fuel_analysis import (
    calculate_all_fuel,
    summarize_fuel,
)


def test_aircraft_variants_are_grouped_by_normalized_type():
    flights = parse_csv(
        "Tests/fixtures/synthetic_edge_1000.csv"
    )

    database = FuelDatabase()

    results = calculate_all_fuel(
        flights,
        database,
    )

    summary = summarize_fuel(results)
    aircraft = summary["by_aircraft"]

    # Equivalent representations must be consolidated.
    assert "B737-800" in aircraft
    assert "737-800" not in aircraft
    assert "800" not in aircraft

    # The MAX must remain a separate aircraft family.
    assert "B737-8200" in aircraft
    assert "B737-800" in aircraft

    assert (
        aircraft["B737-800"]["flights"]
        == 59
    )

    assert (
        aircraft["B737-8200"]["flights"]
        == 59
    )


def test_canonical_aircraft_count():
    flights = parse_csv(
        "Tests/fixtures/synthetic_edge_1000.csv"
    )

    database = FuelDatabase()

    results = calculate_all_fuel(
        flights,
        database,
    )

    summary = summarize_fuel(results)

    assert len(
        summary["by_aircraft"]
    ) == 17
