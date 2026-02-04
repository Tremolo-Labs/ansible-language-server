"""Settings management service.

Port of src/services/settingsManager.ts
"""

from typing import Optional
from urllib.parse import urlparse

from pygls.lsp.server import LanguageServer

from ..models.settings import AnsibleSettings


class SettingsManager:
    """Manages document and workspace settings.

    Caches settings per-document URI and handles LSP configuration requests.
    """

    def __init__(self, server: LanguageServer) -> None:
        self._server = server
        self._settings: dict[str, AnsibleSettings] = {}
        self._global_settings: Optional[AnsibleSettings] = None

    async def get(self, uri: str) -> AnsibleSettings:
        """Get settings for a document URI.

        Requests configuration from client if not cached.
        """
        if uri in self._settings:
            return self._settings[uri]

        # Request configuration from client
        config = await self._server.get_configuration_async(
            items=[{"scopeUri": uri, "section": "ansible"}]
        )

        if config and len(config) > 0:
            settings = AnsibleSettings.from_dict(config[0] or {})
        else:
            settings = AnsibleSettings()

        self._settings[uri] = settings
        return settings

    def get_cached(self, uri: str) -> Optional[AnsibleSettings]:
        """Get cached settings without requesting from client."""
        return self._settings.get(uri)

    def invalidate(self, uri: Optional[str] = None) -> None:
        """Invalidate cached settings.

        Args:
            uri: Specific URI to invalidate, or None to invalidate all.
        """
        if uri is None:
            self._settings.clear()
        elif uri in self._settings:
            del self._settings[uri]

    def get_workspace_folder_uri(self, doc_uri: str) -> Optional[str]:
        """Get the workspace folder URI containing a document."""
        parsed = urlparse(doc_uri)
        doc_path = parsed.path

        workspace_folders = self._server.workspace.folders
        if not workspace_folders:
            return None

        # Find the workspace folder containing this document
        for folder_uri, folder in workspace_folders.items():
            folder_parsed = urlparse(folder_uri)
            if doc_path.startswith(folder_parsed.path):
                return folder_uri

        return None
