import requests
from pathlib import Path
from rich.progress import Progress, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn
from .exceptions import ApiError

def download_file(url: str, output_path: Path, filename: str):
    """Streams a file from a URL to the given output path, showing a progress bar."""
    
    # Ensure the directory exists
    output_path.mkdir(parents=True, exist_ok=True)
    full_path = output_path / filename

    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
    except requests.RequestException as e:
        raise ApiError(f"Failed to connect to download URL: {e}")

    total_size = int(response.headers.get("content-length", 0))

    with Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    ) as progress:
        
        task_id = progress.add_task(f"Downloading {filename}", total=total_size)
        
        try:
            with open(full_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress.update(task_id, advance=len(chunk))
        except IOError as e:
            raise ApiError(f"Failed to write file to disk: {e}")

    return full_path
