# EnderPull ⚡

A fast, automated CLI package manager for Minecraft mods.

EnderPull is a professional-grade command-line interface inspired by tools like `yt-dlp`. It interfaces directly with the Modrinth API to bypass web scraping, allowing users to download, manage, share modpacks, and automatically update Minecraft mods directly to their local machine via simple terminal commands.

## ✨ Features

- **Direct Modrinth API Integration**: Fast, native API queries without fragile web scraping.
- **Local Mod Management**: Installs, searches (locally or online), removes, and lists installed mods with fast ZIP metadata parsing that shows exact version and loader information.
- **Stateful Fabric Loader Management**: Checks, updates, and upgrades your Fabric Loader headlessly. Uses `.enderpull_config.json` to store your preferences (install type, Minecraft version, and active Fabric loader version).
- **Minecraft Version Auto-Detection**: Scans your default `.minecraft/versions` folder to automatically discover your latest played Minecraft version during a fresh install.
- **Smart Auto-Updating**: Automatically scans your installed `.jar` files, calculates their `SHA-1` hashes, and queries Modrinth in bulk to find updates.
- **Strict Environment Matching**: Ensures mods are only updated to versions compatible with your specific `loader` (e.g., Fabric) and `game_version` (e.g., 1.21.1).
- **Modpack Sharing**: Easily export your current mods to a JSON file and import them on another machine with atomic download safety.
- **Graceful Error Handling**: Elegant internet connection checks and API error handling that print clean error messages rather than massive traceback dumps.
- **Rich UI Terminal Feedback**: Enjoy a beautiful terminal experience complete with determinate progress bars, animated status spinners, and beautifully formatted tables detailing your environment.
- **Cross-Platform**: Automatically resolves the `%appdata%/.minecraft/mods` or `~/.minecraft/mods` paths based on your host OS. Automatically cleans up cross-platform installer scripts (removing `.sh` files on Windows and `.bat` files on Linux/macOS).

## 🚀 Setup & Launching Guide

> [!IMPORTANT]
> ### 📥 1. First-Time Installation (1-Click Installer)
>
> Clone the repository and run the platform-appropriate installer. This will automatically set up a Python virtual environment, download all dependencies, register the `mc-dl` command, and perform platform-specific cleanups (e.g. removing unused shell or batch files).
>
> **Step A: Clone and Enter Directory**
> ```bash
> git clone https://github.com/cid-moosa/enderpull.git
> cd enderpull
> ```
>
> **Step B: Run the Installer**
> - **Windows (PowerShell, Cmd, or Explorer):**
>   Double-click **`install.bat`** in file explorer, or run:
>   ```powershell
>   .\install.bat
>   ```
> - **macOS / Linux (Terminal):**
>   Run:
>   ```bash
>   bash install.sh
>   ```

> [!TIP]
> ### ⚡ 2. How to Launch EnderPull (Subsequent Runs)
>
> Once installed, you **do not** run the installer again (in fact, it cleans itself up!). Simply run the launcher script whenever you want to work with EnderPull:
>
> - **On Windows:**
>   Double-click **`launch.bat`** in file explorer, or run:
>   ```powershell
>   .\launch.bat
>   ```
> - **On macOS / Linux:**
>   Run:
>   ```bash
>   ./launch.sh
>   ```
>
> *This automatically opens a dedicated shell with the virtual environment activated, displays the help menu, and leaves the terminal open and ready for your `mc-dl` commands.*


## 📖 Command Reference

EnderPull uses a beautifully formatted, rich-powered `--help` menu. You can append `-h` or `--help` to any command to see its specific arguments.

```bash
mc-dl --help
```

### 1. `mc-dl install` (Download & Install a Mod)
Downloads and installs a specific mod by its exact name or Modrinth project slug.
- **Example**: `mc-dl install sodium`
- **Example with flags**: `mc-dl install iris --loader fabric --mc-version 1.21.1`

### 2. `mc-dl search` (Search Online or Locally)
Searches for mods either on Modrinth (online) or locally in your mods folder.
- **Online Search (Modrinth)**: Displays matching projects with their slugs, download count, loader support, and descriptions in a table.
  - **Example**: `mc-dl search sodium`
- **Local Search**: Searches your installed `.jar` files for mods matching the query term (by ID, display name, or filename).
  - **Example**: `mc-dl search sodium --local`

### 3. `mc-dl remove` (Uninstall a Local Mod)
Deletes matching mod `.jar` files from your local mods directory.
- **Example**: `mc-dl remove sodium`

### 4. `mc-dl list` / `mc-dl --list` (List Installed Mods)
Lists all installed mods in your mods directory with their full name, filename, version, and mod loader parsed directly from the zip metadata on disk.
- **Example (subcommand)**: `mc-dl list`
- **Example (global flag)**: `mc-dl --list`

### 5. `mc-dl update` (The Auto-Updater)
The zero-click solution to keeping your mods updated. It scans your local mods folder, hashes your `.jar` files, queries Modrinth, and atomically downloads newer versions while deleting the old ones. Additionally, if you have run a Fabric installation, it checks and updates your Fabric loader automatically.
- **Example**: `mc-dl update`

### 6. `mc-dl export` (Create a Modpack)
Scans your local mods folder and exports the exact Modrinth project IDs and download URLs into a shareable JSON file.
- **Dedicated Folder**: The JSON file is automatically saved into an isolated `exported_packs/` folder in your current directory to keep your workspace clean.
- **Example**: `mc-dl export my-modpack.json`

### 7. `mc-dl import` (Smart Auto-Updating Modpack)
Reads a JSON file created by `mc-dl export` and implements a **Smart Import System** to save massive amounts of bandwidth and prevent outdated mod crashes.
- **Smart Skipping**: Analyzes your local `.jar` files and automatically skips downloading any mods you already have up-to-date.
- **Auto-Updating**: If the imported modpack lists an older version, EnderPull queries Modrinth, deletes your outdated local file, and automatically fetches the absolute latest release.
- **Atomic Safety**: If a download fails, it remains in the JSON. Rerunning the command safely resumes where it left off.
- **Example**: `mc-dl import exported_packs/my-modpack.json`

### 8. `mc-dl fabric` (Stateful Fabric Loader Management)
Provides subcommands to install, update, or upgrade the Fabric loader headlessly.
- **`mc-dl fabric update`**: Checks the Fabric Meta API for the latest loader version matching your active Minecraft version. Skips with a checkmark if you're already up-to-date.
  - **Example**: `mc-dl fabric update`
  - **Example with overrides**: `mc-dl fabric update --mc-version 1.21.1 --force`
- **`mc-dl fabric upgrade`**: Installs Fabric for a new target Minecraft version, then queries Modrinth to upgrade all your installed mods to versions compatible with the new Minecraft release.
  - **Example**: `mc-dl fabric upgrade 1.21.4`

### 9. `mc-dl clear` (Clear Terminal Screen)
A helper command to clear the terminal screen in a cross-platform manner.
- **Example**: `mc-dl clear`

### 10. `mc-dl self-clean` (Clean Installation)
A utility command to save disk space after globally installing EnderPull. It safely deletes unused repository boilerplate (like `README.md` and `requirements.txt`) from the package directory.
- **Example**: `mc-dl self-clean`

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **CLI Framework**: `argparse` + `rich-argparse`
- **Networking**: `requests`
- **Terminal UI**: `rich`
