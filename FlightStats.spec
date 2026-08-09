# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

PROJECT_DIR = Path("FlightStats.spec").resolve().parent

OPENAP_DATA = collect_data_files(
    "openap",
    include_py_files=False,
)

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
        *OPENAP_DATA,
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
    [],
    exclude_binaries=True,
    name="FlightStats",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="FlightStats",
)

app = BUNDLE(
    coll,
    name="FlightStats.app",
    icon=None,
    bundle_identifier="com.flightstats.app",
)
