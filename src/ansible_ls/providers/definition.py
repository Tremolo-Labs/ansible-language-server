"""Definition provider for Ansible playbooks.

Port of src/providers/definitionProvider.ts
"""

from typing import Optional
from pathlib import Path
from urllib.parse import urlparse

from lsprotocol import types
from pygls.server import LanguageServer

from ..services.workspace_manager import WorkspaceManager
from ..utils.yaml_utils import parse_yaml, get_path_to_position, AncestryBuilder


async def provide_definition(
    server: LanguageServer,
    params: types.DefinitionParams,
    workspace_manager: WorkspaceManager,
) -> Optional[types.Location | list[types.Location]]:
    """Provide go-to-definition for Ansible symbols.

    Supports:
    - Role references (roles: section)
    - Task includes (include_tasks, import_tasks)
    - Variable file includes (vars_files)
    - Playbook imports (import_playbook)

    Args:
        server: The language server instance
        params: Definition request parameters
        workspace_manager: Workspace manager for accessing services

    Returns:
        Location(s) of the definition, or None if not found.
    """
    uri = params.text_document.uri
    document = server.workspace.get_document(uri)

    # Parse YAML and get path to cursor
    tree = parse_yaml(document.source)
    path = get_path_to_position(
        tree,
        params.position.line,
        params.position.character,
    )

    if not path:
        return None

    # Get the word at cursor position
    node = path[-1]
    word = node.text.decode("utf-8").strip().strip("'\"")

    # Determine what kind of reference this is
    ref_type = _determine_reference_type(path)

    if ref_type == "role":
        return await _find_role_definition(word, uri, workspace_manager)
    elif ref_type == "include":
        return _find_include_definition(word, uri)
    elif ref_type == "vars_file":
        return _find_vars_file_definition(word, uri)

    return None


def _determine_reference_type(path: list) -> Optional[str]:
    """Determine what kind of reference the cursor is on.

    Returns 'role', 'include', 'vars_file', or None.
    """
    builder = AncestryBuilder(path)

    # Look for key context
    key = builder.parent("block_mapping").get_string_key()

    if key in ("role", "roles"):
        return "role"
    elif key in ("include_tasks", "import_tasks", "include", "import_playbook"):
        return "include"
    elif key in ("vars_files", "include_vars"):
        return "vars_file"

    return None


async def _find_role_definition(
    role_name: str,
    document_uri: str,
    workspace_manager: WorkspaceManager,
) -> Optional[types.Location]:
    """Find the definition of a role."""
    parsed = urlparse(document_uri)
    doc_dir = Path(parsed.path).parent

    # Check common role locations
    role_paths = [
        doc_dir / "roles" / role_name / "tasks" / "main.yml",
        doc_dir / "roles" / role_name / "tasks" / "main.yaml",
        doc_dir.parent / "roles" / role_name / "tasks" / "main.yml",
    ]

    for role_path in role_paths:
        if role_path.exists():
            return types.Location(
                uri=role_path.as_uri(),
                range=types.Range(
                    start=types.Position(line=0, character=0),
                    end=types.Position(line=0, character=0),
                ),
            )

    return None


def _find_include_definition(
    include_path: str,
    document_uri: str,
) -> Optional[types.Location]:
    """Find the definition of an included file."""
    parsed = urlparse(document_uri)
    doc_dir = Path(parsed.path).parent

    # Resolve relative path
    target_path = doc_dir / include_path
    if target_path.exists():
        return types.Location(
            uri=target_path.as_uri(),
            range=types.Range(
                start=types.Position(line=0, character=0),
                end=types.Position(line=0, character=0),
            ),
        )

    return None


def _find_vars_file_definition(
    vars_path: str,
    document_uri: str,
) -> Optional[types.Location]:
    """Find the definition of a vars file."""
    return _find_include_definition(vars_path, document_uri)
