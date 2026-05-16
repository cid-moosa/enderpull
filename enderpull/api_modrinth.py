import json
import requests
from .exceptions import ModNotFoundError, VersionNotFoundError, ApiError

class ModrinthAPI:
    BASE_URL = "https://api.modrinth.com/v2"

    def __init__(self):
        self.session = requests.Session()
        # Modrinth asks for a custom User-Agent identifying the app
        self.session.headers.update({
            "User-Agent": "enderpull/0.1.0 (CLI Mod Downloader)"
        })

    def resolve_project_slug(self, query: str) -> str:
        """
        Attempts to resolve a query to a project slug.
        First tries exact match, then falls back to search.
        """
        # Try direct hit
        url = f"{self.BASE_URL}/project/{query}"
        resp = self.session.get(url)
        if resp.status_code == 200:
            return resp.json().get("slug", query)
        
        # Fallback to search
        search_url = f"{self.BASE_URL}/search"
        params = {
            "query": query,
            "limit": 1
        }
        resp = self.session.get(search_url, params=params)
        if resp.status_code == 200:
            hits = resp.json().get("hits", [])
            if hits:
                return hits[0]["slug"]
            
        raise ModNotFoundError(f"Could not find any Modrinth project matching '{query}'.")

    def get_version(self, slug: str, loader: str | list[str] = None, mc_version: str | list[str] = None):
        """
        Fetches the latest matching version for the given project, loader, and mc_version.
        """
        url = f"{self.BASE_URL}/project/{slug}/version"
        
        params = {}
        if loader:
            loaders_list = [loader.lower()] if isinstance(loader, str) else [l.lower() for l in loader]
            params["loaders"] = json.dumps(loaders_list)
        if mc_version:
            versions_list = [mc_version] if isinstance(mc_version, str) else mc_version
            params["game_versions"] = json.dumps(versions_list)
            
        resp = self.session.get(url, params=params)
        
        if resp.status_code != 200:
            if resp.status_code == 404:
                raise ModNotFoundError(f"Project '{slug}' not found when checking versions.")
            raise ApiError(f"Modrinth API returned status {resp.status_code}: {resp.text}")
            
        versions = resp.json()
        if not versions:
            error_msg = f"No versions found for '{slug}'"
            if loader or mc_version:
                error_msg += f" matching loader '{loader}' and game version '{mc_version}'"
            raise VersionNotFoundError(error_msg)
            
        # Modrinth returns versions sorted by date descending by default,
        # so the first one is the "latest" matching our criteria.
        latest_version = versions[0]
        
        # Extract the primary file
        files = latest_version.get("files", [])
        primary_file = next((f for f in files if f.get("primary")), None)
        if not primary_file and files:
            primary_file = files[0]
            
        if not primary_file:
            raise VersionNotFoundError(f"Found a version for '{slug}', but it has no downloadable files.")
            
        return {
            "url": primary_file["url"],
            "filename": primary_file["filename"],
            "version_number": latest_version.get("version_number", "unknown"),
            "date_published": latest_version.get("date_published"),
            "project_id": latest_version.get("project_id"),
            "version_type": latest_version.get("version_type", "unknown")
        }

    def get_versions_from_hashes(self, hashes: list[str]) -> dict:
        """
        Takes a list of SHA-1 hashes and returns a dict mapping hashes to version info.
        """
        if not hashes:
            return {}
        url = f"{self.BASE_URL}/version_files"
        payload = {
            "hashes": hashes,
            "algorithm": "sha1"
        }
        resp = self.session.post(url, json=payload)
        if resp.status_code != 200:
            raise ApiError(f"Modrinth API returned status {resp.status_code} during hash lookup: {resp.text}")
        return resp.json()
