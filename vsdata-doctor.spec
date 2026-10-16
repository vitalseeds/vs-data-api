# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for vsdata-doctor, the first-line debugger (see src/vs_doctor/CLAUDE.md).

Build: uv run pyinstaller vsdata-doctor.spec
Output: dist/vsdata-doctor[.exe] (single file)
"""

a = Analysis(
    ["src/vs_doctor/__main__.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=["pypyodbc"],  # imported lazily in diagnose.try_odbc
    hookspath=[],
    runtime_hooks=[],
    # Keep the doctor independent of the main app and its heavy dependencies
    excludes=["vs_data_api", "fastapi", "starlette", "uvicorn", "pandas", "numpy", "woocommerce", "tkinter"],
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
