"""Verify FlightStats aircraft resolution into OpenAP identities."""

from parser.aircraft import AircraftResolver


def test_crj900_resolves_to_openap_crj9():
    resolver = AircraftResolver()

    result = resolver.resolve("CRJ900")

    assert result.icao == "CRJ9"
    assert result.openap == "CRJ9"
    assert result.status == "resolved"


def test_a330_900_is_not_falsely_mapped():
    resolver = AircraftResolver()

    result = resolver.resolve("A330-900")

    assert result.icao is None
    assert result.openap is None
    assert result.status == "unknown"


def test_unsupported_small_aircraft_are_not_falsely_mapped():
    resolver = AircraftResolver()

    for aircraft in (
        "DH8D",
        "ATR72",
        "PA28",
        "PA34",
        "PA44",
        "EA300L",
    ):
        result = resolver.resolve(aircraft)

        assert result.openap is None
