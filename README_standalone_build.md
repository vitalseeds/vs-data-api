# VS Data API - Standalone Deployment

This guide covers building and deploying VS Data API as a standalone executable that runs as a system service, accessible across your local network.

## Overview

The standalone deployment packages the FastAPI application into a single executable using PyInstaller. The server:

- Runs on `0.0.0.0:8432` (accessible from any machine on the LAN)
- Loads configuration from environment variables or a config file
- Can run as a system service (auto-start on boot)
- Validates configuration at startup with clear error messages

## Table of Contents

- [VS Data API - Standalone Deployment](#vs-data-api---standalone-deployment)
  - [Overview](#overview)
  - [Table of Contents](#table-of-contents)
  - [Prerequisites](#prerequisites)
    - [All Platforms](#all-platforms)
    - [macOS](#macos)
    - [Windows 11](#windows-11)
  - [Building the Executable](#building-the-executable)
    - [Build on macOS](#build-on-macos)
    - [Build on Windows 11](#build-on-windows-11)
    - [Build via GitHub Actions](#build-via-github-actions)

---

## Prerequisites

### All Platforms

- FileMaker ODBC driver installed and configured
- FileMaker database with ODBC sharing enabled
- WooCommerce API credentials

### macOS

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [libiodbc](https://formulae.brew.sh/formula/libiodbc): `brew install libiodbc`

### Windows 11

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [NSSM](https://nssm.cc/download) (for running as a service)

---

## Building the Executable

> **Note**: PyInstaller cannot cross-compile. You must build on the target platform (build Windows exe on Windows, macOS binary on macOS).

### Build on macOS

```bash
# 1. Clone the repository
git clone https://github.com/vitalseeds/vs-data-api.git
cd vs-data-api

# 2. Install dependencies including PyInstaller
uv sync --extra dev

# 3. Build the executable
uv run python deploy/build.py --clean

# 4. Verify the build
ls -la dist/vsdata-server/
```

The executable will be at `dist/vsdata-server/vsdata-server`.

### Build on Windows 11

```powershell
# 1. Clone the repository
git clone https://github.com/vitalseeds/vs-data-api.git
cd vs-data-api

# 2. Install dependencies including PyInstaller
uv sync --extra dev

# 3. Build the executable
uv run python deploy/build.py --clean

# 4. Verify the build
dir dist\vsdata-server\
```

The executable will be at `dist\vsdata-server\vsdata-server.exe`.

### Build via GitHub Actions

For automated builds, push a version tag:

```bash
git tag v2.1.1
git push origin v2.1.1
```

Or trigger manually from GitHub:
1. Go to repository → Actions → "Build Executables"
2. Click "Run workflow"
3. Download artifacts when complete