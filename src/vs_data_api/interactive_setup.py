"""
Interactive credential setup for Windows standalone server.

Prompts user for missing configuration when running interactively
(not as a Windows service).
"""

import configparser
import getpass
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CredentialPrompt:
    """Configuration for prompting a single credential."""

    key: str  # Config key (e.g., "fm_connection_string")
    display_name: str  # Human-readable name
    description: str  # Help text for user
    is_secret: bool = False  # Whether to hide input
    example: Optional[str] = None  # Example value to show


CREDENTIAL_PROMPTS = [
    CredentialPrompt(
        key="fm_connection_string",
        display_name="FileMaker Connection String",
        description="ODBC connection string for the main VS database",
        example="Driver={FileMaker ODBC};Server=192.168.1.100;Database=VS_Data;UID=user;PWD=xxx",
    ),
    CredentialPrompt(
        key="fm_link_connection_string",
        display_name="FileMaker Link Connection String",
        description="ODBC connection string for the WooCommerce link database",
        example="Driver={FileMaker ODBC};Server=192.168.1.100;Database=WC_Link;UID=user;PWD=xxx",
    ),
    CredentialPrompt(
        key="wc_url",
        display_name="WooCommerce Store URL",
        description="Your WooCommerce store URL (with https://)",
        example="https://vitalseeds.co.uk",
    ),
    CredentialPrompt(
        key="wc_key",
        display_name="WooCommerce Consumer Key",
        description="WooCommerce REST API Consumer Key (starts with 'ck_')",
        example="ck_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    ),
    CredentialPrompt(
        key="wc_secret",
        display_name="WooCommerce Consumer Secret",
        description="WooCommerce REST API Consumer Secret (starts with 'cs_')",
        is_secret=True,
        example="cs_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
    ),
]


def is_interactive() -> bool:
    """
    Determine if running in an interactive terminal (not as a service).

    Uses multiple signals:
    1. Environment variable override for explicit control
    2. sys.stdin.isatty() - False when running as service
    3. Windows Session ID check (Session 0 = service)
    """
    # Allow explicit override via environment variable
    if os.environ.get("VSDATA_NON_INTERACTIVE"):
        return False

    # Check if stdin is a terminal
    if not sys.stdin.isatty():
        return False

    # On Windows, services run in Session 0
    if sys.platform == "win32":
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            process_id = kernel32.GetCurrentProcessId()
            session_id = ctypes.c_ulong()
            if kernel32.ProcessIdToSessionId(process_id, ctypes.byref(session_id)):
                # Session 0 is for services, Session 1+ for interactive users
                if session_id.value == 0:
                    return False
        except Exception:
            pass  # Fall back to isatty() result

    return True


def prompt_for_credentials(missing_keys: list[str]) -> dict[str, str]:
    """
    Interactively prompt user for missing credentials.

    Args:
        missing_keys: List of missing config keys (e.g., ["VSDATA_FM_CONNECTION_STRING"])

    Returns:
        Dict mapping config keys to user-provided values

    Raises:
        KeyboardInterrupt: If user cancels with Ctrl+C
    """
    print("\n" + "=" * 60)
    print("VS Data API - First Time Setup")
    print("=" * 60)
    print("\nThe following credentials are required to connect to your")
    print("FileMaker database and WooCommerce store.\n")
    print("Press Ctrl+C at any time to cancel.\n")

    credentials = {}

    # Convert missing keys to base names (strip VSDATA_ prefix)
    missing_base_keys = {key.replace("VSDATA_", "").lower() for key in missing_keys}

    for prompt_config in CREDENTIAL_PROMPTS:
        if prompt_config.key not in missing_base_keys:
            continue

        print("-" * 60)
        print(f"\n{prompt_config.display_name}")
        print(f"  {prompt_config.description}")
        if prompt_config.example:
            print(f"  Example: {prompt_config.example}")
        print()

        while True:
            try:
                if prompt_config.is_secret:
                    value = getpass.getpass("  Enter value (hidden): ")
                else:
                    value = input("  Enter value: ")

                value = value.strip()

                if not value:
                    print("  Value cannot be empty. Please try again.")
                    continue

                credentials[prompt_config.key] = value
                break

            except EOFError:
                # Handle piped input ending
                raise KeyboardInterrupt("Input stream closed")

    return credentials


def save_config_file(credentials: dict[str, str], config_path: Path) -> None:
    """
    Save credentials to INI config file.

    Creates parent directories if they don't exist.
    Preserves existing config values not being updated.

    Args:
        credentials: Dict of credential key -> value
        config_path: Path to config.ini file
    """
    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Load existing config if present
    parser = configparser.ConfigParser()
    if config_path.exists():
        parser.read(config_path)

    # Ensure [vsdata] section exists
    if "vsdata" not in parser:
        parser["vsdata"] = {}

    # Add/update credentials
    for key, value in credentials.items():
        parser["vsdata"][key] = value

    # Ensure [server] section exists with defaults
    if "server" not in parser:
        parser["server"] = {
            "host": "0.0.0.0",
            "port": "8432",
        }

    # Write config file
    with open(config_path, "w") as f:
        parser.write(f)

    print(f"\nConfiguration saved to: {config_path}")
