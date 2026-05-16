import argparse
import sys
from pathlib import Path
from rich.console import Console

# Force UTF-8 output on Windows for emoji support
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from .api_modrinth import ModrinthAPI
from .downloader import download_file
from .updater import update_mods
from .config import DEFAULT_MODS_DIR
from .exceptions import AntigravityError

console = Console()

def get_command(args):
    """Handles the 'get' command."""
    api = ModrinthAPI()
    
    # Determine output directory
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
    
    console.print(f"[bold green]Found version {version_info['version_number']}[/bold green] -> [yellow]{filename}[/yellow]")
    
    try:
        final_path = download_file(url, output_dir, filename)
        console.print(f"[bold green]Successfully downloaded[/bold green] to {final_path}")
    except AntigravityError as e:
        console.print(f"[bold red]Download failed:[/bold red] {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        prog="mc-dl",
        description="A blazing fast CLI for downloading Minecraft mods."
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")
    
    # 'get' command
    get_parser = subparsers.add_parser("get", help="Download a mod by name or slug")
    get_parser.add_argument("target", help="The mod name or slug (e.g., 'sodium')")
    get_parser.add_argument("--loader", help="Filter by mod loader (e.g., fabric, forge, neoforge, quilt)")
    get_parser.add_argument("--mc-version", help="Filter by Minecraft version (e.g., 1.21.1)")
    get_parser.add_argument("--latest", action="store_true", help="Download the latest version (default behavior)")
    get_parser.add_argument("--output-dir", help="Override the default output directory")
    
    # 'update' command
    update_parser = subparsers.add_parser("update", help="Automatically update all installed mods")
    update_parser.add_argument("--output-dir", help="Override the default output directory")
    
    args = parser.parse_args()
    
    if args.command == "get":
        get_command(args)
    elif args.command == "update":
        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_MODS_DIR
        update_mods(output_dir)
