"""
EnderPull — Fabric installation manager.

Implements two high-level operations:

  fabric_update(mods_dir, mc_version=None, force=False)
      Keep the current Minecraft version, update Fabric loader to the latest.
      Reads/writes a per-install config file. Skips the installation entirely
      if the loader version in the config already matches the latest from the
      Fabric Meta API (unless force=True).

  fabric_upgrade(new_mc_version, mods_dir)
      Move to a completely new Minecraft version, install the matching Fabric
      loader, then upgrade every mod in mods_dir. Mods with no compatible
      release are skipped with a clear warning; their old .jar files stay.

Both functions are stateful: they read from and write to
.enderpull_config.json (stored in mods_dir.parent, i.e. the .minecraft
folder or server root).
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import Progress, TextColumn, BarColumn, MofNCompleteColumn

from .api_fabric import FabricMetaAPI
from .api_modrinth import ModrinthAPI
from .config import DEFAULT_MINECRAFT_DIR
from .downloader import download_file
from .exceptions import AntigravityError, VersionNotFoundError
from .fabric_config import (
    detect_mc_version,
    load_config,
    prompt_install_type,
    prompt_mc_version,
    save_config,
)
from .updater import calculate_sha1

console = Console()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_installer_jar(tmp_dir: Path) -> Path:
    """
    Downloads the latest stable Fabric installer .jar to *tmp_dir*.
    Returns the full path to the saved file.
    """
    fabric_api = FabricMetaAPI()

    with console.status("[bold cyan]Fetching latest Fabric installer info..."):
        installer_info = fabric_api.get_latest_installer()

    installer_version = installer_info["version"]
    installer_url = installer_info["url"]
    jar_name = f"fabric-installer-{installer_version}.jar"

    console.print(
        f"[green]OK[/green] Latest Fabric installer: [bold]{installer_version}[/bold]"
    )

    jar_path = download_file(installer_url, tmp_dir, jar_name)
    return jar_path


def _run_fabric_installer(
    jar_path: Path,
    mc_version: str,
    install_type: str,
    target_dir: Path | None,
) -> None:
    """
    Runs the Fabric installer silently via subprocess, wrapped in a Rich
    spinner. Java's stdout/stderr are suppressed (DEVNULL).

    Client command:
        java -jar <jar> client -mcversion <mc_version> -noprofile

    Server command:
        java -jar <jar> server -mcversion <mc_version> -downloadMinecraft -dir <target_dir>

    Args:
        jar_path:     Path to the downloaded fabric-installer.jar.
        mc_version:   Target Minecraft version string.
        install_type: "client" or "server".
        target_dir:   Server root path (server installs only); None for client.
    """
    if install_type == "client":
        cmd = [
            "java", "-jar", str(jar_path),
            "client",
            "-mcversion", mc_version,
            "-noprofile",
        ]
    else:
        cmd = [
            "java", "-jar", str(jar_path),
            "server",
            "-mcversion", mc_version,
            "-downloadMinecraft",
            "-dir", str(target_dir),
        ]

    location_hint = str(target_dir) if target_dir else "your .minecraft folder"

    try:
        with console.status(
            f"[bold cyan]Installing Fabric {install_type} for "
            f"Minecraft {mc_version}[/bold cyan] [dim]({location_hint})[/dim]..."
        ):
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
    except FileNotFoundError:
        console.print(
            "[bold red]Error:[/bold red] 'java' was not found. "
            "Make sure Java is installed and on your PATH."
        )
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        console.print(
            f"[bold red]Error:[/bold red] Fabric installer exited with code "
            f"[bold]{exc.returncode}[/bold]."
        )
        sys.exit(1)

    console.print(
        f"[bold green]✅ Fabric {install_type} installed successfully "
        f"for Minecraft {mc_version}[/bold green] "
        f"[dim]→ {location_hint}[/dim]"
    )


def _resolve_mc_version_and_install_type(
    mc_version: str | None,
    minecraft_dir: Path,
    cfg: dict | None,
) -> tuple[str, str, Path | None]:
    """
    Resolves the mc_version, install_type, and (for servers) target_dir to use
    for the current run, consulting the config, auto-detection, and interactive
    prompts in that priority order.

    Returns:
        (mc_version, install_type, target_dir)
    """
    # --- mc_version ---
    if not mc_version:
        # 1. Try config
        if cfg and cfg.get("mc_version"):
            mc_version = cfg["mc_version"]
            console.print(
                f"[dim]Using saved MC version: [bold]{mc_version}[/bold][/dim]"
            )
        else:
            # 2. Try auto-detection
            detected = detect_mc_version(minecraft_dir)
            if detected:
                console.print(
                    f"[green]OK[/green] Auto-detected Minecraft version: "
                    f"[bold]{detected}[/bold]"
                )
                mc_version = detected
            else:
                # 3. Fall back to interactive prompt
                console.print(
                    "[yellow]Could not auto-detect your Minecraft version.[/yellow]"
                )
                mc_version = prompt_mc_version()

    # --- install_type / target_dir ---
    if cfg and cfg.get("install_type"):
        install_type = cfg["install_type"]
        # For server installs, reconstruct target_dir from saved mods_dir parent
        if install_type == "server" and cfg.get("mods_dir"):
            target_dir: Path | None = Path(cfg["mods_dir"]).parent
        else:
            target_dir = None
        console.print(
            f"[dim]Using saved install type: [bold]{install_type}[/bold][/dim]"
        )
    else:
        install_type, target_dir = prompt_install_type()

    return mc_version, install_type, target_dir


# ---------------------------------------------------------------------------
# Public commands
# ---------------------------------------------------------------------------

def fabric_update(
    mods_dir: Path,
    mc_version: str | None = None,
    *,
    force: bool = False,
    silent: bool = False,
) -> None:
    """
    Update Command: keep the Minecraft version, install the latest Fabric loader.

    Args:
        mods_dir:   Path to the mods/ directory (used to locate the config).
        mc_version: Override MC version. If None, reads from config / auto-detects.
        force:      Skip the up-to-date check and always (re-)install.
        silent:     If True, suppress the rule header (used when called from
                    the global 'update' command).

    Steps:
      1. Load config from mods_dir.parent.
      2. Resolve mc_version and install_type (config → auto-detect → prompt).
      3. Query the Fabric Meta API for the latest compatible loader version.
      4. Compare against the saved loader version — skip if up-to-date (unless force).
      5. Download installer, run silently, save state to config.
    """
    if not silent:
        console.rule("[bold cyan]Fabric Update[/bold cyan]")

    minecraft_dir = mods_dir.parent
    cfg = load_config(minecraft_dir)

    # Step 2: resolve mc_version, install_type, target_dir
    mc_version, install_type, target_dir = _resolve_mc_version_and_install_type(
        mc_version, minecraft_dir, cfg
    )

    fabric_api = FabricMetaAPI()

    # Step 3: get the latest loader version for this MC version
    with console.status(
        f"[bold cyan]Querying Fabric Meta API for latest loader "
        f"compatible with MC {mc_version}..."
    ):
        try:
            latest_loader = fabric_api.get_latest_loader_for_mc(mc_version)
        except AntigravityError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    # Step 4: up-to-date check
    saved_loader = cfg.get("fabric_loader_version") if cfg else None
    if not force and saved_loader and saved_loader == latest_loader:
        console.print(
            f"[bold green]✅ Fabric is already up to date![/bold green] "
            f"[dim](loader {latest_loader} for MC {mc_version})[/dim]"
        )
        return

    if saved_loader and saved_loader != latest_loader:
        console.print(
            f"[green]OK[/green] Loader update available: "
            f"[dim]{saved_loader}[/dim] → [bold]{latest_loader}[/bold]"
        )
    else:
        console.print(
            f"[green]OK[/green] Latest stable loader for MC [bold]{mc_version}[/bold]: "
            f"[bold]{latest_loader}[/bold]"
        )

    # Step 5: download installer and run silently
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            jar_path = _fetch_installer_jar(tmp_path)
        except AntigravityError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

        _run_fabric_installer(jar_path, mc_version, install_type, target_dir)

    # Save updated state
    save_config(minecraft_dir, {
        "install_type": install_type,
        "mc_version": mc_version,
        "fabric_loader_version": latest_loader,
        "mods_dir": str(mods_dir),
    })
    console.print(
        f"[dim]Config saved → "
        f"{minecraft_dir / '.enderpull_config.json'}[/dim]"
    )


def fabric_update_if_configured(mods_dir: Path) -> None:
    """
    Called by the global 'update' command after updating mods.

    If a config exists and records a client install, runs fabric_update()
    in non-interactive silent mode (no prompts, no rule header).
    If no config exists, prints a soft hint to the user instead of prompting.

    Server installs are intentionally skipped here because 'mc-dl update'
    scans the mods/ folder which doesn't apply to servers.
    """
    minecraft_dir = mods_dir.parent
    cfg = load_config(minecraft_dir)

    if not cfg:
        console.print(
            "\n[dim]Tip: run [bold]mc-dl fabric update[/bold] to also manage "
            "your Fabric loader.[/dim]"
        )
        return

    install_type = cfg.get("install_type", "client")
    if install_type == "server":
        # Server installs don't use the mods/ dir in the same way; skip silently.
        return

    console.rule("[bold cyan]Fabric Loader[/bold cyan]")
    fabric_update(mods_dir, mc_version=None, force=False, silent=True)


def fabric_upgrade(new_mc_version: str, mods_dir: Path) -> None:
    """
    Upgrade Command: switch to a new Minecraft version, update Fabric, upgrade mods.

    Steps:
      1. Resolve install_type from config (or prompt if missing).
      2. Install Fabric for new_mc_version (silently).
      3. Scan mods_dir for .jar files.
      4. Hash each mod, batch-resolve via Modrinth, fetch new compatible versions.
      5. Download new jars; delete old ones only on success.
         Mods with no compatible release are skipped with a clear warning.
      6. Save new mc_version and fabric_loader_version to config.
    """
    console.rule("[bold cyan]Fabric Upgrade[/bold cyan]")

    minecraft_dir = mods_dir.parent
    cfg = load_config(minecraft_dir)

    # Resolve install_type
    if cfg and cfg.get("install_type"):
        install_type = cfg["install_type"]
        if install_type == "server" and cfg.get("mods_dir"):
            target_dir: Path | None = Path(cfg["mods_dir"]).parent
        else:
            target_dir = None
        console.print(
            f"[dim]Using saved install type: [bold]{install_type}[/bold][/dim]"
        )
    else:
        install_type, target_dir = prompt_install_type()

    # --- Step 1: Get loader version & install Fabric for new version ---
    fabric_api = FabricMetaAPI()
    with console.status(
        f"[bold cyan]Querying Fabric Meta API for loader "
        f"compatible with MC {new_mc_version}..."
    ):
        try:
            loader_version = fabric_api.get_latest_loader_for_mc(new_mc_version)
        except AntigravityError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    console.print(
        f"[green]OK[/green] Target loader for MC [bold]{new_mc_version}[/bold]: "
        f"[bold]{loader_version}[/bold]"
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        try:
            jar_path = _fetch_installer_jar(tmp_path)
        except AntigravityError as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

        _run_fabric_installer(jar_path, new_mc_version, install_type, target_dir)

    # --- Step 2: Scan mods directory ---
    console.rule("[bold cyan]Scanning Mods Directory[/bold cyan]")

    if not mods_dir.exists() or not mods_dir.is_dir():
        console.print(
            f"[bold red]Error:[/bold red] The mods directory "
            f"[bold]{mods_dir}[/bold] does not exist. "
            f"Use [cyan]--mods-dir[/cyan] to specify its location."
        )
        sys.exit(1)

    jar_files = list(mods_dir.glob("*.jar"))
    if not jar_files:
        console.print(
            f"[yellow]No .jar files found in {mods_dir}. "
            f"Fabric has been installed but no mods were upgraded.[/yellow]"
        )
        _save_upgrade_config(minecraft_dir, new_mc_version, loader_version,
                             install_type, mods_dir)
        return

    console.print(f"[green]OK[/green] Found [bold]{len(jar_files)}[/bold] mod(s) to process.\n")

    # --- Step 3: Hash all mods, batch-lookup via Modrinth ---
    file_hashes: dict[str, Path] = {}

    with Progress(
        TextColumn("[cyan]Hashing mods..."),
        BarColumn(),
        MofNCompleteColumn(),
        transient=True,
    ) as progress:
        task = progress.add_task("hashing", total=len(jar_files))
        for jar in jar_files:
            file_hashes[calculate_sha1(jar)] = jar
            progress.update(task, advance=1)

    console.print(f"[green]OK[/green] Hashed [bold]{len(file_hashes)}[/bold] mod(s).")

    modrinth_api = ModrinthAPI()

    with console.status("[bold cyan]Looking up installed mods on Modrinth..."):
        try:
            version_info_map = modrinth_api.get_versions_from_hashes(
                list(file_hashes.keys())
            )
        except AntigravityError as exc:
            console.print(
                f"[bold red]Error querying Modrinth API:[/bold red] {exc}"
            )
            sys.exit(1)

    console.print(
        f"[green]OK[/green] Modrinth recognised "
        f"[bold]{len(version_info_map)}[/bold] of [bold]{len(file_hashes)}[/bold] mod(s).\n"
    )

    # --- Step 4: Upgrade each recognised mod ---
    console.rule("[bold cyan]Upgrading Mods[/bold cyan]")

    results: list[dict] = []

    for file_hash, old_jar in file_hashes.items():
        if file_hash not in version_info_map:
            console.print(
                f"[dim yellow]⚠  Skipping[/dim yellow] [bold]{old_jar.name}[/bold]"
                f" — not found on Modrinth (may be a local or private mod)."
            )
            results.append({
                "name": old_jar.name,
                "status": "Skipped (not on Modrinth)",
                "old_version": "Unknown",
                "new_version": "—",
            })
            continue

        version_info = version_info_map[file_hash]
        project_id = version_info["project_id"]
        old_version_num = version_info.get("version_number", "Unknown")

        mod_display_name = version_info.get("name") or old_jar.name
        if mod_display_name.endswith(".jar"):
            mod_display_name = mod_display_name[:-4]

        try:
            latest = modrinth_api.get_version(
                slug=project_id,
                loader="fabric",
                mc_version=new_mc_version,
            )
        except VersionNotFoundError:
            console.print(
                f"[bold yellow]⚠  WARNING:[/bold yellow] "
                f"[bold]{mod_display_name}[/bold] has no release for "
                f"MC [bold]{new_mc_version}[/bold] + Fabric yet. "
                f"Old file kept intact."
            )
            results.append({
                "name": mod_display_name,
                "status": "⚠ Left Behind (no update available)",
                "old_version": old_version_num,
                "new_version": "—",
            })
            continue
        except AntigravityError as exc:
            console.print(
                f"[bold red]Error[/bold red] while checking "
                f"[bold]{mod_display_name}[/bold]: {exc}. Skipping."
            )
            results.append({
                "name": mod_display_name,
                "status": "Error (skipped)",
                "old_version": old_version_num,
                "new_version": "—",
            })
            continue

        new_version_num = latest.get("version_number", "Unknown")
        new_filename = latest["filename"]
        new_url = latest["url"]
        new_jar_path = mods_dir / new_filename

        console.print(
            f"[bold cyan]↓ Upgrading[/bold cyan] [bold]{mod_display_name}[/bold]  "
            f"[dim]{old_version_num}[/dim] → [bold green]{new_version_num}[/bold green]"
        )
        try:
            download_file(new_url, mods_dir, new_filename)
        except AntigravityError as exc:
            console.print(
                f"[bold red]Download failed for {mod_display_name}:[/bold red] {exc}. "
                f"Old file kept intact."
            )
            results.append({
                "name": mod_display_name,
                "status": "Error (download failed)",
                "old_version": old_version_num,
                "new_version": "—",
            })
            continue

        if old_jar != new_jar_path and old_jar.exists():
            try:
                os.remove(old_jar)
            except OSError as exc:
                console.print(
                    f"[yellow]Warning: could not delete old file "
                    f"{old_jar.name}: {exc}[/yellow]"
                )

        results.append({
            "name": mod_display_name,
            "status": "✅ Upgraded",
            "old_version": old_version_num,
            "new_version": new_version_num,
        })

    _print_upgrade_summary(results, new_mc_version)

    # Save updated state
    _save_upgrade_config(minecraft_dir, new_mc_version, loader_version,
                         install_type, mods_dir)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _save_upgrade_config(
    minecraft_dir: Path,
    mc_version: str,
    loader_version: str,
    install_type: str,
    mods_dir: Path,
) -> None:
    save_config(minecraft_dir, {
        "install_type": install_type,
        "mc_version": mc_version,
        "fabric_loader_version": loader_version,
        "mods_dir": str(mods_dir),
    })
    console.print(
        f"\n[dim]Config saved → "
        f"{minecraft_dir / '.enderpull_config.json'}[/dim]"
    )


def _print_upgrade_summary(results: list[dict], new_mc_version: str) -> None:
    """Renders a Rich table summarising the upgrade results."""
    console.print()
    console.rule("[bold]Upgrade Summary[/bold]")

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Mod Name", min_width=25)
    table.add_column("Status", min_width=32)
    table.add_column("Old Version", min_width=14)
    table.add_column(f"New Version (MC {new_mc_version})", min_width=14)

    results.sort(key=lambda r: r["name"].lower())

    upgraded = left_behind = skipped = errors = 0

    for r in results:
        status = r["status"]
        if "Upgraded" in status:
            status_rich = f"[bold green]{status}[/bold green]"
            upgraded += 1
        elif "Left Behind" in status:
            status_rich = f"[bold yellow]{status}[/bold yellow]"
            left_behind += 1
        elif "Skipped" in status:
            status_rich = f"[dim]{status}[/dim]"
            skipped += 1
        else:
            status_rich = f"[bold red]{status}[/bold red]"
            errors += 1

        table.add_row(r["name"], status_rich, r["old_version"], r["new_version"])

    console.print(table)

    console.print(
        f"\n[bold]Results:[/bold] "
        f"[green]{upgraded} upgraded[/green]  "
        f"[yellow]{left_behind} left behind[/yellow]  "
        f"[dim]{skipped} skipped[/dim]  "
        f"[red]{errors} errors[/red]"
    )

    if left_behind:
        console.print(
            "\n[bold yellow]Heads up:[/bold yellow] "
            f"{left_behind} mod(s) have no release for MC {new_mc_version} + Fabric yet. "
            "Their old .jar files are still in your mods folder. "
            "Check the mod's Modrinth page and remove them manually when ready."
        )
