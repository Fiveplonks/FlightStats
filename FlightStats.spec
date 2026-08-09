# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

PROJECT_DIR = Path("FlightStats.spec").resolve().parent

a = Analysis(
    ["app.py"],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[
        (
            str(PROJECT_DIR / "data" / "airports.csv"),
            "data",
        ),
        (
            str(PROJECT_DIR / "data" / "aircraft_fuel_burn.csv"),
            "data",
        ),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(
    a.pure,
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FlightStats",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

app = BUNDLE(
    exe,
    name="FlightStats.app",
    icon=None,
    bundle_identifier="com.flightstats.app",
)
