"""Definition provider for Ansible Language Server.

Resolves go-to-definition for:
- Role names (roles: list, role: key, include_role, import_role)
- Task file paths (include_tasks, import_tasks)
- Variable file paths (vars_files, include_vars)
- Handler references (notify:)
"""

import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from lsprotocol import types

from ..services.ansible_parser import ParserService, AnsibleContext, DefinitionTarget


def get_definition(
    parser_service: ParserService,
    uri: str,
    content: str,
    line: int,
    character: int,
    workspace_uri: Optional[str] = None,
) -> Optional[types.LocationLink]:
    """Get definition location for a position in an Ansible document.

    Args:
        parser_service: The parser service instance
        uri: Document URI
        content: Document text content
        line: 0-indexed line number
        character: 0-indexed column number
        workspace_uri: Workspace folder URI (for role resolution)

    Returns:
        LocationLink or None if no definition found
    """
    doc = parser_service.parse(uri, content)
    target = doc.get_definition_target_at_position(line, character)

    if not target:
        return None

    # Determine workspace path
    if workspace_uri:
        workspace_path = Path(urlparse(workspace_uri).path)
    else:
        # Fall back to document's directory
        workspace_path = Path(urlparse(uri).path).parent

    match target.kind:
        case AnsibleContext.ROLE_NAME:
            return _resolve_role(target, workspace_path, uri)
        case AnsibleContext.INCLUDE_PATH:
            return _resolve_include(target, uri)
        case AnsibleContext.VARS_FILE_PATH:
            return _resolve_vars_file(target, uri)
        case AnsibleContext.HANDLER_REF:
            return _resolve_handler(target, doc, uri)
        case _:
            return None


def _resolve_role(
    target: DefinitionTarget,
    workspace_path: Path,
    doc_uri: str,
) -> Optional[types.LocationLink]:
    """Resolve role name to roles/<name>/tasks/main.yml"""
    role_name = target.name

    # Search paths for roles
    search_paths = [
        workspace_path / "roles",
        Path.home() / ".ansible" / "roles",
        Path("/etc/ansible/roles"),
    ]

    # Also check relative to the document
    doc_path = Path(urlparse(doc_uri).path)
    search_paths.insert(0, doc_path.parent / "roles")

    for roles_dir in search_paths:
        # Try tasks/main.yml first (most common)
        for main_file in ["main.yml", "main.yaml"]:
            role_main = roles_dir / role_name / "tasks" / main_file
            if role_main.exists():
                return _make_location_link(target, role_main, doc_uri)

        # Also check if role directory exists (meta/main.yml fallback)
        role_dir = roles_dir / role_name
        if role_dir.is_dir():
            for main_file in ["main.yml", "main.yaml"]:
                meta_main = role_dir / "meta" / main_file
                if meta_main.exists():
                    return _make_location_link(target, meta_main, doc_uri)

    return None


def _resolve_include(
    target: DefinitionTarget,
    doc_uri: str,
) -> Optional[types.LocationLink]:
    """Resolve include path relative to current document."""
    doc_path = Path(urlparse(doc_uri).path)
    include_path = doc_path.parent / target.name

    # Try with and without extension
    candidates = [include_path]
    if not include_path.suffix:
        candidates.extend([
            include_path.with_suffix(".yml"),
            include_path.with_suffix(".yaml"),
        ])

    for candidate in candidates:
        if candidate.exists():
            return _make_location_link(target, candidate, doc_uri)

    return None


def _resolve_vars_file(
    target: DefinitionTarget,
    doc_uri: str,
) -> Optional[types.LocationLink]:
    """Resolve vars file path relative to current document."""
    doc_path = Path(urlparse(doc_uri).path)
    vars_path = doc_path.parent / target.name

    candidates = [vars_path]
    if not vars_path.suffix:
        candidates.extend([
            vars_path.with_suffix(".yml"),
            vars_path.with_suffix(".yaml"),
        ])

    for candidate in candidates:
        if candidate.exists():
            return _make_location_link(target, candidate, doc_uri)

    return None


def _resolve_handler(
    target: DefinitionTarget,
    doc,  # AnsibleDocument
    doc_uri: str,
) -> Optional[types.LocationLink]:
    """Find handler definition by name in document."""
    handler_name = target.name

    # Search for handler with matching name in the document
    # Walk the tree looking for handlers: section with matching name
    root = doc.yaml_tree.root_node

    handler_location = _find_handler_in_tree(root, handler_name, doc.content)
    if handler_location:
        line, col = handler_location
        return types.LocationLink(
            origin_selection_range=types.Range(
                start=types.Position(line=target.range[0][0], character=target.range[0][1]),
                end=types.Position(line=target.range[1][0], character=target.range[1][1]),
            ),
            target_uri=doc_uri,
            target_range=types.Range(
                start=types.Position(line=line, character=0),
                end=types.Position(line=line, character=100),
            ),
            target_selection_range=types.Range(
                start=types.Position(line=line, character=col),
                end=types.Position(line=line, character=col + len(handler_name)),
            ),
        )

    return None


def _find_handler_in_tree(
    node,
    handler_name: str,
    content: str,
) -> Optional[tuple[int, int]]:
    """Recursively search for handler definition with matching name."""
    # Look for handlers: key
    if node.type == "block_mapping_pair":
        key_node = node.child_by_field_name("key")
        if key_node and content[key_node.start_byte:key_node.end_byte] == "handlers":
            value_node = node.child_by_field_name("value")
            if value_node:
                return _find_handler_name_in_list(value_node, handler_name, content)

    # Recurse into children
    for child in node.children:
        result = _find_handler_in_tree(child, handler_name, content)
        if result:
            return result

    return None


def _find_handler_name_in_list(
    node,
    handler_name: str,
    content: str,
) -> Optional[tuple[int, int]]:
    """Search handler list for matching name."""
    # node should be block_sequence or similar
    for child in node.children:
        if child.type in ("block_sequence_item", "block_node", "block_mapping"):
            # Look for name: key in this handler
            result = _find_name_key(child, handler_name, content)
            if result:
                return result
            # Recurse
            result = _find_handler_name_in_list(child, handler_name, content)
            if result:
                return result
    return None


def _find_name_key(
    node,
    handler_name: str,
    content: str,
) -> Optional[tuple[int, int]]:
    """Find name: key with matching value in a mapping."""
    if node.type == "block_mapping_pair":
        key_node = node.child_by_field_name("key")
        value_node = node.child_by_field_name("value")
        if key_node and value_node:
            key_text = content[key_node.start_byte:key_node.end_byte]
            if key_text == "name":
                value_text = content[value_node.start_byte:value_node.end_byte].strip().strip('"\'')
                if value_text == handler_name:
                    return (value_node.start_point[0], value_node.start_point[1])

    for child in node.children:
        result = _find_name_key(child, handler_name, content)
        if result:
            return result

    return None


def _make_location_link(
    target: DefinitionTarget,
    file_path: Path,
    doc_uri: str,
) -> types.LocationLink:
    """Create LocationLink from target to file."""
    target_uri = f"file://{file_path}"

    return types.LocationLink(
        origin_selection_range=types.Range(
            start=types.Position(line=target.range[0][0], character=target.range[0][1]),
            end=types.Position(line=target.range[1][0], character=target.range[1][1]),
        ),
        target_uri=target_uri,
        target_range=types.Range(
            start=types.Position(line=0, character=0),
            end=types.Position(line=0, character=0),
        ),
        target_selection_range=types.Range(
            start=types.Position(line=0, character=0),
            end=types.Position(line=0, character=0),
        ),
    )
