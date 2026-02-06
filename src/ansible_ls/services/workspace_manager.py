"""Workspace management service.

Port of src/services/workspaceManager.ts
"""

from typing import Optional, Protocol
from urllib.parse import urlparse

from pygls.lsp.server import LanguageServer
from lsprotocol import types

from .settings_manager import SettingsManager


class WorkspaceFolderContext:
    """Context for a single workspace folder.

    Lazily initializes services as needed.
    """

    def __init__(
        self,
        workspace_folder: types.WorkspaceFolder,
        server: LanguageServer,
        settings_manager: SettingsManager,
    ) -> None:
        self._folder = workspace_folder
        self._server = server
        self._settings_manager = settings_manager

        # Lazy-loaded services (initialized on first access)
        self._docs_library: Optional["DocsLibrary"] = None
        self._ansible_config: Optional["AnsibleConfig"] = None
        self._ansible_lint: Optional["AnsibleLint"] = None

    @property
    def uri(self) -> str:
        """Get the workspace folder URI."""
        return self._folder.uri

    @property
    def name(self) -> str:
        """Get the workspace folder name."""
        return self._folder.name

    async def get_docs_library(self) -> "DocsLibrary":
        """Get or initialize the DocsLibrary for this workspace."""
        if self._docs_library is None:
            from .docs_library import DocsLibrary

            settings = await self._settings_manager.get(self.uri)
            self._docs_library = DocsLibrary(
                workspace_uri=self.uri,
                settings=settings,
            )
            await self._docs_library.initialize()
        return self._docs_library

    async def get_ansible_config(self) -> "AnsibleConfig":
        """Get or initialize the AnsibleConfig for this workspace."""
        if self._ansible_config is None:
            from .ansible_config import AnsibleConfig

            settings = await self._settings_manager.get(self.uri)
            self._ansible_config = AnsibleConfig(
                workspace_uri=self.uri,
                settings=settings,
            )
            await self._ansible_config.initialize()
        return self._ansible_config

    def dispose(self) -> None:
        """Clean up resources when workspace folder is removed."""
        if self._docs_library:
            self._docs_library.dispose()


class WorkspaceManager:
    """Manages workspace folder contexts.

    Creates and tracks WorkspaceFolderContext instances for each
    workspace folder in a multi-root workspace.
    """

    def __init__(
        self,
        server: LanguageServer,
        settings_manager: SettingsManager,
    ) -> None:
        self._server = server
        self._settings_manager = settings_manager
        self._contexts: dict[str, WorkspaceFolderContext] = {}

    def get_context(self, uri: str) -> Optional[WorkspaceFolderContext]:
        """Get the context for a document URI."""
        # Find which workspace folder contains this URI
        folder_uri = self._find_workspace_folder(uri)
        if folder_uri:
            return self._contexts.get(folder_uri)
        return None

    def _find_workspace_folder(self, doc_uri: str) -> Optional[str]:
        """Find the workspace folder containing a document."""
        parsed = urlparse(doc_uri)
        doc_path = parsed.path

        for folder_uri in self._contexts:
            folder_parsed = urlparse(folder_uri)
            if doc_path.startswith(folder_parsed.path):
                return folder_uri

        return None

    def add_folder(self, folder: types.WorkspaceFolder) -> WorkspaceFolderContext:
        """Add a workspace folder and create its context."""
        context = WorkspaceFolderContext(
            workspace_folder=folder,
            server=self._server,
            settings_manager=self._settings_manager,
        )
        self._contexts[folder.uri] = context
        return context

    def remove_folder(self, folder_uri: str) -> None:
        """Remove a workspace folder and dispose its context."""
        if folder_uri in self._contexts:
            self._contexts[folder_uri].dispose()
            del self._contexts[folder_uri]

    def handle_workspace_folders_change(
        self,
        added: list[types.WorkspaceFolder],
        removed: list[types.WorkspaceFolder],
    ) -> None:
        """Handle workspace/didChangeWorkspaceFolders notification."""
        for folder in removed:
            self.remove_folder(folder.uri)
        for folder in added:
            self.add_folder(folder)

    def dispose(self) -> None:
        """Dispose all workspace contexts."""
        for context in self._contexts.values():
            context.dispose()
        self._contexts.clear()
