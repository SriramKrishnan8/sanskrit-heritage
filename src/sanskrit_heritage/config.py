#!/usr/bin/env python3
# src/sanskrit_heritage/config.py

import os
import sys
import platform
from pathlib import Path

# Base directory of the installed package
# This points to src/sanskrit_heritage/
PACKAGE_DIR = Path(__file__).parent.resolve()

# The assets folder where you will bundle binaries and data
ASSETS_DIR = PACKAGE_DIR / "assets"


def get_bundled_binary_path():
    """
    Returns the bundled binary path for the current OS.
    Checks for multiple possible filenames (interface2.cgi, interface, etc.)
    """
    system = platform.system().lower()

    if system == "linux":
        base_dir = ASSETS_DIR / "bin" / "linux"
    elif system == "darwin":  # macOS
        base_dir = ASSETS_DIR / "bin" / "macos"
    else:
        # Windows users generally need WSL or Docker (Phase 2)
        return None

    # 2. Check for common binary names in that folder
    possible_names = [
        "interface2.cgi", "interface2", "sktgraph2.cgi", "sktgraph2"
    ]

    for name in possible_names:
        binary_path = base_dir / name
        if binary_path.exists():
            return binary_path

    return None


def resolve_binary_path(custom_path=None):
    """
    Determines the correct binary path using the following priority:
    1. Custom path passed at runtime (for testing/overrides).
    2. Environment variable 'SANSKRIT_HERITAGE_BIN'.
    3. Standard Linux Installation (/usr/lib/cgi-bin/SKT/...)
    3. Bundled binary inside the package (src/sanskrit_heritage/assets/...).
    """
    # 1. Priority: Runtime Argument
    if custom_path:
        path = Path(custom_path)
        if path.exists():
            return path
        raise FileNotFoundError(f"Custom binary path not found: {custom_path}")

    # 2. Priority: Environment Variable
    env_path = os.getenv("SANSKRIT_HERITAGE_BIN")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path
        # Warn but continue to fallback? Or raise? Let's fallback.
        print(
            f"Warning: SANSKRIT_HERITAGE_BIN {env_path} missing. "
            "Trying bundled.",
            file=sys.stderr
        )

    # 3. Standard Linux Installation
    # Common names: sktgraph2 or interface2
    linux_paths = [
        Path("/usr/lib/cgi-bin/SKT/sktgraph2"),
        Path("/usr/lib/cgi-bin/SKT/sktgraph2.cgi"),
        Path("/usr/lib/cgi-bin/SKT/interface2"),
        Path("/usr/lib/cgi-bin/SKT/interface2.cgi")
    ]
    for path in linux_paths:
        if path.exists():
            return path

    # 3. Priority: Bundled Binary
    bundled = get_bundled_binary_path()
    if bundled and bundled.exists():
        return bundled

    return None


def get_data_path(binary_path):
    """
    Determines where the 'data' folder is relative to the binary.

    Scenario A (Bundled):
    Binary is in assets/bin/linux/, Data is in assets/data/

    Scenario B (Linux Std):
    Binary in /usr/lib/cgi-bin/SKT/, Data in /var/www/html/SKT/DATA/
    """
    # Scenario A: Bundled (We check if 'assets' is in the path)
    if ASSETS_DIR in binary_path.parents:
        return ASSETS_DIR  # We set CWD to assets/ so binary finds ./data

    # Scenario B: Standard Linux Split
    # If binary is at /usr/lib/cgi-bin/SKT/sktgraph2
    # We suspect data is at /var/www/html/SKT/DATA/
    # The CWD must be the folder containing 'DATA'.

    # Check common data locations
    potential_data_roots = [
        Path("/var/www/html/SKT/"),
        # Path("/var/www/html/sanskrit/"),
        binary_path.parent  # Fallback: Data is next to binary
    ]

    for root in potential_data_roots:
        if (root / "DATA").exists():
            return root
        if (root / "data").exists():
            return root

    # Default fallback
    return binary_path.parent
