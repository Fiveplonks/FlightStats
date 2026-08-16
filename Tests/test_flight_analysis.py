from datetime import date

import pytest

from parser.flight_analysis import (
    calculate_all_distances,
    calculate_flight_distance,
    total_distance_km,
)
from parser.models import Flight


class FakeAirportDatabase:
    def __init__(self, airports):
        self.airports = airports

    def resolve(self, code):
        return self.airports.get(code)


def make_flight(departure, arrival):
    return Flight(
        date=date(2026, 1, 1),
        departure=departure,
        departure_time=None,
        arrival=arrival,
        arrival_time=None,
        aircraft="B738",
        registration="TEST",
        flight_minutes=60,
    )


def test_calculate_flight_distance_raises_for_unresolved_airport():
    database = FakeAirportDatabase(
        {
            "AAA": {
                "latitude": 50.0,
                "longitude": 4.0,
            },
        }
    )

    flight = make_flight("AAA", "UNKNOWN")

    with pytest.raises(
        ValueError,
        match="Unable to resolve arrival airport: UNKNOWN",
    ):
        calculate_flight_distance(
            flight,
            database,
        )


def test_calculate_all_distances_preserves_unresolved_flight():
    database = FakeAirportDatabase(
        {
            "AAA": {
                "latitude": 50.0,
                "longitude": 4.0,
            },
            "BBB": {
                "latitude": 51.0,
                "longitude": 5.0,
            },
        }
    )

    flights = [
        make_flight("AAA", "BBB"),
        make_flight("AAA", "UNKNOWN"),
        make_flight("BBB", "AAA"),
    ]

    results = calculate_all_distances(
        flights,
        database,
    )

    assert len(results) == 3

    assert results[0]["distance_km"] is not None
    assert results[1]["distance_km"] is None
    assert results[2]["distance_km"] is not None


def test_calculate_all_distances_continues_after_unresolved_flight():
    database = FakeAirportDatabase(
        {
            "AAA": {
                "latitude": 50.0,
                "longitude": 4.0,
            },
            "BBB": {
                "latitude": 51.0,
                "longitude": 5.0,
            },
        }
    )

    flights = [
        make_flight("AAA", "UNKNOWN"),
        make_flight("AAA", "BBB"),
    ]

    results = calculate_all_distances(
        flights,
        database,
    )

    assert len(results) == 2
    assert results[0]["distance_km"] is None
    assert results[1]["distance_km"] is not None


def test_total_distance_ignores_unresolved_flights():
    results = [
        {
            "flight": make_flight("AAA", "BBB"),
            "distance_km": 100.0,
        },
        {
            "flight": make_flight("AAA", "UNKNOWN"),
            "distance_km": None,
        },
        {
            "flight": make_flight("BBB", "AAA"),
            "distance_km": 250.0,
        },
    ]

    assert total_distance_km(results) == 350.0
