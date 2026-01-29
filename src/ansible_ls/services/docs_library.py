"""Documentation library service.

Port of src/services/docsLibrary.ts
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import logging

from ..models.module import ModuleMetadata, ModuleDocumentation
from ..models.settings import AnsibleSettings


logger = logging.getLogger(__name__)


@dataclass
class DocsLibraryOptions:
    """Options for DocsLibrary initialization."""
    workspace_uri: str
    settings: AnsibleSettings
    collections_paths: list[Path] = None


class DocsLibrary:
    """Caches and provides Ansible module documentation.

    Discovers modules from:
    1. ansible.builtin modules (bundled with Ansible)
    2. Collections in ANSIBLE_COLLECTIONS_PATHS
    3. Playbook-adjacent collections (./collections)

    Documentation is loaded lazily on first access.
    """

    def __init__(
        self,
        workspace_uri: str,
        settings: AnsibleSettings,
    ) -> None:
        self._workspace_uri = workspace_uri
        self._settings = settings
        self._initialized = False

        # Module cache: FQCN -> ModuleMetadata
        self._modules: dict[str, ModuleMetadata] = {}

        # Short name to FQCN mappings (for non-FQCN lookups)
        self._short_names: dict[str, list[str]] = {}

    async def initialize(self) -> None:
        """Initialize the docs library by discovering modules."""
        if self._initialized:
            return

        await self._discover_builtin_modules()
        await self._discover_collection_modules()

        self._initialized = True
        logger.info(
            f"DocsLibrary initialized with {len(self._modules)} modules "
            f"for workspace {self._workspace_uri}"
        )

    async def _discover_builtin_modules(self) -> None:
        """Discover ansible.builtin modules."""
        # TODO: Use ansible-runner or direct imports to list modules
        ...

    async def _discover_collection_modules(self) -> None:
        """Discover modules from installed collections."""
        # TODO: Scan collection paths for module plugins
        ...

    def get_module(self, name: str) -> Optional[ModuleMetadata]:
        """Get module metadata by name.

        Args:
            name: Module name (FQCN like 'ansible.builtin.debug' or
                  short name like 'debug')

        Returns:
            ModuleMetadata if found, None otherwise.
        """
        # Try as FQCN first
        if name in self._modules:
            return self._modules[name]

        # Try short name lookup
        if name in self._short_names:
            fqcns = self._short_names[name]
            if len(fqcns) == 1:
                return self._modules[fqcns[0]]
            # Ambiguous - prefer ansible.builtin
            for fqcn in fqcns:
                if fqcn.startswith("ansible.builtin."):
                    return self._modules[fqcn]
            # Return first match
            return self._modules[fqcns[0]]

        return None

    async def get_module_documentation(
        self, name: str
    ) -> Optional[ModuleDocumentation]:
        """Get full documentation for a module.

        Loads documentation lazily if not already cached.
        """
        module = self.get_module(name)
        if not module:
            return None

        if module.documentation is None:
            # Load documentation
            module.documentation = await self._load_module_docs(module.fqcn)

        return module.documentation

    async def _load_module_docs(self, fqcn: str) -> Optional[ModuleDocumentation]:
        """Load documentation for a module by FQCN."""
        # TODO: Use ansible-runner.get_plugin_docs or parse DOCUMENTATION string
        ...
        return None

    def find_modules(self, prefix: str) -> list[ModuleMetadata]:
        """Find modules matching a prefix (for completion)."""
        results = []
        for fqcn, module in self._modules.items():
            if fqcn.startswith(prefix) or module.name.startswith(prefix):
                results.append(module)
        return results

    def dispose(self) -> None:
        """Clean up resources."""
        self._modules.clear()
        self._short_names.clear()
        self._initialized = False
