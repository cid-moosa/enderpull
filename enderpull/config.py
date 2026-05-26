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


def get_minecraft_dir() -> Path:
    """
    Returns the default Minecraft base directory (parent of the mods/ folder).
    This is the .minecraft folder on client installs, or the server root for
    server installs. The EnderPull config file is stored here.
    """
    return get_default_mods_dir().parent


DEFAULT_MODS_DIR = get_default_mods_dir()
DEFAULT_MINECRAFT_DIR = get_minecraft_dir()
