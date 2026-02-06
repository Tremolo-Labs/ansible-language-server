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
        """Discover ansible.builtin modules using ansible-doc."""
        import asyncio
        import json

        try:
            proc = await asyncio.create_subprocess_exec(
                "ansible-doc",
                "--list",
                "--type", "module",
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0 or not stdout:
                logger.warning(f"ansible-doc failed: {stderr.decode()[:200] if stderr else 'no output'}")
                return

            modules = json.loads(stdout.decode("utf-8"))

            for name, info in modules.items():
                # ansible-doc returns both short names and FQCNs
                # Short names are builtin if they don't have dots
                if "." not in name:
                    fqcn = f"ansible.builtin.{name}"
                    short_name = name
                elif name.startswith("ansible.builtin."):
                    fqcn = name
                    short_name = name.split(".")[-1]
                else:
                    # Skip non-builtin modules in this pass
                    continue

                metadata = ModuleMetadata(
                    source="builtin",
                    fqcn=fqcn,
                    namespace="ansible",
                    collection="builtin",
                    name=short_name,
                )
                self._modules[fqcn] = metadata
                self._short_names.setdefault(short_name, []).append(fqcn)

            logger.info(f"Discovered {len(self._modules)} builtin modules")

        except FileNotFoundError:
            logger.warning("ansible-doc not found - module discovery disabled")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse ansible-doc output: {e}")
        except Exception as e:
            logger.error(f"Module discovery failed: {e}")

    async def _discover_collection_modules(self) -> None:
        """Discover modules from installed collections."""
        import asyncio
        import json

        try:
            # Get all modules including collections
            proc = await asyncio.create_subprocess_exec(
                "ansible-doc",
                "--list",
                "--type", "module",
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0 or not stdout:
                return

            modules = json.loads(stdout.decode("utf-8"))

            for name, info in modules.items():
                # Skip builtins (handled separately) and non-FQCN entries
                if "." not in name or name.startswith("ansible.builtin."):
                    continue

                # Parse FQCN: namespace.collection.module_name
                parts = name.split(".")
                if len(parts) >= 3:
                    namespace = parts[0]
                    collection = parts[1]
                    short_name = parts[-1]

                    metadata = ModuleMetadata(
                        source="collection",
                        fqcn=name,
                        namespace=namespace,
                        collection=collection,
                        name=short_name,
                    )
                    self._modules[name] = metadata
                    self._short_names.setdefault(short_name, []).append(name)

            logger.info(f"Total modules after collection discovery: {len(self._modules)}")

        except Exception as e:
            logger.warning(f"Collection module discovery failed: {e}")

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
        """Load documentation for a module by FQCN using ansible-doc."""
        import asyncio
        import json
        from ..models.module import Option

        try:
            proc = await asyncio.create_subprocess_exec(
                "ansible-doc",
                fqcn,
                "--json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0 or not stdout:
                logger.debug(f"No docs found for {fqcn}")
                return None

            docs = json.loads(stdout.decode("utf-8"))

            if fqcn not in docs:
                return None

            doc_data = docs[fqcn].get("doc", {})

            # Parse options into Option objects (dict keyed by name)
            options: dict[str, Option] = {}
            for opt_name, opt_data in doc_data.get("options", {}).items():
                desc = opt_data.get("description", "")
                if isinstance(desc, list):
                    desc = "\n".join(desc)

                options[opt_name] = Option(
                    name=opt_name,
                    description=desc,
                    required=opt_data.get("required", False),
                    type=opt_data.get("type"),
                    default=opt_data.get("default"),
                    choices=opt_data.get("choices", []),
                    aliases=opt_data.get("aliases", []),
                )

            desc = doc_data.get("description", "")
            if isinstance(desc, list):
                desc = "\n".join(desc)

            return ModuleDocumentation(
                short_description=doc_data.get("short_description"),
                description=desc,
                options=options,
                notes=doc_data.get("notes", []),
            )

        except FileNotFoundError:
            logger.warning("ansible-doc not found")
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse module docs: {e}")
            return None
        except Exception as e:
            logger.debug(f"Failed to load docs for {fqcn}: {e}")
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
