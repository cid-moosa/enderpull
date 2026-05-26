"""
EnderPull — Fabric state persistence & environment helpers.

Manages a lightweight per-install JSON config file written alongside the
Minecraft installation (in the parent of the mods/ directory, i.e. the
.minecraft folder or server root).

Config file: .enderpull_config.json
Schema:
    {
        "install_type":          "client" | "server",
        "mc_version":            "1.21.1",
        "fabric_loader_version": "0.19.2",
        "mods_dir":              "/absolute/path/to/mods"
    }

Public API
----------
get_config_path(base_dir)       -> Path
load_config(base_dir)           -> dict | None
save_config(base_dir, data)     -> None
detect_mc_version(minecraft_dir)-> str | None
prompt_install_type()           -> tuple[str, Path | None]
"""

import json
import re
import sys
from pathlib import Path

from rich.console import Console

console = Console()

CONFIG_FILENAME = ".enderpull_config.json"

# Regex that matches standard MC release strings like "1.21", "1.21.1", "1.8.9"
# Excludes loader-prefixed entries like "fabric-loader-0.19.2-1.21.1"
_MC_VERSION_RE = re.compile(r"^\d+\.\d+(\.\d+)?$")


# ---------------------------------------------------------------------------
# Config file helpers
# ---------------------------------------------------------------------------

def get_config_path(base_dir: Path) -> Path:
    """
    Returns the path to the .enderpull_config.json file for a given
    base directory (the .minecraft folder or server root — i.e. the
    *parent* of the mods/ directory).
    """
    return base_dir / CONFIG_FILENAME


def load_config(base_dir: Path) -> dict | None:
    """
    Reads and returns the config dict, or None if the file is missing or
    cannot be parsed.

    Args:
        base_dir: The .minecraft folder (or server root). Not the mods/ dir.
    """
    path = get_config_path(base_dir)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except (json.JSONDecodeError, OSError):
        return None


def save_config(base_dir: Path, data: dict) -> None:
    """
    Writes *data* to the config file, merging with any existing content so
    that callers only need to pass the keys they want to update.

    Args:
        base_dir: The .minecraft folder (or server root).
        data:     Keys to write / overwrite.

    Raises:
        OSError: if the file cannot be written (propagated to caller).
    """
    path = get_config_path(base_dir)

    # Load existing config so we only overwrite the keys we're given.
    existing: dict = {}
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, dict):
                existing = {}
        except (json.JSONDecodeError, OSError):
            existing = {}

    existing.update(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)


# ---------------------------------------------------------------------------
# Minecraft version auto-detection
# ---------------------------------------------------------------------------

def detect_mc_version(minecraft_dir: Path) -> str | None:
    """
    Attempts to auto-detect the most recently used Minecraft release version
    by scanning the ``versions/`` subdirectory of *minecraft_dir*.

    Strategy:
      1. List all subdirectories of ``<minecraft_dir>/versions/``.
      2. Filter to entries whose names match a plain version pattern
         (e.g. "1.21.1") — excluding loader-prefixed entries like
         "fabric-loader-0.19.2-1.21.1".
      3. Return the name of the most recently *modified* directory (the
         one the launcher last created or updated), which correlates with
         the last-played version.

    Returns:
        A version string such as "1.21.1", or None if detection fails.
    """
    versions_dir = minecraft_dir / "versions"
    if not versions_dir.is_dir():
        return None

    candidates: list[tuple[float, str]] = []

    for entry in versions_dir.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name
        if _MC_VERSION_RE.match(name):
            try:
                mtime = entry.stat().st_mtime
                candidates.append((mtime, name))
            except OSError:
                continue

    if not candidates:
        return None

    # Most recently modified first
    candidates.sort(reverse=True)
    return candidates[0][1]


# ---------------------------------------------------------------------------
# Interactive prompting (moved here from fabric_manager so it is reusable)
# ---------------------------------------------------------------------------

def prompt_install_type() -> tuple[str, Path | None]:
    """
    Interactively asks the user whether they are installing for a client or
    server, validates the response, and — for server installs — asks for a
    target directory.

    Returns:
        A 2-tuple of (install_type, target_dir) where:
            install_type  – "client" or "server"
            target_dir    – Path for server installs; None for client installs.
    """
    valid = {"client", "server"}

    while True:
        try:
            raw = input("\nAre you installing for a client or a server? (client/server): ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Installation cancelled.[/yellow]")
            sys.exit(0)

        choice = raw.strip().lower()
        if choice in valid:
            break
        console.print(
            f"[bold red]Invalid choice:[/bold red] '{raw.strip()}' — "
            "please type [bold]client[/bold] or [bold]server[/bold]."
        )

    target_dir: Path | None = None

    if choice == "server":
        try:
            raw_dir = input(
                "Enter the target server directory "
                f"(press Enter to use current directory [{Path.cwd()}]): "
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Installation cancelled.[/yellow]")
            sys.exit(0)

        stripped = raw_dir.strip()
        target_dir = Path(stripped) if stripped else Path.cwd()

        if not target_dir.exists():
            console.print(
                f"[yellow]Directory '{target_dir}' does not exist — creating it.[/yellow]"
            )
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                console.print(
                    f"[bold red]Error:[/bold red] Could not create directory: {exc}"
                )
                sys.exit(1)

    return choice, target_dir


def prompt_mc_version() -> str:
    """
    Interactively asks the user for their Minecraft version. Used as a
    fallback when auto-detection fails.

    Returns:
        A non-empty version string as entered by the user.
    """
    while True:
        try:
            raw = input("Enter your Minecraft version (e.g. 1.21.1): ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Cancelled.[/yellow]")
            sys.exit(0)

        version = raw.strip()
        if version:
            return version
        console.print("[bold red]Version cannot be blank.[/bold red] Please try again.")
