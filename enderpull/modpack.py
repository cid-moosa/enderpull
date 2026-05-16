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
        export_dir = Path("exported_packs")
        export_dir.mkdir(exist_ok=True)
        safe_filename = os.path.basename(filename)
        export_path = export_dir / safe_filename
        
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(modpack_data, f, indent=4)
        console.print(f"[bold green]✓ Successfully exported {len(modpack_data)} mods to exported_packs/{safe_filename}[/bold green]")
    except IOError as e:
        console.print(f"[bold red]Failed to write to {export_path}:[/bold red] {e}")

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
    
    api = ModrinthAPI()
    
    # The Scan Phase
    local_projects_map = {}
    jar_files = list(output_dir.glob("*.jar"))
    if jar_files:
        with console.status("[cyan]Scanning local mods..."):
            file_hashes = {calculate_sha1(jar): jar for jar in jar_files}
            try:
                version_info_map = api.get_versions_from_hashes(list(file_hashes.keys()))
                for f_hash, info in version_info_map.items():
                    pid = info.get("project_id")
                    if pid:
                        local_projects_map[pid] = {
                            "date_published": info.get("date_published", ""),
                            "jar_path": file_hashes[f_hash]
                        }
            except Exception:
                pass

    remaining_mods = list(modpack_data)
    
    for mod in modpack_data:
        project_name = mod.get("name", mod.get("filename", "Unknown Mod"))
        project_id = mod.get("project_id")
        url = mod.get("url")
        target_filename = mod.get("filename")
        
        # The Intelligence Loop
        if project_id:
            loaders = [mod.get("loader", "unknown").lower()] if mod.get("loader") else []
            game_versions = [mod.get("game_version")] if mod.get("game_version") else []
            try:
                with console.status(f"[yellow]Resolving {project_name}...[/yellow]"):
                    latest_version = api.get_version(slug=project_id, loader=loaders, mc_version=game_versions)
                    
                    if latest_version:
                        url = latest_version.get("url")
                        target_filename = latest_version.get("filename")
                        latest_date = latest_version.get("date_published", "")
                        
                        if project_id in local_projects_map:
                            local_info = local_projects_map[project_id]
                            if local_info["date_published"] >= latest_date:
                                console.print(f"[cyan]⏭️ Skipped: {project_name} (Already up-to-date)[/cyan]")
                                remaining_mods.remove(mod)
                                with open(filename, "w", encoding="utf-8") as f:
                                    json.dump(remaining_mods, f, indent=4)
                                continue
                            else:
                                console.print(f"[yellow]🔄 Updating: {project_name} (Found newer version)[/yellow]")
                                try:
                                    os.remove(local_info["jar_path"])
                                except OSError:
                                    pass
                        else:
                            console.print(f"[green]⬇️ Downloading: {project_name}[/green]")
            except Exception:
                pass
                
        # Fallback if API resolution failed or no project_id
        if not url:
            version_id = mod.get("version_id")
            if version_id:
                try:
                    with console.status(f"[yellow]Resolving fallback for {project_name}...[/yellow]"):
                        resp = api.session.get(f"{api.BASE_URL}/version/{version_id}")
                        if resp.status_code == 200:
                            data = resp.json()
                            for fd in data.get("files", []):
                                if fd.get("primary") or len(data["files"]) == 1:
                                    url = fd.get("url")
                                    if not target_filename:
                                        target_filename = fd.get("filename")
                                    break
                except Exception:
                    pass
                    
        if not url:
            console.print(f"[bold red]Failed to resolve download URL for {project_name}[/bold red]")
            continue
            
        if not target_filename:
            target_filename = url.split("/")[-1]
            
        try:
            # We don't print "Downloading..." here if we already printed it in the Intelligence loop
            if project_id not in local_projects_map and not url:
                 console.print(f"[cyan]Downloading[/cyan] [yellow]{project_name}[/yellow]...")
            elif project_id not in local_projects_map:
                pass # Already printed in Case C
            elif project_id in local_projects_map and url:
                pass # Already printed in Case B
            else:
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
