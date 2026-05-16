import os
from pathlib import Path
from rich.console import Console

console = Console()

def self_clean():
    """Deletes unnecessary source files from the installation directory."""
    # Find the root of the project relative to this file
    # This file is in enderpull/cleaner.py
    current_dir = Path(__file__).parent
    project_root = current_dir.parent
    
    files_to_delete = [
        "README.md",
        "requirements.txt",
        ".gitignore"
    ]
    
    # Check if we are in a git repository
    if (project_root / ".git").exists() or (project_root / ".git").is_dir():
        console.print("[bold yellow]Warning:[/bold yellow] A .git directory was detected.")
        console.print("You are likely running this from an active source repository.")
        console.print("Deleting these files will cause Git to mark them as deleted.")
        
    deleted_count = 0
    for filename in files_to_delete:
        file_path = project_root / filename
        if file_path.exists() and file_path.is_file():
            try:
                os.remove(file_path)
                console.print(f"[dim]Deleted {filename}[/dim]")
                deleted_count += 1
            except OSError as e:
                console.print(f"[red]Failed to delete {filename}:[/red] {e}")
                
    if deleted_count > 0:
        console.print(f"[bold green]✓ Successfully deleted {deleted_count} unnecessary files to save space.[/bold green]")
    else:
        console.print("[yellow]No files needed cleaning. Already clean.[/yellow]")
