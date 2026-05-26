import json
import requests
from requests.exceptions import ConnectionError as RequestsConnectionError, HTTPError
from .exceptions import ModNotFoundError, VersionNotFoundError, ApiError

class ModrinthAPI:
    BASE_URL = "https://api.modrinth.com/v2"

    def __init__(self):
        self.session = requests.Session()
        # Modrinth asks for a custom User-Agent identifying the app
        self.session.headers.update({
            "User-Agent": "enderpull/0.1.0 (CLI Mod Downloader)"
        })

    # ------------------------------------------------------------------
    # Network helper
    # ------------------------------------------------------------------

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Central HTTP dispatcher that converts low-level network failures into
        clean typed exceptions instead of raw urllib3 tracebacks.

        Raises:
            ApiError         – no internet / DNS failure, or non-404 HTTP errors.
            ModNotFoundError – HTTP 404 (project or version does not exist).
        """
        try:
            resp = self.session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except RequestsConnectionError:
            raise ApiError(
                "Could not connect to the Modrinth API. "
                "Please check your internet connection."
            )
        except HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            if status == 404:
                raise ModNotFoundError(
                    f"API Error: 404 Not Found for {url}. "
                    "The mod or version may not exist on Modrinth."
                )
            raise ApiError(
                f"Modrinth API Error: {status} — {exc}."
            )

    def resolve_project_slug(self, query: str) -> str:
        """
        Attempts to resolve a query to a project slug.
        First tries exact match, then falls back to search.
        """
        # Try direct hit — a 404 means no exact match; fall through to search.
        url = f"{self.BASE_URL}/project/{query}"
        try:
            resp = self._request("GET", url)
            return resp.json().get("slug", query)
        except ModNotFoundError:
            pass  # Not an exact slug — try the search endpoint below.

        # Fallback to search
        search_url = f"{self.BASE_URL}/search"
        params = {"query": query, "limit": 1}
        resp = self._request("GET", search_url, params=params)
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

        resp = self._request("GET", url, params=params)
            
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
        payload = {"hashes": hashes, "algorithm": "sha1"}
        resp = self._request("POST", url, json=payload)
        return resp.json()

    def search_projects(self, query: str, limit: int = 10) -> list:
        """
        Searches Modrinth projects by query.
        """
        url = f"{self.BASE_URL}/search"
        params = {"query": query, "limit": limit}
        resp = self._request("GET", url, params=params)
        return resp.json().get("hits", [])
