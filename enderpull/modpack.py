import json
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import box
from rich.progress import Progress, TextColumn, BarColumn, MofNCompleteColumn

from .api_modrinth import ModrinthAPI
from .updater import calculate_sha1
from .downloader import download_file
from .exceptions import AntigravityError

console = Console()

def export_modpack(filename: str, output_dir: Path):
    if not output_dir.exists() or not output_dir.is_dir():
        console.print(f"[bold red]Error:[/bold red] The directory {output_dir} does not exist.")
        return

    jar_files = list(output_dir.glob("*.jar"))
    if not jar_files:
        console.print(f"[yellow]No .jar files found in {output_dir}. Nothing to export.[/yellow]")
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
            
    api = ModrinthAPI()
    
    with console.status("[yellow]Querying Modrinth API for modpack data...") as status:
        try:
            version_info_map = api.get_versions_from_hashes(list(file_hashes.keys()))
        except AntigravityError as e:
            console.print(f"[bold red]Error querying Modrinth API:[/bold red] {e}")
            return

    modpack_data = []
    unrecognized_files = []

    for file_hash, jar_path in file_hashes.items():
        if file_hash not in version_info_map:
            unrecognized_files.append(jar_path.name)
            continue
            
        version_info = version_info_map[file_hash]
        
        # Determine human-readable name
        project_name = version_info.get("name")
        if not project_name:
            project_name = jar_path.name
        if project_name.endswith(".jar"):
            project_name = project_name[:-4]

        # Extract loaders and game_versions
        loaders = version_info.get("loaders", [])
        game_versions = version_info.get("game_versions", [])

        display_game_version = game_versions[0] if game_versions else "Unknown"
        display_loader = loaders[0].capitalize() if loaders else "Unknown"

        mod_entry = {
            "name": project_name,
            "project_id": version_info.get("project_id"),
            "version_id": version_info.get("id"),
            "loader": display_loader,
            "game_version": display_game_version,
            "filename": jar_path.name
        }
        
        # If the file has files array, try to find the direct URL
        for file_data in version_info.get("files", []):
            if file_data.get("primary", False) or len(version_info["files"]) == 1:
                mod_entry["url"] = file_data.get("url")
                break
                
        modpack_data.append(mod_entry)

    # Write to JSON
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(modpack_data, f, indent=4)
        console.print(f"[bold green]✓ Successfully exported {len(modpack_data)} mods to {filename}[/bold green]")
    except IOError as e:
        console.print(f"[bold red]Failed to write to {filename}:[/bold red] {e}")

    # Print unrecognized files warning
    if unrecognized_files:
        console.print("\n")
        table = Table(title="⚠️ Unrecognized Mods (Could not be exported)", show_header=True, header_style="bold yellow", box=box.ROUNDED)
        table.add_column("Filename")
        for uf in unrecognized_files:
            table.add_row(uf)
        console.print(table)


def import_modpack(filename: str, output_dir: Path):
    if not os.path.exists(filename):
        console.print(f"[bold red]Error:[/bold red] The file {filename} does not exist.")
        return
        
    try:
        with open(filename, "r", encoding="utf-8") as f:
            modpack_data = json.load(f)
    except json.JSONDecodeError:
        console.print(f"[bold red]Error:[/bold red] The file {filename} is not a valid JSON file.")
        return
    except IOError as e:
        console.print(f"[bold red]Error reading {filename}:[/bold red] {e}")
        return

    if not modpack_data:
        console.print(f"[yellow]The file {filename} is empty or has no mods to download.[/yellow]")
        return
        
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"[bold cyan]Starting import of {len(modpack_data)} mods from {filename}...[/bold cyan]")
    
    remaining_mods = list(modpack_data)
    
    api = ModrinthAPI()
    
    for mod in modpack_data:
        project_name = mod.get("name", mod.get("filename", "Unknown Mod"))
        url = mod.get("url")
        target_filename = mod.get("filename")
        
        # If url is missing, we need to fetch it
        if not url:
            version_id = mod.get("version_id")
            if version_id:
                try:
                    with console.status(f"[yellow]Resolving {project_name}...[/yellow]"):
                        resp = api.session.get(f"{api.BASE_URL}/version/{version_id}")
                        if resp.status_code == 200:
                            data = resp.json()
                            for fd in data.get("files", []):
                                if fd.get("primary") or len(data["files"]) == 1:
                                    url = fd.get("url")
                                    if not target_filename:
                                        target_filename = fd.get("filename")
                                    break
                except Exception as e:
                    pass
                    
        if not url:
            console.print(f"[bold red]Failed to resolve download URL for {project_name}[/bold red]")
            continue
            
        if not target_filename:
            target_filename = url.split("/")[-1]
            
        try:
            console.print(f"[cyan]Downloading[/cyan] [yellow]{project_name}[/yellow]...")
            download_file(url, output_dir, target_filename)
            
            # Atomic update
            remaining_mods.remove(mod)
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(remaining_mods, f, indent=4)
                
        except Exception as e:
            console.print(f"[bold red]Failed to download {project_name}:[/bold red] {e}")
            
    if not remaining_mods:
        try:
            os.remove(filename)
            console.print(f"\n[bold green]✓ Import completed successfully! {filename} has been deleted.[/bold green]")
        except OSError as e:
            console.print(f"\n[bold yellow]Import finished, but could not delete {filename}:[/bold yellow] {e}")
    else:
        console.print(f"\n[bold yellow]Import finished with errors. {len(remaining_mods)} mods remain in {filename}. Run the command again to retry.[/bold yellow]")
