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
from .modpack import export_modpack, import_modpack
from .cleaner import self_clean
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

from rich_argparse import RichHelpFormatter

def main():
    # Set up styling for the help menu
    RichHelpFormatter.styles["argparse.prog"] = "bold cyan"
    
    parser = argparse.ArgumentParser(
        prog="mc-dl",
        description="[bold cyan]EnderPull CLI - Mod Manager[/bold cyan]\n\nA blazing fast CLI for downloading and managing Minecraft mods natively via Modrinth.",
        formatter_class=RichHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommands")
    
    # 'get' command
    get_parser = subparsers.add_parser("get", help="Download a mod by name or slug", formatter_class=RichHelpFormatter)
    get_parser.add_argument("target", help="The mod name or slug (e.g., 'sodium')")
    get_parser.add_argument("--loader", help="Filter by mod loader (e.g., fabric, forge, neoforge, quilt)")
    get_parser.add_argument("--mc-version", help="Filter by Minecraft version (e.g., 1.21.1)")
    get_parser.add_argument("--latest", action="store_true", help="Download the latest version (default behavior)")
    get_parser.add_argument("--output-dir", help="Override the default output directory")
    
    # 'update' command
    update_parser = subparsers.add_parser("update", help="Automatically update all installed mods", formatter_class=RichHelpFormatter)
    update_parser.add_argument("--output-dir", help="Override the default output directory")
    
    # 'export' command
    export_parser = subparsers.add_parser("export", help="Export currently installed mods to a JSON modpack file", formatter_class=RichHelpFormatter)
    export_parser.add_argument("filename", help="The name of the JSON file (e.g., modpack.json)")
    export_parser.add_argument("--output-dir", help="Override the default mods directory")

    # 'import' command
    import_parser = subparsers.add_parser("import", help="Import and download mods from a JSON modpack file", formatter_class=RichHelpFormatter)
    import_parser.add_argument("filename", help="The name of the JSON file (e.g., modpack.json)")
    import_parser.add_argument("--output-dir", help="Override the default mods directory")
    
    # 'self-clean' command
    subparsers.add_parser("self-clean", help="Delete unnecessary source files from the installation directory", formatter_class=RichHelpFormatter)
    
    args = parser.parse_args()
    
    if args.command == "get":
        get_command(args)
    elif args.command == "update":
        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_MODS_DIR
        update_mods(output_dir)
    elif args.command == "export":
        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_MODS_DIR
        export_modpack(args.filename, output_dir)
    elif args.command == "import":
        output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_MODS_DIR
        import_modpack(args.filename, output_dir)
    elif args.command == "self-clean":
        self_clean()
