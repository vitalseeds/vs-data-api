"""
Standalone entry point for PyInstaller-bundled executable.

Starts Uvicorn server programmatically with configuration loaded from:
1. Environment variables (highest priority)
2. User config file in platform-appropriate location
3. Built-in defaults (lowest priority)

Exit codes:
- 0: Clean shutdown
- 1: Configuration error (missing required settings) - do not restart
- 2: Runtime error (crash/exception) - service should restart
"""
import configparser
import os
import sys
from pathlib import Path
from typing import Optional

import uvicorn


# Exit codes for service management
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_RUNTIME_ERROR = 2

# Required configuration keys (without VSDATA_ prefix)
REQUIRED_CONFIG = [
    "fm_connection_string",
    "fm_link_connection_string",
    "wc_url",
    "wc_key",
    "wc_secret",
]


def get_config_dir() -> Path:
    """Return platform-appropriate config directory."""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "VSData"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VSData"
    else:  # Linux and others
        xdg_config = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg_config) / "vsdata"


def get_data_dir() -> Path:
    """Return platform-appropriate data directory (for logs, certs)."""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "VSData"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "VSData"
    else:
        xdg_data = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        return Path(xdg_data) / "vsdata"


def load_config_file() -> dict:
    """Load configuration from INI file if it exists."""
    config_path = get_config_dir() / "config.ini"
    config = {}

    if config_path.exists():
        print(f"Loading config from: {config_path}")
        parser = configparser.ConfigParser()
        parser.read(config_path)

        # [vsdata] section -> VSDATA_* environment variables
        if "vsdata" in parser:
            for key, value in parser["vsdata"].items():
                env_key = f"VSDATA_{key.upper()}"
                config[env_key] = value

        # [ssl] section
        if "ssl" in parser:
            for key, value in parser["ssl"].items():
                if value:  # Only set if not empty
                    config[f"SSL_{key.upper()}"] = value

        # [server] section
        if "server" in parser:
            for key, value in parser["server"].items():
                config[f"VSDATA_{key.upper()}"] = value

        # [logging] section
        if "logging" in parser:
            for key, value in parser["logging"].items():
                config[key.upper()] = value
    else:
        print(f"No config file found at: {config_path}")

    return config


def apply_config_to_env(config: dict):
    """Apply config file values to environment (only if not already set)."""
    for key, value in config.items():
        if key not in os.environ:
            os.environ[key] = value


def validate_config() -> list[str]:
    """
    Validate that all required configuration is present.
    Returns list of missing config keys.
    """
    missing = []
    for key in REQUIRED_CONFIG:
        env_key = f"VSDATA_{key.upper()}"
        if not os.environ.get(env_key):
            missing.append(env_key)
    return missing


def get_ssl_paths() -> tuple[Optional[str], Optional[str]]:
    """Get SSL certificate and key file paths."""
    keyfile = os.environ.get("SSL_KEYFILE")
    certfile = os.environ.get("SSL_CERTFILE")

    # Check if SSL files exist at data directory location
    if not keyfile or not certfile:
        data_dir = get_data_dir()
        default_key = data_dir / "ssl" / "server_key.pem"
        default_cert = data_dir / "ssl" / "server_cert.pem"

        if default_key.exists() and default_cert.exists():
            keyfile = str(default_key)
            certfile = str(default_cert)

    # Validate files exist if specified
    if keyfile and certfile:
        if Path(keyfile).exists() and Path(certfile).exists():
            return keyfile, certfile
        else:
            print(f"Warning: SSL files not found (key: {keyfile}, cert: {certfile})")

    return None, None


def print_startup_info(host: str, port: int, ssl_enabled: bool):
    """Print startup information."""
    print("=" * 50)
    print("VS Data API Server")
    print("=" * 50)
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"SSL:  {'Enabled' if ssl_enabled else 'Disabled'}")
    print(f"URL:  {'https' if ssl_enabled else 'http'}://{host}:{port}")
    print("=" * 50)


def main():
    """Main entry point for standalone server."""
    try:
        # Load config file and apply to environment (env vars take precedence)
        file_config = load_config_file()
        apply_config_to_env(file_config)

        # Validate required configuration
        missing = validate_config()
        if missing:
            print("\n" + "=" * 50)
            print("CONFIGURATION ERROR")
            print("=" * 50)
            print("Missing required configuration:")
            for key in missing:
                print(f"  - {key}")
            print("\nSet these as environment variables or in config file:")
            print(f"  {get_config_dir() / 'config.ini'}")
            print("=" * 50)
            sys.exit(EXIT_CONFIG_ERROR)

        # Server configuration
        host = os.environ.get("VSDATA_HOST", "0.0.0.0")
        port = int(os.environ.get("VSDATA_PORT", "8432"))

        # SSL configuration
        ssl_keyfile, ssl_certfile = get_ssl_paths()

        # Log level
        log_level = os.environ.get("VS_DATA_LOGGING_LEVEL", "INFO").lower()

        # Print startup info
        print_startup_info(host, port, ssl_keyfile is not None)

        # Run the server
        uvicorn.run(
            "vs_data_api.main:app",
            host=host,
            port=port,
            reload=False,  # Cannot use reload in frozen app
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            log_level=log_level,
        )

        sys.exit(EXIT_SUCCESS)

    except KeyboardInterrupt:
        print("\nShutdown requested...")
        sys.exit(EXIT_SUCCESS)
    except Exception as e:
        print(f"\nRuntime error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(EXIT_RUNTIME_ERROR)


if __name__ == "__main__":
    main()
