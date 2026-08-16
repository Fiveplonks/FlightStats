from datetime import date, time

import data_manager
from parser.models import Flight


def make_flight(
    departure="AAA",
    arrival="BBB",
):
    return Flight(
        date=date(2026, 1, 1),
        departure=departure,
        departure_time=time(10, 0),
        arrival=arrival,
        arrival_time=time(11, 0),
        aircraft="B738",
        registration="TEST",
        flight_minutes=60,
        captain=None,
        logged_flight_minutes=60,
        logged_time_status="valid",
    )


def prepare_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    monkeypatch.setattr(
        data_manager,
        "CACHE_DIR",
        cache_dir,
    )

    logbook = tmp_path / "logbook.pdf"
    logbook.write_bytes(
        b"test logbook contents"
    )

    flights = [
        make_flight(),
    ]

    data_manager._save_cached_flights(
        logbook,
        flights,
        previous_experience_minutes=120,
    )

    return logbook, flights


def test_valid_cache_is_loaded(
    tmp_path,
    monkeypatch,
):
    logbook, flights = prepare_cache(
        tmp_path,
        monkeypatch,
    )

    result = data_manager._load_cached_flights(
        logbook,
    )

    assert result is not None

    cached_flights, previous_experience = result

    assert len(cached_flights) == 1
    assert cached_flights[0].departure == flights[0].departure
    assert cached_flights[0].arrival == flights[0].arrival
    assert previous_experience == 120


def test_changed_logbook_invalidates_cache(
    tmp_path,
    monkeypatch,
):
    logbook, _ = prepare_cache(
        tmp_path,
        monkeypatch,
    )

    logbook.write_bytes(
        b"changed logbook contents"
    )

    assert (
        data_manager._load_cached_flights(
            logbook,
        )
        is None
    )


def test_changed_cache_version_invalidates_cache(
    tmp_path,
    monkeypatch,
):
    logbook, _ = prepare_cache(
        tmp_path,
        monkeypatch,
    )

    monkeypatch.setattr(
        data_manager,
        "CACHE_VERSION",
        data_manager.CACHE_VERSION + 1,
    )

    assert (
        data_manager._load_cached_flights(
            logbook,
        )
        is None
    )


def test_changed_parser_signature_invalidates_cache(
    tmp_path,
    monkeypatch,
):
    logbook, _ = prepare_cache(
        tmp_path,
        monkeypatch,
    )

    original_signature = (
        data_manager._parser_signature()
    )

    monkeypatch.setattr(
        data_manager,
        "_parser_signature",
        lambda: original_signature + "-changed",
    )

    assert (
        data_manager._load_cached_flights(
            logbook,
        )
        is None
    )


def test_corrupt_cache_is_ignored(
    tmp_path,
    monkeypatch,
):
    logbook, _ = prepare_cache(
        tmp_path,
        monkeypatch,
    )

    cache_path = data_manager._cache_path()

    cache_path.write_text(
        "{ this is not valid JSON",
        encoding="utf-8",
    )

    assert (
        data_manager._load_cached_flights(
            logbook,
        )
        is None
    )


def test_valid_cache_can_load_without_source_logbook(
    tmp_path,
    monkeypatch,
):
    logbook, _ = prepare_cache(
        tmp_path,
        monkeypatch,
    )

    logbook.unlink()

    result = data_manager._load_cached_flights(
        logbook,
        allow_missing_logbook=True,
    )

    assert result is not None

    cached_flights, previous_experience = result

    assert len(cached_flights) == 1
    assert cached_flights[0].departure == "AAA"
    assert cached_flights[0].arrival == "BBB"
    assert previous_experience == 120


def test_missing_source_logbook_rejects_cache_by_default(
    tmp_path,
    monkeypatch,
):
    logbook, _ = prepare_cache(
        tmp_path,
        monkeypatch,
    )

    logbook.unlink()

    assert (
        data_manager._load_cached_flights(
            logbook,
        )
        is None
    )
