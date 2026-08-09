"""Milestone 6: verify FlightStats -> OpenAP aircraft mappings."""

from parser.fuel import FuelDatabase


def test_crj900_uses_openap_crj9():
    assert FuelDatabase.OPENAP_TYPES["CRJ900"] == "CRJ9"


def test_a330_900_is_not_falsely_mapped():
    assert "A330-900" not in FuelDatabase.OPENAP_TYPES


def test_unsupported_small_aircraft_are_not_falsely_mapped():
    for aircraft in ("DH8D", "ATR72", "PA28", "PA34", "PA44", "EA300L"):
        assert aircraft not in FuelDatabase.OPENAP_TYPES
