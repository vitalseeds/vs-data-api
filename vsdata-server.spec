# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for VS Data API standalone server.

Build commands:
  Windows: pyinstaller vsdata-server.spec
  macOS:   pyinstaller vsdata-server.spec

Output: dist/vsdata-server/vsdata-server[.exe]
"""
import sys
from pathlib import Path

block_cipher = None

# Determine platform-specific settings
is_windows = sys.platform == "win32"
is_macos = sys.platform == "darwin"

# Path to the source directory
src_path = Path("src")

a = Analysis(
    ["src/vs_data_api/standalone.py"],
    pathex=[str(src_path)],
    binaries=[],
    datas=[],
    hiddenimports=[
        # FastAPI and Starlette
        "fastapi",
        "fastapi.responses",
        "fastapi.routing",
        "fastapi.middleware",
        "fastapi.middleware.cors",
        "starlette",
        "starlette.responses",
        "starlette.routing",
        "starlette.middleware",
        "starlette.middleware.cors",
        "starlette.staticfiles",
        "starlette.templating",

        # Uvicorn and ASGI
        "uvicorn",
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",

        # Pydantic
        "pydantic",
        "pydantic.fields",
        "pydantic_settings",
        "pydantic_core",
        "pydantic_core._pydantic_core",

        # HTTP/Networking
        "httptools",
        "websockets",
        "h11",
        "anyio",
        "anyio._backends",
        "anyio._backends._asyncio",
        "sniffio",

        # WooCommerce
        "woocommerce",
        "requests",
        "requests.adapters",
        "urllib3",
        "urllib3.util",
        "urllib3.util.retry",
        "certifi",
        "charset_normalizer",
        "idna",

        # Database
        "pypyodbc",
        "pypika",

        # Data processing
        "pandas",
        "pandas._libs",
        "pandas._libs.tslibs",
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.timedeltas",
        "numpy",
        "numpy.core",
        "numpy.core._multiarray_umath",

        # CLI and output
        "click",
        "rich",
        "rich.logging",
        "rich.console",
        "rich.traceback",

        # Service container
        "svcs",

        # Standard library modules that might be missed
        "email.mime.text",
        "email.mime.multipart",
        "configparser",
        "json",
        "ssl",
        "multiprocessing",
        "logging.config",

        # Application modules
        "vs_data_api",
        "vs_data_api.main",
        "vs_data_api.config",
        "vs_data_api.cli",
        "vs_data_api.__about__",
        "vs_data_api.vs_data",
        "vs_data_api.vs_data.fm",
        "vs_data_api.vs_data.fm.db",
        "vs_data_api.vs_data.fm.vs_tables",
        "vs_data_api.vs_data.fm.link_tables",
        "vs_data_api.vs_data.fm.constants",
        "vs_data_api.vs_data.wc",
        "vs_data_api.vs_data.orders",
        "vs_data_api.vs_data.stock",
        "vs_data_api.vs_data.products",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude test-only dependencies
        "pytest",
        "pytest_cov",
        "pytest_timeout",
        "pytest_factoryboy",
        "coverage",
        "responses",

        # Exclude development tools
        "pudb",
        "ipython",
        "objexplore",
        "pre_commit",

        # Exclude unused heavy packages
        "matplotlib",
        "scipy",
        "tkinter",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add uvloop only on non-Windows platforms
if not is_windows:
    a.hiddenimports.append("uvloop")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vsdata-server",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Keep console for logging output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="vsdata-server",
)
