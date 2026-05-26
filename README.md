# EnderPull ⚡

A fast, automated CLI package manager for Minecraft mods.

EnderPull is a professional-grade command-line interface inspired by tools like `yt-dlp`. It interfaces directly with the Modrinth API to bypass web scraping, allowing users to download, manage, share modpacks, and automatically update Minecraft mods directly to their local machine via simple terminal commands.

## ✨ Features

- **Direct Modrinth API Integration**: Fast, native API queries without fragile web scraping.
- **Stateful Fabric Loader Management**: Checks, updates, and upgrades your Fabric Loader headlessly. Uses `.enderpull_config.json` to store your preferences (install type, Minecraft version, and active Fabric loader version).
- **Minecraft Version Auto-Detection**: Scans your default `.minecraft/versions` folder to automatically discover your latest played Minecraft version during a fresh install.
- **Smart Auto-Updating**: Automatically scans your installed `.jar` files, calculates their `SHA-1` hashes, and queries Modrinth in bulk to find updates.
- **Strict Environment Matching**: Ensures mods are only updated to versions compatible with your specific `loader` (e.g., Fabric) and `game_version` (e.g., 1.21.1).
- **Modpack Sharing**: Easily export your current mods to a JSON file and import them on another machine with atomic download safety.
- **Graceful Error Handling**: Elegant internet connection checks and API error handling that print clean error messages rather than massive traceback dumps.
- **Rich UI Terminal Feedback**: Enjoy a beautiful terminal experience complete with determinate progress bars, animated status spinners, and beautifully formatted tables detailing your environment.
- **Cross-Platform**: Automatically resolves the `%appdata%/.minecraft/mods` or `~/.minecraft/mods` paths based on your host OS. Automatically cleans up cross-platform installer scripts (removing `.sh` files on Windows and `.bat` files on Linux/macOS).

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/cid-moosa/enderpull.git
   cd enderpull
   ```
2. Run the 1-click installer for your operating system:

   **On Windows:**
   Simply double-click the `install.bat` file, or run it in your terminal:
   ```powershell
   .\install.bat
   ```

   **On macOS/Linux:**
   Run the installation script in your terminal:
   ```bash
   bash install.sh
   ```

That's it! The script will automatically create a virtual environment, install EnderPull, perform a platform-specific file cleanup, and register the `mc-dl` command so you can use it immediately.

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
The zero-click solution to keeping your mods updated. It scans your local mods folder, hashes your `.jar` files, queries Modrinth, and atomically downloads newer versions while deleting the old ones. Additionally, if you have run a Fabric installation, it checks and updates your Fabric loader automatically.
- **Example**: `mc-dl update`

### 3. `mc-dl export` (Create a Modpack)
Scans your local mods folder and exports the exact Modrinth project IDs and download URLs into a shareable JSON file.
- **Dedicated Folder**: The JSON file is automatically saved into an isolated `exported_packs/` folder in your current directory to keep your workspace clean.
- **Example**: `mc-dl export my-modpack.json`

### 4. `mc-dl import` (Smart Auto-Updating Modpack)
Reads a JSON file created by `mc-dl export` and implements a **Smart Import System** to save massive amounts of bandwidth and prevent outdated mod crashes.
- **Smart Skipping**: Analyzes your local `.jar` files and automatically skips downloading any mods you already have up-to-date.
- **Auto-Updating**: If the imported modpack lists an older version, EnderPull queries Modrinth, deletes your outdated local file, and automatically fetches the absolute latest release.
- **Atomic Safety**: If a download fails, it remains in the JSON. Rerunning the command safely resumes where it left off.
- **Example**: `mc-dl import exported_packs/my-modpack.json`

### 5. `mc-dl fabric` (Stateful Fabric Loader Management)
Provides subcommands to install, update, or upgrade the Fabric loader headlessly.
- **`mc-dl fabric update`**: Checks the Fabric Meta API for the latest loader version matching your active Minecraft version. Skips with a checkmark if you're already up-to-date.
  - **Example**: `mc-dl fabric update`
  - **Example with overrides**: `mc-dl fabric update --mc-version 1.21.1 --force`
- **`mc-dl fabric upgrade`**: Installs Fabric for a new target Minecraft version, then queries Modrinth to upgrade all your installed mods to versions compatible with the new Minecraft release.
  - **Example**: `mc-dl fabric upgrade 1.21.4`

### 6. `mc-dl clear` (Clear Terminal Screen)
A helper command to clear the terminal screen in a cross-platform manner.
- **Example**: `mc-dl clear`

### 7. `mc-dl self-clean` (Clean Installation)
A utility command to save disk space after globally installing EnderPull. It safely deletes unused repository boilerplate (like `README.md` and `requirements.txt`) from the package directory.
- **Example**: `mc-dl self-clean`

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **CLI Framework**: `argparse` + `rich-argparse`
- **Networking**: `requests`
- **Terminal UI**: `rich`
