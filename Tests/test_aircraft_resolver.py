from parser.aircraft import AircraftResolver


def test_737_aliases_resolve_to_b738():
    resolver = AircraftResolver()

    for value in (
        "738",
        "737-800",
        "B737-800",
        "73H",
    ):
        result = resolver.resolve(value)

        assert result.canonical == "Boeing 737-800"
        assert result.icao == "B738"
        assert result.openap == "B738"
        assert result.status == "resolved"


def test_777_aliases_resolve_to_b772():
    resolver = AircraftResolver()

    for value in (
        "772",
        "777-200",
        "700-200",
    ):
        result = resolver.resolve(value)

        assert result.canonical == "Boeing 777-200"
        assert result.icao == "B772"
        assert result.openap == "B772"
        assert result.status == "resolved"


def test_7879_aliases_resolve_to_b789():
    resolver = AircraftResolver()

    for value in (
        "789",
        "787-9",
        "787-900",
        "B787-900",
    ):
        result = resolver.resolve(value)

        assert result.canonical == "Boeing 787-9"
        assert result.icao == "B789"
        assert result.openap == "B789"
        assert result.status == "resolved"


def test_78710_is_known_but_unsupported():
    resolver = AircraftResolver()

    result = resolver.resolve("787-10")

    assert result.canonical == "Boeing 787-10"
    assert result.icao == "B78X"
    assert result.openap is None
    assert result.status == "known_unsupported"


def test_unknown_aircraft_remains_unknown():
    resolver = AircraftResolver()

    result = resolver.resolve("ACFT-X")

    assert result.canonical is None
    assert result.icao is None
    assert result.openap is None
    assert result.status == "unknown"
