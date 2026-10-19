# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for vsdata-doctor, the first-line debugger (see src/vs_doctor/CLAUDE.md).

The window (gui.py) uses tkinter and the sv-ttk theme, so both are bundled. The exe stays a
console build: the window hides the console at start and the --console flag keeps it.

Build: uv run pyinstaller vsdata-doctor.spec
Output: dist/vsdata-doctor[.exe] (single file)
"""

from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ["src/vs_doctor/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=collect_data_files("sv_ttk"),
    hiddenimports=["pypyodbc", "sv_ttk"],  # imported lazily in diagnose.try_odbc and gui.run
    hookspath=[],
    runtime_hooks=[],
    # Keep the doctor independent of the main app and its heavy dependencies
    excludes=["vs_data_api", "fastapi", "starlette", "uvicorn", "pandas", "numpy", "woocommerce"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="vsdata-doctor",
    debug=False,
    strip=False,
    upx=True,
    console=True,
)
