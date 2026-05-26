"""
Fabric Meta API client.

Wraps the public Fabric Meta API (https://meta.fabricmc.net/v2/) to retrieve:
  - Available Fabric loader versions (filtered to stable builds).
  - The latest stable installer .jar URL.
  - The latest stable loader version that supports a given Minecraft version.
"""

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError, HTTPError
from .exceptions import ApiError, VersionNotFoundError

FABRIC_META_BASE = "https://meta.fabricmc.net/v2"


class FabricMetaAPI:
    """Thin wrapper around the Fabric Meta API."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "enderpull/0.1.0 (CLI Mod Manager; Fabric Installer)"}
        )

    # ------------------------------------------------------------------
    # Network helper
    # ------------------------------------------------------------------

    def _get(self, url: str, **kwargs) -> requests.Response:
        """
        Thin wrapper around ``session.get`` that converts low-level network
        errors into clean, typed exceptions the CLI can display gracefully.

        Raises:
            ApiError           – ConnectionError (no internet / DNS failure) or
                                 any non-404 HTTP error status.
            VersionNotFoundError – HTTP 404 (invalid MC version / missing resource).
        """
        try:
            resp = self.session.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except RequestsConnectionError:
            raise ApiError(
                "Could not connect to the Fabric Meta API. "
                "Please check your internet connection."
            )
        except HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "unknown"
            if status == 404:
                raise VersionNotFoundError(
                    f"API Error: 404 Not Found for {url}. "
                    "Double-check that your Minecraft version is typed correctly!"
                )
            raise ApiError(
                f"API Error: {status} — {exc}. "
                "Double-check that your Minecraft version is typed correctly!"
            )

    # ------------------------------------------------------------------
    # Installer helpers
    # ------------------------------------------------------------------

    def get_latest_installer(self) -> dict:
        """
        Returns metadata for the latest *stable* Fabric installer.

        Returns a dict with keys:
            version (str)  – installer version string
            url     (str)  – direct download URL for the .jar
        """
        url = f"{FABRIC_META_BASE}/versions/installer"
        resp = self._get(url, timeout=15)

        installers = resp.json()
        # The list is sorted newest-first; prefer the first stable entry.
        stable = [i for i in installers if i.get("stable")]
        chosen = stable[0] if stable else (installers[0] if installers else None)
        if not chosen:
            raise VersionNotFoundError("No Fabric installer versions found.")

        return {"version": chosen["version"], "url": chosen["url"]}

    # ------------------------------------------------------------------
    # Loader helpers
    # ------------------------------------------------------------------

    def get_all_loaders(self) -> list[dict]:
        """
        Returns the full list of Fabric loader versions from the API.
        Each entry has at minimum: version (str), stable (bool).
        """
        url = f"{FABRIC_META_BASE}/versions/loader"
        resp = self._get(url, timeout=15)
        loaders = resp.json()
        if not loaders:
            raise VersionNotFoundError("Fabric Meta API returned no loader versions.")
        return loaders

    def get_latest_stable_loader(self) -> str:
        """
        Returns the version string of the latest *stable* Fabric loader.
        Falls back to the absolute latest if no stable entry exists.
        """
        loaders = self.get_all_loaders()
        stable = [lo for lo in loaders if lo.get("stable")]
        chosen = stable[0] if stable else loaders[0]
        return chosen["version"]

    def get_latest_loader_for_mc(self, mc_version: str) -> str:
        """
        Returns the version string of the latest *stable* Fabric loader that
        is compatible with *mc_version*.

        The Fabric Meta API endpoint
            GET /v2/versions/loader/<mc_version>
        returns an ordered list of loader objects that are verified to work
        with that game version.  We pick the first stable one.

        Raises:
            VersionNotFoundError – if the mc_version has no compatible loaders.
            ApiError             – on non-200 HTTP responses.
        """
        url = f"{FABRIC_META_BASE}/versions/loader/{mc_version}"
        # _get() raises VersionNotFoundError on 404 and ApiError on other failures.
        # We catch VersionNotFoundError here to enrich the message with mc_version context.
        try:
            resp = self._get(url, timeout=15)
        except VersionNotFoundError:
            raise VersionNotFoundError(
                f"Minecraft version '{mc_version}' was not found in the Fabric "
                f"Meta API. Make sure you typed the version correctly (e.g. 1.21.1)."
            )

        entries = resp.json()
        if not entries:
            raise VersionNotFoundError(
                f"No Fabric loader versions found for Minecraft {mc_version}."
            )

        # Each entry looks like: {"loader": {"version": "0.x.y", "stable": true/false}, ...}
        stable_entries = [e for e in entries if e.get("loader", {}).get("stable")]
        chosen = stable_entries[0] if stable_entries else entries[0]
        return chosen["loader"]["version"]

    # ------------------------------------------------------------------
    # Convenience: game version list
    # ------------------------------------------------------------------

    def get_supported_game_versions(self) -> list[str]:
        """
        Returns a list of Minecraft version strings that Fabric supports,
        ordered newest-first.
        """
        url = f"{FABRIC_META_BASE}/versions/game"
        resp = self._get(url, timeout=15)
        versions = resp.json()
        return [v["version"] for v in versions if v.get("stable")]
