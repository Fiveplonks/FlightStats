# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

PROJECT_DIR = Path("FlightStats-windows.spec").resolve().parent

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
            str(PROJECT_DIR / "data"),
            "data",
        ),
        (
            str(PROJECT_DIR / "FlightStats.ico"),
            ".",
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
    a.datas,
    [],
    name="FlightStats",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(PROJECT_DIR / "FlightStats.ico"),
)
