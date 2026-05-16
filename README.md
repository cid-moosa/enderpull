# EnderPull ⚡

A fast, automated CLI package manager for Minecraft mods.

EnderPull is a professional-grade command-line interface inspired by tools like `yt-dlp`. It interfaces directly with the Modrinth API to bypass web scraping, allowing users to download, manage, and automatically update Minecraft mods directly to their local machine via simple terminal commands.

## ✨ Features

- **Direct Modrinth API Integration**: Fast, native API queries without fragile web scraping.
- **Smart Auto-Updating**: Automatically scans your installed `.jar` files, calculates their `SHA-1` hashes, and queries Modrinth in bulk to find updates.
- **Strict Environment Matching**: Ensures mods are only updated to versions compatible with your specific `loader` (e.g., Fabric) and `game_version` (e.g., 1.21.1).
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

## 💻 Usage

Once installed, the `mc-dl` command will be available globally in your terminal.

### 📥 Downloading Mods

Download a mod by its name or exact slug:
```bash
mc-dl get sodium
```

Filter by your specific mod loader or Minecraft version:
```bash
mc-dl get iris --loader fabric --mc-version 1.21.1
```

### 🔄 Auto-Updating Mods

Simply run the update command to scan your local mods directory, check against the Modrinth API, and download the latest compatible `.jar` files automatically!

```bash
mc-dl update
```

The CLI will output a beautifully themed table summarizing the Mod Name, Status, Mod Version, Game Version, Loader, and Release Type!

## 🛠️ Tech Stack

- **Language**: Python 3.10+
- **CLI Framework**: `argparse`
- **Networking**: `requests`
- **Terminal UI**: `rich`
