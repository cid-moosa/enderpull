# EnderPull ⚡

A fast, automated CLI package manager for Minecraft mods.

EnderPull is a professional-grade command-line interface inspired by tools like `yt-dlp`. It interfaces directly with the Modrinth API to bypass web scraping, allowing users to download, manage, share modpacks, and automatically update Minecraft mods directly to their local machine via simple terminal commands.

## ✨ Features

- **Direct Modrinth API Integration**: Fast, native API queries without fragile web scraping.
- **Smart Auto-Updating**: Automatically scans your installed `.jar` files, calculates their `SHA-1` hashes, and queries Modrinth in bulk to find updates.
- **Strict Environment Matching**: Ensures mods are only updated to versions compatible with your specific `loader` (e.g., Fabric) and `game_version` (e.g., 1.21.1).
- **Modpack Sharing**: Easily export your current mods to a JSON file and import them on another machine with atomic download safety.
- **Rich UI Terminal Feedback**: Enjoy a beautiful terminal experience complete with determinate progress bars, animated status spinners, and beautifully formatted tables detailing your environment.
- **Cross-Platform**: Automatically resolves the `%appdata%/.minecraft/mods` or `~/.minecraft/mods` paths based on your host OS.

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/enderpull.git
   cd enderpull
   ```
2. Create and activate a virtual environment (recommended):

   **On Windows:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

   **On macOS/Linux:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install the package in editable mode:
   ```bash
   pip install -e .
   ```

## 📖 Command Reference

EnderPull uses a beautifully formatted, rich-powered `--help` menu. You can append `-h` or `--help` to any command to see its specific arguments.

```bash
mc-dl --help
```

### 1. `mc-dl get` (Download a Mod)
Downloads a specific mod by its exact name or Modrinth project slug.
- **Example**: `mc-dl get sodium`
- **Example with flags**: `mc-dl get iris --loader fabric --mc-version 1.21.1`

### 2. `mc-dl update` (The Auto-Updater)
The zero-click solution to keeping your mods updated. It scans your local mods folder, hashes your `.jar` files, queries Modrinth, and atomically downloads newer versions while deleting the old ones. It finishes by rendering a premium, color-coded summary table.
- **Example**: `mc-dl update`

### 3. `mc-dl export` (Create a Modpack)
Scans your local mods folder and exports the exact Modrinth project IDs and download URLs into a shareable JSON file.
- **Example**: `mc-dl export my-modpack.json`

### 4. `mc-dl import` (Download a Modpack)
Reads a JSON file created by `mc-dl export` and downloads all the listed mods. It uses safety-resume logic: if a download succeeds, it is removed from the JSON. If the process is interrupted or a mod fails to download, running the command again will safely resume where it left off.
- **Example**: `mc-dl import my-modpack.json`

### 5. `mc-dl self-clean` (Clean Installation)
A utility command to save disk space after globally installing EnderPull. It safely deletes unused repository boilerplate (like `README.md` and `requirements.txt`) from the package directory.
- **Example**: `mc-dl self-clean`

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **CLI Framework**: `argparse` + `rich-argparse`
- **Networking**: `requests`
- **Terminal UI**: `rich`
