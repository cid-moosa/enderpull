import hashlib
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import Progress, TextColumn, BarColumn, MofNCompleteColumn

from .api_modrinth import ModrinthAPI
from .downloader import download_file
from .exceptions import AntigravityError, VersionNotFoundError

console = Console()

def calculate_sha1(file_path: Path) -> str:
    """Calculates the SHA-1 hash of a file."""
    sha1 = hashlib.sha1()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha1.update(chunk)
    return sha1.hexdigest()

def update_mods(output_dir: Path):
    """Scans the output_dir for .jar files and updates them via Modrinth API."""
    if not output_dir.exists() or not output_dir.is_dir():
        console.print(f"[bold red]Error:[/bold red] The directory {output_dir} does not exist.")
        return

    jar_files = list(output_dir.glob("*.jar"))
    if not jar_files:
        console.print(f"[yellow]No .jar files found in {output_dir}. Nothing to update.[/yellow]")
        return

    file_hashes = {}
    
    with Progress(
        TextColumn("[cyan]Hashing local mods..."),
        BarColumn(),
        MofNCompleteColumn(),
        transient=True
    ) as progress:
        task = progress.add_task("Hashing", total=len(jar_files))
        for jar in jar_files:
            file_hashes[calculate_sha1(jar)] = jar
            progress.update(task, advance=1)
            
    console.print(f"[green]OK Hashed {len(jar_files)} local mods.[/green]")

    api = ModrinthAPI()
    
    mod_results = []

    with console.status("[yellow]Querying Modrinth API for updates...") as status:
        try:
            version_info_map = api.get_versions_from_hashes(list(file_hashes.keys()))
        except AntigravityError as e:
            console.print(f"[bold red]Error querying Modrinth API:[/bold red] {e}")
            return

        status.update("[yellow]Resolving latest versions for current environment...")

        for file_hash, jar_path in file_hashes.items():
            if file_hash not in version_info_map:
                mod_results.append({
                    "name": jar_path.name,
                    "status": "Unavailable",
                    "version_display": "Unknown",
                    "game_version": "Unknown",
                    "loader": "Unknown",
                    "release_type": "Unknown"
                })
                continue

            version_info = version_info_map[file_hash]
            project_id = version_info["project_id"]
            loaders = version_info.get("loaders", [])
            game_versions = version_info.get("game_versions", [])
            old_date = version_info.get("date_published", "")
            old_version_num = version_info.get("version_number", "Unknown")
            old_version_type = version_info.get("version_type", "Unknown")
            
            display_game_version = game_versions[0] if game_versions else "Unknown"
            display_loader = loaders[0].capitalize() if loaders else "Unknown"
            
            # Extract a human-readable name: use the version name or fallback to filename
            project_name = version_info.get("name")
            if not project_name:
                project_name = jar_path.name
            
            # Clean up the name if it's too long or contains the file extension
            if project_name.endswith(".jar"):
                project_name = project_name[:-4]

            try:
                latest_version = api.get_version(slug=project_id, loader=loaders, mc_version=game_versions)
                new_date = latest_version.get("date_published", "")
                new_version_num = latest_version.get("version_number", "Unknown")
                new_version_type = latest_version.get("version_type", "Unknown")
                
                if new_date > old_date:
                    # Suspend status briefly so we don't interleave with downloader progress bar
                    status.stop()
                    console.print(f"[bold cyan]Updating[/bold cyan] [yellow]{project_name}[/yellow]...")
                    new_file_path = download_file(latest_version["url"], output_dir, latest_version["filename"])
                    
                    if new_file_path != jar_path:
                        try:
                            os.remove(jar_path)
                        except OSError as e:
                            console.print(f"[yellow]Warning: Could not delete old file {jar_path.name}: {e}[/yellow]")
                    
                    mod_results.append({
                        "name": project_name,
                        "status": "Updated",
                        "version_display": f"{old_version_num} -> {new_version_num}",
                        "game_version": display_game_version,
                        "loader": display_loader,
                        "release_type": new_version_type
                    })
                    status.start()
                else:
                    mod_results.append({
                        "name": project_name,
                        "status": "Up to Date",
                        "version_display": old_version_num,
                        "game_version": display_game_version,
                        "loader": display_loader,
                        "release_type": old_version_type
                    })
                    
            except VersionNotFoundError:
                mod_results.append({
                    "name": jar_path.name,
                    "status": "Unavailable",
                    "version_display": old_version_num,
                    "game_version": display_game_version,
                    "loader": display_loader,
                    "release_type": old_version_type
                })
            except AntigravityError as e:
                mod_results.append({
                    "name": jar_path.name,
                    "status": "Unavailable",
                    "version_display": "Unknown",
                    "game_version": "Unknown",
                    "loader": "Unknown",
                    "release_type": "Unknown"
                })
                
    console.print("[green]OK Update check completed![/green]")

    # Print summary tables
    console.print("\n[bold]Update Summary[/bold]")
    
    # Sort alphabetically by name (case insensitive)
    mod_results.sort(key=lambda x: x["name"].lower())
    
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Mod Name")
    table.add_column("Status")
    table.add_column("Mod Version")
    table.add_column("Game Version")
    table.add_column("Loader")
    table.add_column("Release Type")
    
    for mod in mod_results:
        # Format status
        if mod["status"] == "Updated":
            status_display = "[bold green]🚀 Updated[/bold green]"
        elif mod["status"] == "Up to Date":
            status_display = "[cyan]✅ Up to Date[/cyan]"
        else:
            status_display = "[dim yellow]⚠️ Unrecognized[/dim yellow]"
            
        # Format release type
        rtype = mod["release_type"].lower()
        if rtype == "release":
            rtype_display = "[green]🟢 Release[/green]"
        elif rtype == "beta":
            rtype_display = "[yellow]🟡 Beta[/yellow]"
        elif rtype == "alpha":
            rtype_display = "[red]🔴 Alpha[/red]"
        else:
            rtype_display = "[dim]Unknown[/dim]"
            
        table.add_row(
            mod["name"],
            status_display,
            mod["version_display"],
            mod["game_version"],
            mod["loader"],
            rtype_display
        )
        
    console.print(table)
