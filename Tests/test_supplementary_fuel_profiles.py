"""Milestone 7: verify supplementary fuel profiles."""

from parser.fuel import FuelDatabase


def test_atr72_supplementary_profile():
    profile = FuelDatabase.SUPPLEMENTARY_PROFILES["ATR72"]
    assert profile["average_burn"] == 650.0
    assert profile["unit"] == "kg/h"


def test_dh8d_supplementary_profile():
    profile = FuelDatabase.SUPPLEMENTARY_PROFILES["DH8D"]
    assert profile["average_burn"] == 812.5
    assert profile["unit"] == "kg/h"


def test_pa44_supplementary_profile():
    profile = FuelDatabase.SUPPLEMENTARY_PROFILES["PA44"]
    assert profile["average_burn"] == 88.2
    assert profile["unit"] == "L/h"


def test_a330_900_remains_unresolved():
    assert "A330-900" not in FuelDatabase.SUPPLEMENTARY_PROFILES


def test_pa28_pa34_ea300l_remain_unresolved():
    for aircraft in ("PA28", "PA34", "EA300L"):
        assert aircraft not in FuelDatabase.SUPPLEMENTARY_PROFILES
