import os
import zipfile
import json
import re
from pathlib import Path
from rich.console import Console

console = Console()

def get_local_jar_metadata(jar_path: Path) -> dict:
    """
    Attempts to read metadata (like version and loader) directly from a jar file.
    Returns a dict with metadata keys: filename, name, id, version, loader.
    """
    metadata = {
        "filename": jar_path.name,
        "name": jar_path.stem,
        "id": jar_path.stem.lower(),
        "version": "Unknown",
        "loader": "Unknown"
    }
    
    try:
        with zipfile.ZipFile(jar_path, "r") as z:
            # Check for Fabric
            if "fabric.mod.json" in z.namelist():
                with z.open("fabric.mod.json") as f:
                    data = json.loads(f.read().decode("utf-8", errors="ignore"))
                    metadata["id"] = data.get("id", metadata["id"])
                    metadata["name"] = data.get("name", metadata["name"])
                    metadata["version"] = data.get("version", metadata["version"])
                    metadata["loader"] = "Fabric"
                    return metadata
            
            # Check for Forge/NeoForge (mods.toml)
            if "META-INF/mods.toml" in z.namelist():
                with z.open("META-INF/mods.toml") as f:
                    content = f.read().decode("utf-8", errors="ignore")
                    name_match = re.search(r'displayName\s*=\s*"([^"]+)"', content)
                    ver_match = re.search(r'version\s*=\s*"([^"]+)"', content)
                    id_match = re.search(r'modId\s*=\s*"([^"]+)"', content)
                    
                    if name_match:
                        metadata["name"] = name_match.group(1)
                    if ver_match:
                        metadata["version"] = ver_match.group(1)
                    if id_match:
                        metadata["id"] = id_match.group(1)
                    metadata["loader"] = "Forge/NeoForge"
                    return metadata
            
            # Check for old Forge (mcmod.info)
            if "mcmod.info" in z.namelist():
                with z.open("mcmod.info") as f:
                    try:
                        data = json.loads(f.read().decode("utf-8", errors="ignore"))
                        if isinstance(data, list) and len(data) > 0:
                            data = data[0]
                        metadata["id"] = data.get("modid", metadata["id"])
                        metadata["name"] = data.get("name", metadata["name"])
                        metadata["version"] = data.get("version", metadata["version"])
                        metadata["loader"] = "Forge"
                    except Exception:
                        pass
                    return metadata
    except Exception:
        pass
    
    return metadata


def list_installed_mods(mods_dir: Path) -> list[dict]:
    """Scans the mods_dir for .jar files and returns a list of mod metadata dicts."""
    if not mods_dir.exists() or not mods_dir.is_dir():
        return []
    
    jar_files = list(mods_dir.glob("*.jar"))
    mods = []
    for jar in jar_files:
        mods.append(get_local_jar_metadata(jar))
    # Sort alphabetically by name
    mods.sort(key=lambda x: x["name"].lower())
    return mods


def search_local_mods(query: str, mods_dir: Path) -> list[dict]:
    """Filters local mods that match the query term (case-insensitive)."""
    installed_mods = list_installed_mods(mods_dir)
    query_lower = query.lower()
    
    matches = []
    for mod in installed_mods:
        if (query_lower in mod["name"].lower() or 
            query_lower in mod["id"].lower() or 
            query_lower in mod["filename"].lower()):
            matches.append(mod)
    return matches


def remove_local_mod(query: str, mods_dir: Path) -> list[dict]:
    """
    Finds and deletes local mods matching the query term.
    Returns a list of successfully deleted mod info dicts.
    """
    matches = search_local_mods(query, mods_dir)
    if not matches:
        return []
    
    deleted = []
    for mod in matches:
        file_path = mods_dir / mod["filename"]
        if file_path.exists() and file_path.is_file():
            try:
                os.remove(file_path)
                deleted.append(mod)
            except OSError as e:
                console.print(f"[bold red]Error deleting {mod['filename']}:[/bold red] {e}")
                
    return deleted
