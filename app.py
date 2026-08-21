"""
FlightStats application entry point.

Development:
    python app.py

Packaged:
    PyInstaller uses this module as the application entry point.
"""

from gui import main
from gui_layout_fixes import apply_dashboard_layout_fixes


if __name__ == "__main__":
    apply_dashboard_layout_fixes()
    main()
