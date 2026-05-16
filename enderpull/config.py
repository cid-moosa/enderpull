import os
import platform
from pathlib import Path

def get_default_mods_dir() -> Path:
    """Returns the default Minecraft mods directory based on the OS."""
    system = platform.system()
    home = Path.home()
    
    if system == "Windows":
        appdata = os.getenv("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = home / "AppData" / "Roaming"
        return base / ".minecraft" / "mods"
    elif system == "Darwin":
        return home / "Library" / "Application Support" / "minecraft" / "mods"
    else:
        # Default to Linux/Unix
        return home / ".minecraft" / "mods"

DEFAULT_MODS_DIR = get_default_mods_dir()
