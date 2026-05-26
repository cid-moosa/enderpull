import argparse
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box

# Force UTF-8 output on Windows for emoji support
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from .api_modrinth import ModrinthAPI
from .downloader import download_file
from .updater import update_mods
from .modpack import export_modpack, import_modpack
from .cleaner import self_clean
from .config import DEFAULT_MODS_DIR, DEFAULT_MINECRAFT_DIR
from .exceptions import AntigravityError
from .fabric_manager import fabric_update, fabric_upgrade, fabric_update_if_configured
from .local_manager import list_installed_mods, search_local_mods, remove_local_mod

from rich_argparse import RichHelpFormatter

console = Console()


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def install_command(args):
    """Handles the 'install' command."""
    api = ModrinthAPI()

    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_MODS_DIR

    with console.status(f"[bold cyan]Resolving project '{args.target}'..."):
        try:
            slug = api.resolve_project_slug(args.target)
        except AntigravityError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)

    with console.status(f"[bold cyan]Finding latest version for '{slug}'..."):
        try:
            version_info = api.get_version(
                slug=slug,
                loader=args.loader,
                mc_version=args.mc_version
            )
        except AntigravityError as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            sys.exit(1)

    url = version_info["url"]
    filename = version_info["filename"]

    console.print(
        f"[bold green]Found version {version_info['version_number']}[/bold green] "
        f"-> [yellow]{filename}[/yellow]"
    )

    try:
        final_path = download_file(url, output_dir, filename)
        console.print(f"[bold green]Successfully downloaded[/bold green] to {final_path}")
    except AntigravityError as e:
        console.print(f"[bold red]Download failed:[/bold red] {e}")
        sys.exit(1)


def search_command(args):
    """Handles the 'search' command."""
    if args.local:
        # Local search
        mods_dir = Path(args.mods_dir) if args.mods_dir else DEFAULT_MODS_DIR
        with console.status(f"[bold cyan]Searching locally for '{args.query}'..."):
            matches = search_local_mods(args.query, mods_dir)
            
        if not matches:
            console.print(f"[yellow]No local mods found matching '{args.query}'.[/yellow]")
            return
            
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Mod Name")
        table.add_column("File Name")
        table.add_column("Version")
        table.add_column("Loader")
        
        for mod in matches:
            loader_style = "[bold magenta]Fabric[/bold magenta]" if mod["loader"] == "Fabric" else f"[yellow]{mod['loader']}[/yellow]"
            table.add_row(
                mod["name"],
                mod["filename"],
                mod["version"],
                loader_style
            )
            
        console.print(f"\n[bold green]Local matches for '{args.query}' ({len(matches)}):[/bold green]")
        console.print(table)
    else:
        # Remote Modrinth search
        api = ModrinthAPI()
        with console.status(f"[bold cyan]Searching Modrinth for '{args.query}'..."):
            try:
                hits = api.search_projects(args.query, limit=args.limit)
            except AntigravityError as e:
                console.print(f"[bold red]Error:[/bold red] {e}")
                sys.exit(1)
                
        if not hits:
            console.print(f"[yellow]No Modrinth projects found matching '{args.query}'.[/yellow]")
            return
            
        table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
        table.add_column("Title")
        table.add_column("Slug")
        table.add_column("Downloads")
        table.add_column("Loaders")
        table.add_column("Description")
        
        for hit in hits:
            loaders = ", ".join([l.capitalize() for l in hit.get("categories", []) if l in ["fabric", "forge", "neoforge", "quilt"]])
            downloads = f"{hit.get('downloads', 0):,}"
            table.add_row(
                hit.get("title", "Unknown"),
                f"[yellow]{hit.get('slug', '')}[/yellow]",
                downloads,
                loaders,
                hit.get("description", "").strip()
            )
            
        console.print(f"\n[bold green]Modrinth matches for '{args.query}':[/bold green]")
        console.print(table)


def remove_command(args):
    """Handles the 'remove' command."""
    mods_dir = Path(args.mods_dir) if args.mods_dir else DEFAULT_MODS_DIR
    with console.status(f"[bold cyan]Uninstalling '{args.target}'..."):
        deleted = remove_local_mod(args.target, mods_dir)
        
    if not deleted:
        console.print(f"[bold red]Error:[/bold red] No local mods matching '{args.target}' were found or successfully deleted.")
        sys.exit(1)
        
    for mod in deleted:
        console.print(f"[bold green]✓ Successfully removed[/bold green] [yellow]{mod['name']}[/yellow] ({mod['filename']})")


def list_command(args):
    """Handles the 'list' command or '--list' flag."""
    mods_dir = Path(args.mods_dir) if hasattr(args, "mods_dir") and args.mods_dir else DEFAULT_MODS_DIR
    with console.status("[bold cyan]Scanning installed mods..."):
        mods = list_installed_mods(mods_dir)
    
    if not mods:
        console.print("[yellow]No mods found in your mods directory.[/yellow]")
        return
        
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Mod Name")
    table.add_column("File Name")
    table.add_column("Version")
    table.add_column("Loader")
    
    for mod in mods:
        loader_style = "[bold magenta]Fabric[/bold magenta]" if mod["loader"] == "Fabric" else f"[yellow]{mod['loader']}[/yellow]"
        table.add_row(
            mod["name"],
            mod["filename"],
            mod["version"],
            loader_style
        )
        
    console.print(f"\n[bold green]Installed Mods ({len(mods)}):[/bold green]")
    console.print(table)


def update_command(args):
    """
    Handles the 'update' command.

    1. Updates all mods in the mods directory via Modrinth hashes.
    2. Then runs a non-interactive Fabric loader check — skips if up-to-date,
       and only acts if a config file already exists (no prompts).
    """
    output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_MODS_DIR
    update_mods(output_dir)
    fabric_update_if_configured(output_dir)


def fabric_update_command(args):
    """Handles the 'mc-dl fabric update' subcommand."""
    mods_dir = Path(args.mods_dir) if args.mods_dir else DEFAULT_MODS_DIR
    mc_version = args.mc_version if hasattr(args, "mc_version") else None
    fabric_update(mods_dir, mc_version=mc_version, force=args.force)


def fabric_upgrade_command(args):
    """Handles the 'mc-dl fabric upgrade' subcommand."""
    mods_dir = Path(args.mods_dir) if args.mods_dir else DEFAULT_MODS_DIR
    fabric_upgrade(args.new_mc_version, mods_dir)


def clear_command(args):
    """Clears the terminal screen."""
    import os
    os.system("cls" if os.name == "nt" else "clear")



# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------

def _build_fabric_parser(subparsers) -> None:
    """
    Adds the 'fabric' top-level command with its own nested subparsers:

        mc-dl fabric update [--mc-version X] [--mods-dir PATH] [--force]
        mc-dl fabric upgrade <new_mc_version> [--mods-dir PATH]
    """
    fabric_parser = subparsers.add_parser(
        "fabric",
        help="Manage the Fabric mod loader (update or upgrade)",
        description=(
            "[bold cyan]mc-dl fabric[/bold cyan] — Fabric Loader Manager\n\n"
            "Statefully manages your Fabric installation. Config is stored in "
            "[dim].enderpull_config.json[/dim] next to your mods/ folder."
        ),
        formatter_class=RichHelpFormatter,
    )

    fabric_sub = fabric_parser.add_subparsers(
        dest="fabric_command",
        required=True,
        help="Fabric subcommands",
    )

    # --- fabric update ---
    update_p = fabric_sub.add_parser(
        "update",
        help="Update Fabric loader to the latest version (keeps your MC version)",
        description=(
            "[bold cyan]mc-dl fabric update[/bold cyan] — Update Fabric Loader\n\n"
            "Queries the Fabric Meta API for the newest stable loader. If your "
            "installed version already matches, it skips the installation and "
            "prints ✅ Fabric is already up to date!"
        ),
        formatter_class=RichHelpFormatter,
    )
    update_p.add_argument(
        "--mc-version",
        dest="mc_version",
        metavar="VERSION",
        help="Override MC version (e.g. 1.21.1). Defaults to value in config "
             "or auto-detected from your .minecraft/versions directory.",
    )
    update_p.add_argument(
        "--mods-dir",
        help="Override the mods directory (config is stored in its parent folder).",
    )
    update_p.add_argument(
        "--force",
        action="store_true",
        help="Re-install even if Fabric is already up to date.",
    )

    # --- fabric upgrade ---
    upgrade_p = fabric_sub.add_parser(
        "upgrade",
        help="Upgrade to a new MC version, update Fabric, and upgrade all mods",
        description=(
            "[bold cyan]mc-dl fabric upgrade <new_mc_version>[/bold cyan] — Full Upgrade\n\n"
            "Installs Fabric for the target Minecraft version, then scans your "
            "mods folder and downloads the latest Fabric-compatible release of "
            "each mod from Modrinth. Mods with no compatible release are skipped "
            "with a warning and their old .jar files are left intact."
        ),
        formatter_class=RichHelpFormatter,
    )
    upgrade_p.add_argument(
        "new_mc_version",
        help="Target Minecraft version to upgrade to (e.g. 1.21.4)",
    )
    upgrade_p.add_argument(
        "--mods-dir",
        help="Override the default mods directory.",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main():
    RichHelpFormatter.styles["argparse.prog"] = "bold cyan"

    parser = argparse.ArgumentParser(
        prog="mc-dl",
        description=(
            "[bold cyan]EnderPull CLI - Mod Manager[/bold cyan]\n\n"
            "A blazing fast CLI for downloading and managing Minecraft mods "
            "natively via Modrinth."
        ),
        formatter_class=RichHelpFormatter,
    )

    parser.add_argument("--list", action="store_true", help="List all installed mods and exit")

    subparsers = parser.add_subparsers(dest="command", help="Subcommands")

    # --- install ---
    install_parser = subparsers.add_parser(
        "install", help="Download and install a mod by name or slug", formatter_class=RichHelpFormatter
    )
    install_parser.add_argument("target", help="The mod name or slug (e.g., 'sodium')")
    install_parser.add_argument("--loader", help="Filter by mod loader (e.g., fabric, forge, neoforge, quilt)")
    install_parser.add_argument("--mc-version", help="Filter by Minecraft version (e.g., 1.21.1)")
    install_parser.add_argument("--latest", action="store_true", help="Download the latest version (default behavior)")
    install_parser.add_argument("--output-dir", help="Override the default output directory")

    # --- search ---
    search_parser = subparsers.add_parser(
        "search",
        help="Search for mods online or locally",
        formatter_class=RichHelpFormatter,
    )
    search_parser.add_argument("query", help="The search query (e.g., 'sodium')")
    search_parser.add_argument("-l", "--local", action="store_true", help="Search locally in your mods folder instead of Modrinth")
    search_parser.add_argument("--limit", type=int, default=10, help="Limit the number of online search results (default: 10)")
    search_parser.add_argument("--mods-dir", help="Override the mods directory for local search")

    # --- remove ---
    remove_parser = subparsers.add_parser(
        "remove",
        help="Uninstall/delete a local mod",
        formatter_class=RichHelpFormatter,
    )
    remove_parser.add_argument("target", help="The name, id, or filename of the mod to remove")
    remove_parser.add_argument("--mods-dir", help="Override the default mods directory")

    # --- list ---
    list_parser = subparsers.add_parser(
        "list",
        help="List all locally installed mods",
        formatter_class=RichHelpFormatter,
    )
    list_parser.add_argument("--mods-dir", help="Override the default mods directory")

    # --- update ---
    update_parser = subparsers.add_parser(
        "update",
        help="Update all installed mods and check the Fabric loader",
        description=(
            "[bold cyan]mc-dl update[/bold cyan] — Update Mods + Fabric\n\n"
            "Updates all mods in your mods/ folder via Modrinth, then checks "
            "whether your Fabric loader needs updating (using the saved config). "
            "Run [bold]mc-dl fabric update[/bold] first if no config exists yet."
        ),
        formatter_class=RichHelpFormatter,
    )
    update_parser.add_argument("--output-dir", help="Override the default output directory")

    # --- export ---
    export_parser = subparsers.add_parser(
        "export", help="Export currently installed mods to a JSON modpack file",
        formatter_class=RichHelpFormatter
    )
    export_parser.add_argument("filename", help="The name of the JSON file (e.g., modpack.json)")
    export_parser.add_argument("--output-dir", help="Override the default mods directory")

    # --- import ---
    import_parser = subparsers.add_parser(
        "import", help="Import and download mods from a JSON modpack file",
        formatter_class=RichHelpFormatter
    )
    import_parser.add_argument("filename", help="The name of the JSON file (e.g., modpack.json)")
    import_parser.add_argument("--output-dir", help="Override the default mods directory")

    # --- self-clean ---
    subparsers.add_parser(
        "self-clean",
        help="Delete unnecessary source files from the installation directory",
        formatter_class=RichHelpFormatter,
    )

    # --- clear ---
    subparsers.add_parser(
        "clear",
        help="Clear the terminal screen",
        formatter_class=RichHelpFormatter,
    )

    # --- fabric (nested subcommands) ---
    _build_fabric_parser(subparsers)

    # -----------------------------------------------------------------------
    args = parser.parse_args()

    if args.list:
        list_command(args)
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "install":
        install_command(args)
    elif args.command == "search":
        search_command(args)
    elif args.command == "remove":
        remove_command(args)
    elif args.command == "list":
        list_command(args)
    elif args.command == "update":
        update_command(args)
    elif args.command == "export":
        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_MODS_DIR
        export_modpack(args.filename, output_dir)
    elif args.command == "import":
        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_MODS_DIR
        import_modpack(args.filename, output_dir)
    elif args.command == "self-clean":
        self_clean()
    elif args.command == "clear":
        clear_command(args)
    elif args.command == "fabric":
        if args.fabric_command == "update":
            fabric_update_command(args)
        elif args.fabric_command == "upgrade":
            fabric_upgrade_command(args)
